# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test general reader functionality."""


from galter_subjects_utils.reader import get_rdm_subjects, mapping_by


def test_mapping_by():
    iterable = [
        {
            "RECTYPE": "D",
            "MH": "Volvox",
            "AQ": [
                "CH", "CL", "CY", "DE", "EN", "GD", "GE", "IM", "IP", "ME",
                "MI", "PH", "PS", "PY", "RE", "UL", "VI"
            ],
            "MN": "B01.875.150.950",
            "MH_TH": "NLM (1998)",
            "ST": "T002",
            "RN": "txid3066",
            "PI": "Algae, Green (1970-2003)",
            "MS": "A genus of GREEN ALGAE in the family Volvocaceae...",
            "PM": "2004; see ALGAE, GREEN 1998-2003",
            "HN": "2004; use ALGAE, GREEN 1998-2003",
            "MR": "20210630",
            "DA": "20030709",
            "DC": "1",
            "DX": "20040101",
            "UI": "D044446",
        },
        {
            "RECTYPE": "D",
            "MH": "American Native Continental Ancestry Group",
            "AQ": ["CL", "ED", "EH", "GE", "HI", "LJ", "PX", "SN"],
            "MN": "M01.686.508.150",
            "MH_TH": "NLM (2004)",
            "ST": "T098",
            "MS": "Individuals whose ancestral origins are in the ...",
            "PM": "2004",
            "HN": "2004",
            "DA": "20030709",
            "DC": "1",
            "DX": "20040101",
            "UI": "D044467",
        }
    ]

    mapping = mapping_by(iterable, by="UI", keys=["UI", "MH", "AQ"])

    expected = {
        "D044446": {
            "UI": "D044446",
            "MH": "Volvox",
            "AQ": [
                "CH", "CL", "CY", "DE", "EN", "GD", "GE", "IM", "IP", "ME",
                "MI", "PH", "PS", "PY", "RE", "UL", "VI"
            ],
        },
        "D044467": {
            "UI": "D044467",
            "MH": "American Native Continental Ancestry Group",
            "AQ": ["CL", "ED", "EH", "GE", "HI", "LJ", "PX", "SN"],
        }
    }
    assert expected == mapping


def test_get_rdm_subjects(running_app, create_subject_data):
    subjects = [
        create_subject_data(
            input_={
                "id": "http://example.org/foo/0",
                "scheme": "foo",
                "subject": "0",
            }
        ),
        create_subject_data(
            input_={
                "id": "http://example.org/foo/1",
                "scheme": "foo",
                "subject": "1",
            },
        ),
        create_subject_data(
            input_={
                "id": "http://example.org/foo/2",
                "scheme": "foo",
                "subject": "2",
            },
        ),
        create_subject_data(
            input_={
                "id": "http://example.org/bar/0",
                "scheme": "bar",
                "subject": "0",
            },
        )
    ]

    subjects = [s for s in get_rdm_subjects(scheme="foo")]
    assert 3 == len(subjects)
    assert {"0", "1", "2"} == {e["subject"] for e in subjects}
