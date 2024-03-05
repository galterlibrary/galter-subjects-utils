# -*- coding: utf-8 -*-
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

bulk = search.helpers.bulk


def filter_ops_by_type(ops_data, _type):
    """Filter ops_data by _type."""
    return [op for op in ops_data if op.get("type") == _type]


def find_idx_subject_dict(subjects, id_):
    """Return (idx, subject_dict) of subject with `id_` in `subjects`.

    Return (-1, {}) if not found.
    """
    return next(
        ((i, s) for i, s in enumerate(subjects) if s.get("id") == id_),
        (-1, {})
    )


def op_replace(subjects, op_data):
    """Replace subject in-place.

    op_data:

    ```python
        {
            "type": "replace",
            "scheme": "...",
            "id": "...",
            "new_id": "...",
            "new_subject": "..."
        }
    ```
    """
    idx, subject_dict = find_idx_subject_dict(subjects, op_data["id"])
    if idx == -1:
        return False
    new_subject_dict = {
        # **subject_dict,  # probably not needed
        "id": op_data["new_id"],
    }
    subjects[idx] = new_subject_dict
    return True


def op_remove(subjects, op_data):
    """Remove subject in-place.

    op_data:

    ```python
        {
            "type": "remove",
            "scheme": "...",
            "id": "...",
        }
    ```
    """
    idx, subject_dict = find_idx_subject_dict(subjects, op_data["id"])
    if idx == -1:
        return False
    subjects.pop(idx)
    return True


def op_rename(subjects, op_data):
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
    idx, subject_dict = find_idx_subject_dict(subjects, op_data["id"])
    if idx == -1:
        return False
    # no action as mentioned
    return True


def apply_op_data_change(op_data, orig_subjects, record):
    """Apply `op_data` change on `record`."""
    subjects = record["metadata"]["subjects"]
    applied = False
    if op_data.get("type") == "replace":
        applied = op_replace(subjects, op_data)
    elif op_data.get("type") == "remove":
        applied = op_remove(subjects, op_data)
    elif op_data.get("type") == "rename":
        applied = op_rename(orig_subjects, op_data)
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
    result = [dict([t]) for t in result.keys()]  # back to subjects
    return result


def update_rdm_record(record, ops_data, logger, keep_trace):
    """Apply changes to record's subjects."""
    orig_subjects = copy.deepcopy(record["metadata"]["subjects"])
    for op_data in ops_data:
        applied = apply_op_data_change(
            op_data,
            orig_subjects,
            record,
        )

        if applied:
            if keep_trace.should_trace(op_data):
                keep_trace.trace(record, op_data["subject"])
            logger.log(record.pid.pid_value, delta=op_data)

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
    except Exception as e:
        msg = re.sub(r"\s+", " ", str(e))
        logger.log(record.pid.pid_value, error=msg)
    finally:
        logger.flush()


def get_records_to_update(ops_data, data_cls):
    """Return data-layer records to update."""

    def get_targeted_ids(ops_data):
        return [
            op["id"] for op in ops_data
            if op.get("type") in ["replace", "remove", "rename"]
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

    targeted_ids = frozenset(get_targeted_ids(ops_data))

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

    def __init__(self, ops_data, logger, keep_trace):
        """Constructor."""
        self._ops_data = ops_data
        self._logger = logger
        self._keep_trace = keep_trace

    def update(self):
        """Execute changes."""
        self._add_rdm_subjects()
        self._rename_rdm_subjects()

        self._update_rdm_records()

        self._remove_rdm_subjects()

    def _add_rdm_subjects(self):
        """Add to the Subjects entries."""
        service = current_service_registry.get("subjects")
        add_ops = filter_ops_by_type(self._ops_data, "add")
        for op in add_ops:
            service.create(
                system_identity,
                {
                    "id": op["id"],
                    "scheme": op["scheme"],
                    "subject": op["subject"],
                }
            )

    def _rename_rdm_subjects(self):
        """Rename subjects in the Subjects entries."""
        service = current_service_registry.get("subjects")
        rename_ops = filter_ops_by_type(self._ops_data, "rename")
        for op in rename_ops:
            service.update(
                system_identity,
                op["id"],
                {
                    "id": op["id"],
                    "scheme": op["scheme"],
                    "subject": op["new_subject"]
                }
            )

    def _update_rdm_records(self):
        """Execute operations (replace/remove/rename) on RDM records."""
        entries = get_records_to_update(self._ops_data, data_cls=RDMRecord)
        for record in entries:
            update_rdm_record(
                record,
                ops_data=self._ops_data,
                logger=self._logger,
                keep_trace=self._keep_trace
            )

        # Don't keep trace for drafts
        entries = get_records_to_update(self._ops_data, data_cls=RDMDraft)
        for draft in entries:
            update_rdm_record(
                draft,
                ops_data=self._ops_data,
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
            op["id"] for op in self._ops_data
            if op.get("type") in ["remove", "replace"]
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
