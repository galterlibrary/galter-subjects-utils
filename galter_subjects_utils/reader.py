# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic reader functionality."""

import csv
import json

from invenio_db import db
from invenio_vocabularies.contrib.subjects.models import SubjectsMetadata
from sqlalchemy import bindparam, select, text


def read_jsonl(filepath):
    """KISS jsonl file reader."""
    with open(filepath) as f:
        for line in f:
            yield json.loads(line)


def read_csv(filepath, reader_kwargs=None):
    """KISS csv reader."""
    reader_kwargs = reader_kwargs or {}
    with open(filepath) as f:
        reader = csv.DictReader(f, **reader_kwargs)
        yield from reader


def mapping_by(iterable, by, keys=None):
    """Return dict out of `iterable` mapped by `by` with only `keys` chosen.

    If multiple entries in iterable have same `by` value, the last one will
    take precedence.

    :param iterable: iterable of dict
    :param by: key used to group
    :param keys: keys of each dict in iterable that should be kept
                 (with their values)
    :return: dict
    """
    return {
        d.get(by): {k: d.get(k) for k in keys} if keys else d
        for d in iterable
    }


def get_rdm_subjects(scheme):
    """Return all rdm subjects of corresponding scheme."""
    is_scheme = (
        text('json::json->>\'scheme\' = :scheme')
        .bindparams(
            bindparam(
                "scheme",
                value=scheme,
            )
        )
    )

    stmt = (
        select(SubjectsMetadata.json)
        .where(is_scheme)
    )

    return db.session.scalars(stmt)
