# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Terms updater."""

from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_rdm_records.records import RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import RecordCommitOp
from sqlalchemy import bindparam, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB


def filter_ops_by_type(ops_data, _type):
    """Filter ops_data by _type."""
    return [op for op in ops_data if op.get("type") == _type]


def op_remove(subjects, op_data):
    """Remove subject in-place.

    This is actually a rare op, because usually subjects are replaced.

    op_data:

    ```python
        {
            "type": "remove",
            "scheme": "...",
            "id": "...",
        }
    ```
    """
    idx, subject_dict = next(
        ((i, s) for i, s in enumerate(subjects) if s.get("id") == op_data["id"]),  # noqa
        (-1, None)
    )
    if idx == -1:
        return
    subjects.pop(idx)
    return True


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
    idx, subject_dict = next(
        ((i, s) for i, s in enumerate(subjects) if s.get("id") == op_data["id"]),  # noqa
        (-1, None)
    )
    if idx == -1:
        return
    new_subject_dict = {
        **subject_dict,  # probably not needed
        "id": op_data["new_id"],
    }
    subjects[idx] = new_subject_dict
    return True


def apply_op_data_change(record, op_data, logger):
    """Apply operation change on record."""
    subjects = record["metadata"]["subjects"]
    applied = False
    if op_data.get("type") == "replace":
        applied = op_replace(subjects, op_data)
    elif op_data.get("type") == "remove":
        applied = op_remove(subjects, op_data)

    if applied:
        logger.log(record.pid.pid_value, delta=op_data)


def update_rdm_record(record, ops_data, logger):
    """Apply changes to record's subjects."""
    for op_data in ops_data:
        apply_op_data_change(record, op_data, logger)

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


def get_records_to_update(ops_data):
    """Return data-layer records to update."""

    def targeted_subjects(ops_data):
        # Only 'replace' and 'remove' need to alter rdm_records
        relevant_ops = (
            filter_ops_by_type(ops_data, "replace") +
            filter_ops_by_type(ops_data, "remove")
        )
        return [op["id"] for op in relevant_ops]

    def at_least_1_subject_targeted(ops_data):
        """Where clause to get records with at least 1 relevant subject.

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
            ) for subject_id in targeted_subjects(ops_data)
        ]
        return or_(*raw)

    stmt = (
        select(RDMRecord.model_cls)
        .where(at_least_1_subject_targeted(ops_data))
    )

    result = (
        RDMRecord(obj.data, model=obj) for obj in db.session.scalars(stmt)
    )

    return result


class SubjectDeltaUpdater:
    """Translates delta operations into actual changes."""

    def __init__(self, ops_data, logger):
        """Constructor."""
        self._ops_data = ops_data
        self._logger = logger

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
        """Execute operations (replace/remove) on RDM records."""
        for record in get_records_to_update(self._ops_data):
            update_rdm_record(record, self._ops_data, self._logger)

    def _remove_rdm_subjects(self):
        """Remove subjects from the Subjects entries."""
        service = current_service_registry.get("subjects")

        remove_ops = filter_ops_by_type(self._ops_data, "remove")
        replace_ops = filter_ops_by_type(self._ops_data, "replace")
        for op in remove_ops + replace_ops:
            service.delete(
                system_identity,
                op["id"]
            )
