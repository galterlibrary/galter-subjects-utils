# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH-related conversion functionality."""

from galter_subjects_utils.contrib.mesh.converter import MeSHRDMConverter


def test_converter():
    topics = [{
        'MH': 'Seed Bank',
        'DC': '1',
        'AQ': ['CL', 'EC'],
        'UI': 'D000068098'
    }]
    qualifiers_mapping = {
        "CL": {
            "QA": "CL",
            "SH": "classification",
            "UI": "Q000145"
        },
        "EC": {
            "QA": "EC",
            "SH": "economics",
            "UI": "Q000191"
        }
    }

    converter = MeSHRDMConverter(topics, qualifiers_mapping)
    objects = [o for o in converter]

    expected = [
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098',
            "scheme": "MeSH",
            "subject": "Seed Bank"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000145',
            "scheme": "MeSH",
            "subject": "Seed Bank/classification"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000191',
            "scheme": "MeSH",
            "subject": "Seed Bank/economics"
        },
    ]
    assert expected == objects
