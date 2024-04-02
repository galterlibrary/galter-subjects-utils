# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

from datetime import datetime
from pathlib import Path

from galter_subjects_utils.contrib.lcsh.converter import LCSHRDMConverter, \
    raw_to_deprecated
from galter_subjects_utils.reader import read_jsonl


def test_converter():
    # File is setup to test
    # - regular entries
    # - deprecated entry that is ignored
    # - entry with multiple labels (take the last)
    filepath = Path(__file__).parent / "data" / "fake_lcsh.skosrdf.jsonld"
    topics = list(read_jsonl(filepath))
    converter = LCSHRDMConverter(topics)

    dicts_of_lcsh_terms = [d for d in converter.convert()]

    expected = [
        {
            "id": 'https://id.loc.gov/authorities/subjects/sh00000011',
            "scheme": "LCSH",
            "subject": "ActionScript (Computer program language)"
        },
        {
            "id": 'https://id.loc.gov/authorities/subjects/sh00000014',
            "scheme": "LCSH",
            "subject": "Tacos"
        },
        {
            "id": 'https://id.loc.gov/authorities/subjects/sh90000997',
            "scheme": "LCSH",
            "subject": "Rooms"
        }
    ]
    assert expected == dicts_of_lcsh_terms


def test_deprecated():
    filepath = Path(__file__).parent / "data" / "fake_lcsh.skosrdf.jsonld"
    topics = list(read_jsonl(filepath))

    dicts_of_replacements = [d for d in raw_to_deprecated(topics)]

    expected = [
        # No clear new_id/new_subject
        {
            "id": "https://id.loc.gov/authorities/subjects/sh00000273",
            "time": "2021-07-20T08:25:20",
            "subject": "Child concentration camp inmates",
            "new_id": "",
            "new_subject": "",
            "notes": "This authority record has been deleted because the heading is covered by the subject headings {Child internment camp inmates} (DLC)sh2021004026 and {Child Nazi concentration camp inmates} (DLC)sh2021004027"  # noqa
        },
        # Clear new_id/new_subject
        {
            "id": "https://id.loc.gov/authorities/subjects/sh2008007279",
            "time": "2023-01-23T12:01:15",
            "subject": "Computer games industry",
            "new_id": "https://id.loc.gov/authorities/subjects/sh2006005259",
            "new_subject": "Video games industry",
            "notes": "This authority record has been deleted because the heading is covered by the subject heading {Video games industry} (DLC)sh2006005259"  # noqa
        },
        # Variation: strange formatting to account for
        {
            "id": "https://id.loc.gov/authorities/subjects/sh2006004185",
            "time": "2023-01-23T12:01:15",
            "subject": "Computer games--Law and legislation",
            "new_id": "https://id.loc.gov/authorities/subjects/sh85143203",
            "new_subject": "Video games--Law and legislation",
            "notes": "This authority record has been deleted because the heading is covered by the subject heading {Video games--Law and legislation} (DLC)sh 85143203"  # noqa
        },
        # Variation: different wording + no replacement subject
        {
            "id": "https://id.loc.gov/authorities/subjects/sh2022001344",
            "time": "2023-09-29T18:42:32",
            "subject": "Evangelisch-Lutherse Kerk (Netherlands)--Relations--Nederlandse Hervormde Kerk",  # noqa
            "new_id": "https://id.loc.gov/authorities/subjects/sh2022001319",
            "new_subject": "",
            "notes": "This authority record has been deleted because the heading is covered by an identical subject heading (DLC)sh2022001319"  # noqa
        },
    ]
    assert expected == dicts_of_replacements


def test_deprecated_since():
    filepath = Path(__file__).parent / "data" / "fake_lcsh.skosrdf.jsonld"
    topics = list(read_jsonl(filepath))

    dicts_of_replacements = [
        d for d in raw_to_deprecated(topics, datetime(2023, 9, 29))
    ]

    expected = [
        {
            "id": "https://id.loc.gov/authorities/subjects/sh2022001344",
            "time": "2023-09-29T18:42:32",
            "subject": "Evangelisch-Lutherse Kerk (Netherlands)--Relations--Nederlandse Hervormde Kerk",  # noqa
            "new_id": "https://id.loc.gov/authorities/subjects/sh2022001319",
            "new_subject": "",
            "notes": "This authority record has been deleted because the heading is covered by an identical subject heading (DLC)sh2022001319"  # noqa
        },
    ]
    assert expected == dicts_of_replacements
