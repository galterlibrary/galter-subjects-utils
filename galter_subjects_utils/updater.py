# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Terms updater."""

import copy
from dataclasses import dataclass

from invenio_access.permissions import system_identity
from invenio_db import db
from invenio_rdm_records.records import RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_records_resources.services.uow import RecordCommitOp
from invenio_search.engine import dsl
from sqlalchemy import bindparam, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB


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
            if op_data.get("keep_trace"):
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


def get_records_to_update(ops_data):
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
        select(RDMRecord.model_cls)
        .where(at_least_1_subject_targeted(targeted_ids))
    )

    result = (
        RDMRecord(obj.data, model=obj) for obj in db.session.scalars(stmt)
    )

    return result


@dataclass
class KeepTrace:
    """Keeps trace of subject at field in record using template."""

    field: str  # dotted path to field
    template: str

    def trace(self, record, subject):
        """Save expanded `self.template` at `self.field` in record."""
        if not self.field or not self.template or not subject:
            return

        final_dict = self.find_final_dict(record)
        self.assign_template(final_dict, subject)

    def find_final_dict(self, record):
        """Find or create final dict by following `field`."""
        obj = record
        keys = self.field.split(".")

        for key in keys[:-1]:
            got = obj.get(key)
            if isinstance(got, dict):
                obj = got
            elif got is None:
                new_dict = {}
                obj[key] = new_dict
                obj = new_dict
            elif isinstance(got, list):
                new_dict = {}
                got.append(new_dict)
                obj = new_dict
            else:
                break

        assert isinstance(obj, dict), f"KeepTrace.field '{self.field}' is invalid."  # noqa
        return obj

    def assign_template(self, dict_, subject):
        """Assign expanded template."""
        final_key = self.field.split(".")[-1]
        dict_[final_key] = self.template.format(subject=subject)


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
        """Execute operations (replace/remove) on RDM records."""
        for record in get_records_to_update(self._ops_data):
            update_rdm_record(
                record,
                ops_data=self._ops_data,
                logger=self._logger,
                keep_trace=self._keep_trace
            )

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
