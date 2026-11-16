#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Terms updater."""

import copy
import re
from collections import OrderedDict

from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records import RDMDraft, RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import RecordCommitOp
from invenio_search.engine import search
from sqlalchemy import delete, select

from .keeptrace import KeepTrace
from .serdes import SubjectRDMSerdes

bulk = search.helpers.bulk


def filter_deltas_by_type(deltas, _type):
    """Filter deltas by _type.

    Args:
        deltas (iter[Delta]) : deltas to filter
        _type (str) : delta type to filter for
    """
    return (d for d in deltas if d.type == _type)


def find_idx_subject_dict(subjects, id_):
    """Return (idx, subject_dict) of subject with `id_` in `subjects`.

    Return (-1, {}) if not found.
    """
    return next(
        ((i, s) for i, s in enumerate(subjects) if s.get("id") == id_),
        (-1, {})
    )


def op_replace(subjects, delta):
    """Replace subject in-place.

    Args:
        subjects (list[dict - RDM subject shape]) : a record's subjects
        delta (Delta) : delta operation
    """
    idx, _ = find_idx_subject_dict(subjects, delta.subject_src.id)

    if idx == -1:
        return False

    for i, replacement in enumerate(delta.subjects_dst):
        new_subject_dict = {
            # Keeping as it was in the codebase before for now and just have id
            "id": replacement.id,
        }
        # first replacement takes place of src subject
        if i == 0:
            subjects[idx] = new_subject_dict
        # others are appended
        else:
            subjects.append(new_subject_dict)

    return True


def op_remove(subjects, delta):
    """Remove subject in-place.

    Args:
        subjects (list[dict - RDM subject shape]) : original subjects
        delta (Delta) : delta operation
    """
    idx, _ = find_idx_subject_dict(subjects, delta.subject_src.id)
    if idx == -1:
        return False
    subjects.pop(idx)
    return True


def op_rename(subjects, delta):
    """Fake rename subject in-place.

    Renaming is not done at the record DB level since a record's subjects
    are dereferenced dynamically. We do need to know if the record would
    see a rename in one of its subjects, so that we can flag it for
    keeping track of former subject + logging.

    The passed subjects should also be the original subjects of the record.
    Otherwise, a replace X for Y, followed by rename of Y's label could
    leave a trace on the record as though the record used to have Y's
    previous label.
    """
    idx, _ = find_idx_subject_dict(subjects, delta.subject_src.id)
    return idx != -1


def apply_op_data_change(delta, orig_subjects, record):
    """Apply `delta` change on `record`.

    Args:
        delta (Delta) : delta operation
        orig_subjects (list[dict - RDM subject shape]) : original subjects
        record (Record) : record

    Returns:
        boolean : was the change applied or not
    """
    subjects = record["metadata"]["subjects"]
    applied = False
    if delta.type == "replace":
        applied = op_replace(subjects, delta)
    elif delta.type == "remove":
        applied = op_remove(subjects, delta)
    elif delta.type == "edit":
        applied = op_rename(orig_subjects, delta)
    return applied


def deduplicate_subjects(subjects):
    """Return a deduplicated (order preserved) list of subjects.

    :param subjects: list[dict]
    :returns: list[dict]
    """
    def _tuplify(d):
        """Transforms a subject dict into a tuple with value stripped.

        This is needed because dicts are unhashable.
        """
        key = "id" if "id" in d else "subject"  # only 2 possibilities
        value = d.get(key).strip()
        return (key, value)

    result = [_tuplify(d) for d in subjects]
    result = OrderedDict.fromkeys(result)  # rm duplicates AND keeps order
    result = [dict([t]) for t in result]  # back to subjects
    return result


def update_rdm_record(record, deltas, logger, keep_trace):
    """Apply changes to record's subjects.

    Args:
        record (Record) : record
        deltas (iter[Delta]) : delta operations
        logger (SubjectDeltaLogger): Logger object
        keep_trace (KeepTrace) : KeepTrace object
    """
    orig_subjects = copy.deepcopy(record["metadata"]["subjects"])
    for delta in deltas:
        applied = apply_op_data_change(
            delta,
            orig_subjects,
            record,
        )

        if applied:
            if delta.keep_trace:
                keep_trace.trace(record, delta.subject_src.label)
            logger.log(record.pid.pid_value, delta=delta)

    # Make sure subjects are deduplicated
    record["metadata"]["subjects"] = deduplicate_subjects(
        record["metadata"]["subjects"]
    )

    # All side-effects
    # ---
    records_service = current_service_registry.get("records")
    # According to other code in InvenioRDM, the same indexer is used for
    # records and drafts
    commit_op = RecordCommitOp(record, records_service.indexer)
    # The following on_register, on_commit don't use the uow object
    # so passing None is fine
    fake_uow = None
    try:
        commit_op.on_register(fake_uow)  # commits to DB
        commit_op.on_commit(fake_uow)  # reindexes in index
    except Exception as e:  # noqa
        msg = re.sub(r"\s+", " ", str(e))
        logger.log(record.pid.pid_value, error=msg)
    finally:
        logger.flush()


def get_records_to_update(deltas, data_cls):
    """Return data-layer records to update."""

    def get_targeted_ids(deltas):
        return [
            d.subject_src.id for d in deltas
            if d.type in ["replace", "remove", "edit"]
        ]

    def has_at_least_1_subject_targeted(record_data_db, ids):
        """Return True if `record_data_db` has at least 1 subject in `ids`.

        Because of cases where there are 100K+ subjects, we can't construct
        queries filtering at the DB level. We do the filtering in memory,
        on batches of records. We keep loading simple at the cost of
        performance (but this is fine since this operation is in the
        background anyway).
        """
        # May be None in some Drafts
        if not record_data_db:
            return False
        subjects = record_data_db.get("metadata", {}).get("subjects", [])
        return any(s.get("id") in ids for s in subjects)

    targeted_ids = frozenset(get_targeted_ids(deltas))

    if not targeted_ids:
        return []

    stmt = (
        select(data_cls.model_cls)
        .execution_options(yield_per=200)  # could be made adjustable
    )

    result = (
        data_cls(obj.data, model=obj) for obj
        in db.session.scalars(stmt)
        if has_at_least_1_subject_targeted(obj.data, targeted_ids)
    )

    return result


class SubjectDeltaUpdater:
    """Translates delta operations into actual changes."""

    def __init__(self, deltas, logger, keep_trace):
        """Constructor.

        Args:
            deltas (list[Delta]): list of delta operatios.
            logger (SubjectDeltaLogger): Logger object.
            keep_trace (KeepTrace): KeepTrace object.
        """
        self._ops_data = deltas
        self._logger = logger
        self._keep_trace = keep_trace
        self._subject_rdm_serdes = SubjectRDMSerdes()

    def update(self):
        """Execute changes."""
        self._add_rdm_subjects()
        self._rename_rdm_subjects()

        self._update_rdm_records()

        self._remove_rdm_subjects()

    def _add_rdm_subjects(self):
        """Add to the Subjects entries."""
        service = current_service_registry.get("subjects")
        add_ops = filter_deltas_by_type(self._ops_data, "add")
        for op in add_ops:
            service.create(
                system_identity,
                self._subject_rdm_serdes.serialize(op.subjects_dst[0]),
            )

    def _rename_rdm_subjects(self):
        """Rename subjects in the Subjects entries."""
        service = current_service_registry.get("subjects")
        rename_ops = filter_deltas_by_type(self._ops_data, "edit")
        for op in rename_ops:
            service.update(
                system_identity,
                op.subject_src.id,
                self._subject_rdm_serdes.serialize(op.subjects_dst[0]),
            )

    def _update_rdm_records(self):
        """Execute operations (replace/remove/rename) on RDM records."""
        entries = get_records_to_update(self._ops_data, data_cls=RDMRecord)
        for record in entries:
            update_rdm_record(
                record,
                deltas=self._ops_data,
                logger=self._logger,
                keep_trace=self._keep_trace
            )

        # Don't keep trace for drafts
        entries = get_records_to_update(self._ops_data, data_cls=RDMDraft)
        for draft in entries:
            update_rdm_record(
                draft,
                deltas=self._ops_data,
                logger=self._logger,
                keep_trace=KeepTrace(None, None)  # noop KeepTrace
            )

    def _remove_rdm_subjects(self):
        """Remove subjects from the Subjects entries.

        We have to resort to low-level commands because the high-level ones
        are not made for bulk operations. We've checked the implications
        and we should be fine (at least at time of writing).
        """
        ids_for_removal = [
            d.subject_src.id for d in self._ops_data
            if d.type in ["remove", "replace"]
        ]
        service = current_service_registry.get("subjects")

        model_cls = service.record_cls.model_cls
        size_of_batch = 200  # Maybe TODO: make configurable
        for offset in range(0, len(ids_for_removal), size_of_batch):
            batch = ids_for_removal[offset:offset + size_of_batch]

            # Delete from database
            # ===
            # Get ids of model class
            # The ids_for_removal internally correspond to
            # pids, so they need to be dereferenced first
            stmt_to_select_ids = (
                select(model_cls.id)
                .where(model_cls.id == PersistentIdentifier.object_uuid)
                .where(PersistentIdentifier.pid_type == "sub")
                .where(PersistentIdentifier.pid_value.in_(batch))
            )
            ids_of_model_cls = list(db.session.scalars(stmt_to_select_ids))

            # Delete subject records
            stmt_to_delete_subjects = (
                delete(model_cls)
                .where(model_cls.id.in_(ids_of_model_cls))
                # ORM session synchronization has to be specified when deleting
                # Here we skip synchronization since not needed
                .execution_options(synchronize_session=False)
            )
            db.session.execute(stmt_to_delete_subjects)

            # Delete backing subject PID
            stmt_to_delete_pids = (
                delete(PersistentIdentifier)
                .where(PersistentIdentifier.pid_type == "sub")
                .where(PersistentIdentifier.pid_value.in_(batch))
                .execution_options(synchronize_session=False)
            )
            db.session.execute(stmt_to_delete_pids)

            db.session.commit()

            # Delete from document engine
            # ===
            alias_of_index = service.record_cls.index.search_alias
            bulk(
                service.indexer.client,
                (
                    {
                        "_op_type": "delete",
                        "_index": alias_of_index,
                        "_id": id_
                    }
                    for id_ in ids_of_model_cls
                ),
            )
