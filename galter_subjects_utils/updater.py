# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Terms updater."""

import copy

from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_pidstore.errors import PersistentIdentifierError
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records import RDMDraft, RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import RecordCommitOp
from sqlalchemy import and_, bindparam, delete, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB

from .keeptrace import KeepTrace


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

    # All side-effects
    records_service = current_service_registry.get("records")
    commit_op = RecordCommitOp(record, records_service.indexer)
    # the following on_register, on_commit don't use the uow object
    # so passing None is fine
    fake_uow = None
    try:
        commit_op.on_register(fake_uow)  # commits to DB
        commit_op.on_commit(fake_uow)  # reindexes in index
    except Exception as e:
        logger.log(record.pid.pid_value, error=str(e))
    finally:
        logger.flush()


def get_records_to_update(ops_data, data_cls):
    """Return data-layer records to update."""

    def get_targeted_ids(ops_data):
        relevant_ops = (
            filter_ops_by_type(ops_data, "replace") +
            filter_ops_by_type(ops_data, "remove") +
            filter_ops_by_type(ops_data, "rename")
        )
        return [op["id"] for op in relevant_ops]

    def at_least_1_subject_targeted(ids):
        """Where clause to get records with at least 1 relevant subject id.

        Only call this for non-empty `ids`, otherwise the resulting where
        clause is all-permissive.

        WARNING: This is very ugly and I don't know how to make it better.
                 We use RAW SQL to check for presence of id (@>). The syntax
                 is not great but it gives us what we want.
        """
        raw = [
            text(
                'json::jsonb->\'metadata\'->\'subjects\' @> :subject_id'
            ).bindparams(
                bindparam(
                    "subject_id",
                    value=[{"id": subject_id}],
                    unique=True,
                    type_=JSONB
                )
            ) for subject_id in ids
        ]
        return or_(*raw)

    targeted_ids = get_targeted_ids(ops_data)

    if not targeted_ids:
        return []

    stmt = (
        select(data_cls.model_cls)
        .where(at_least_1_subject_targeted(targeted_ids))
    )

    result = (
        data_cls(obj.data, model=obj) for obj in db.session.scalars(stmt)
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
        """Remove subjects from the Subjects entries."""
        service = current_service_registry.get("subjects")

        remove_ops = filter_ops_by_type(self._ops_data, "remove")
        replace_ops = filter_ops_by_type(self._ops_data, "replace")
        for op in remove_ops + replace_ops:
            try:
                service.delete(
                    system_identity,
                    op["id"]
                )
            except PersistentIdentifierError:
                # For any persistent identifier related problem
                # we just ignore it and make sure we can continue.
                # Main scenario is when a subject has already been
                # "service.delete"'d in which case its PID is only marked as
                # deleted which interferes with service.delete and
                # service.create.
                pass

            # Purge (completely delete) backing subject PID
            # This operation is idempotent.
            delete_pid_stmt = (
                delete(PersistentIdentifier)
                .where(
                    and_(
                        PersistentIdentifier.pid_type == "sub",
                        PersistentIdentifier.pid_value == op["id"],
                    )
                )
            )
            db.session.execute(delete_pid_stmt)
            db.session.commit()
