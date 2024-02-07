# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test generic writer functionality."""

from pathlib import Path

from galter_subjects_utils.reader import read_jsonl
from galter_subjects_utils.writer import SubjectDeltaLogger, write_jsonl


def test_write():
    filepath = Path(__file__).parent / "test_subjects_mesh.jsonl"
    entries = [
        {
            "id": 'D000015',
            "tags": ["mesh"],
            "title": {
                "en": 'Abnormalities, Multiple'
            }
        },
        {
            "id": 'D000068098',
            "tags": ["mesh"],
            "title": {
                "en": 'Seed Bank'
            }
        },
        {
            "id": 'D005368',
            "tags": ["mesh"],
            "title": {
                "en": 'Filariasis'
            }
        }
    ]

    write_jsonl(entries, filepath)

    read_entries = list(read_jsonl(filepath))
    assert entries == read_entries

    filepath.unlink(missing_ok=True)


def test_logging_corner_cases():
    # Log exception messages
    logger = SubjectDeltaLogger()

    delta = {
        "type": "remove",
        "scheme": "foo",
        "id": "A",
    }

    try:
        raise Exception("msg")
    except Exception as e:
        logger.log("abcde-54321", error=str(e))
        logger.flush()

    entries = logger.read()
    assert "msg" == entries[0]["error"]

    # Log multiple deltas
    logger = SubjectDeltaLogger()
    deltas = [
        {
            "type": "remove",
            "scheme": "foo",
            "id": "A",
        },
        {
            "type": "replace",
            "scheme": "foo",
            "id": "B",
            "new_id": "D",
        },
    ]
    logger.log("abcde-12345", deltas[0])
    logger.log("abcde-12345", deltas[1])
    logger.flush()
    entries = logger.read()
    deltas = "A -> X + B -> D"
    assert deltas == entries[0]["deltas"]
    assert "" == entries[0]["error"]
