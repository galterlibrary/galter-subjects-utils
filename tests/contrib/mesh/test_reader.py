# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH-related reading functionality."""

from pathlib import Path

from galter_subjects_utils.contrib.mesh.reader import MeSHNewReader, \
    MeSHReader, MeSHReplaceReader, topic_filter

# Utilities


def assert_includes(dicts, dict_cores):
    """Checks that each dict in dicts has the corresponding dict_core."""
    for d, dc in zip(dicts, dict_cores):
        for key, value in dc.items():
            assert value == d[key]

# Tests


def test_reader_descriptors_filter():
    filepath = Path(__file__).parent / "data" / "fake_d2022.bin"

    reader = MeSHReader(filepath, filter=topic_filter)
    topics = [t for t in reader]

    expected_cores = [
        {
            'MH': 'Seed Bank',
            'DC': '1',
            'AQ': ['CL', 'EC'],
            'UI': 'D000068098'
        },
        {
            'MH': 'Abbreviations as Topic',
            'DC': '1',
            'UI': 'D000004'
        },
        {
            'MH': 'Abdomen',
            'DC': '1',
            'AQ': ['AB', 'AH'],
            'UI': 'D000005'
        },
        {
            'MH': 'American Indians or Alaska Natives',
            'DC': '1',
            'AQ': ['CL', 'ED', 'EH', 'GE', 'HI', 'LJ', 'PX', 'SN'],
            'UI': 'D000086562'
        }
    ]
    assert_includes(topics, expected_cores)


def test_reader_qualifiers():
    filepath = Path(__file__).parent / "data" / "fake_q2023.bin"

    reader = MeSHReader(filepath)
    qualifiers = [q for q in reader]

    expected_cores = [
        {
            "QA": "AB",
            "SH": "abnormalities",
            "UI": "Q000002"
        },
        {
            "QA": "AH",
            "SH": "anatomy & histology",
            "UI": "Q000033"
        },
        {
            "QA": "CL",
            "SH": "classification",
            "UI": "Q000145"
        },
        {
            "QA": "EC",
            "SH": "economics",
            "UI": "Q000191"
        },
    ]
    assert_includes(qualifiers, expected_cores)


def test_new_reader():
    filepath = Path(__file__).parent / "data" / "fake_meshnew2023.txt"

    reader = MeSHNewReader(filepath)
    entries = [e for e in reader.read()]

    expected = [
        {
            "MH": "Document Analysis",
            "UI": "D000092002",
            "MN": "H1.770.644.241.850.375",
            "MS": "A form of qualitative research that uses a systematic procedure to analyze documentary evidence and answer specific research questions.",  # noqa
            "HN": "2023",
        },
        {
            "MH": "Family Structure",
            "UI": "D000092822",
            "MN": "F1.829.263.315.250",
            "MN": "I1.240.361.330",
            "MN": "I1.880.761.125",
            "MN": "I1.880.853.150.423.250",
            "MN": "N1.224.361.330",
            "MN": "N1.824.308.125",
            "MN": "N6.850.505.400.400.580",
            "MS": "Structural nature of relationships among members of a household typically in reference to a MINOR residing in the same home. More broadly any organizational framework that determines family membership, and the functions and hierarchical position of family members (https://eric.ed.gov/?qt=Family+Structure&ti=Family+Structure).",  # noqa
            "HN": "2023; for STEPFAMILY and FAMILY, RECONSTITUTED use FAMILY 1996-2022; for MATRIARCHY and PATRIARCHY use FAMILY CHARACTERISTICS 1995-2022",  # noqa
            "BX": "Family, Reconstituted",
            "BX": "Reconstituted Family",
            "BX": "Step-parent Family",
            "BX": "Stepfamily",
            "BX": "Stepparent Family",
        }
    ]
    assert expected == entries


def test_replace_reader():
    filepath = Path(__file__).parent / "data" / "fake_replace2023.txt"

    reader = MeSHReplaceReader(filepath)
    entries = [e for e in reader.read()]

    expected = [
        {
            "MH OLD": "Far East",
            "MH NEW": "Asia, Eastern",
            "delete": "",
            "status": "P",
        },
        {
            "MH OLD": "American Indians or Alaska Natives",
            "MH NEW": "American Indian or Alaska Native",
            "delete": "#",
            "status": "P",
        },
        {
            "MH OLD": "Asians",
            "MH NEW": "Asian People",
            "delete": "",
            "status": "N*",
        },
        {
            "MH OLD": "Whites",
            "MH NEW": "White People",
            "delete": "",
            "status": "P*",
        },
        {
            "MH OLD": "RNA, Guide",
            "MH NEW": "RNA, Guide, Kinetoplastida",
            "delete": "",
            "status": "",
        }
    ]
    assert expected == entries
