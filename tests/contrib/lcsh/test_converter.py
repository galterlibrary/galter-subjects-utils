# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

from pathlib import Path

from galter_subjects_utils.contrib.lcsh.converter import LCSHRDMConverter, \
    deprecated_to_replacements
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

    dicts_of_replacements = [d for d in deprecated_to_replacements(topics)]

    expected = [
        {
            "id": "https://id.loc.gov/authorities/subjects/sh00000273",
            "time": "2021-07-20T08:25:20",
            "subject": "Child concentration camp inmates",
            "new_id": "TODO:Expert:Fill me",
            "new_subject": "TODO:Expert:Fill me",
            "notes": "This authority record has been deleted because the heading is covered by the subject headings {Child internment camp inmates} (DLC)sh2021004026 and {Child Nazi concentration camp inmates} (DLC)sh2021004027"  # noqa
        }
    ]
    assert expected == dicts_of_replacements
