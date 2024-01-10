# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH extractor."""

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from galter_subjects_utils.converter import MeSHRDMConverter
from galter_subjects_utils.downloader import MeSHDownloader
from galter_subjects_utils.reader import MeSHReader, read_jsonl, topic_filter
from galter_subjects_utils.writer import write_jsonl

# Helpers


@contextmanager
def fake_request_context(url, stream):
    """A faked requests.get context result."""
    filename = url.rsplit("/", 1)[-1]
    fp = Path(__file__).parent / f"data/mesh/fake_{filename}"

    FakeRequestContext = namedtuple("FakeRequestContext", ["raw"])

    with open(fp, "rb") as f:
        yield FakeRequestContext(raw=f)


def assert_includes(dicts, dict_cores):
    """Checks that each dict in dicts has the corresponding dict_core."""
    for d, dc in zip(dicts, dict_cores):
        for key, value in dc.items():
            assert value == d[key]


# Tests


@mock.patch('galter_subjects_utils.downloader.requests.get')
def test_downloader(patched_get, tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    # patch requests.get to return files
    patched_get.side_effect = fake_request_context

    # Testing the current_year variant seemed like it would lead to a test
    # mirror, so it has been tested manually instead. This really just tests
    # that we have the right name, interfaces and final files written to disk
    # in right location.
    downloader = MeSHDownloader(
        year="2023",
        directory=downloads_dir
    )
    downloader.download()

    patched_get.assert_called()
    assert (downloads_dir / "d2023.bin").exists()
    assert (downloads_dir / "q2023.bin").exists()
    assert (downloads_dir / "meshnew2023.txt").exists()
    assert (downloads_dir / "replace2023.txt").exists()


def test_reader_descriptors_filter():
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_d2022.bin"

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
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_q2023.bin"

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


def test_converter():
    mesh_topics = [{
        'MH': 'Seed Bank',
        'DC': '1',
        'AQ': ['CL', 'EC'],
        'UI': 'D000068098'
    }]
    mesh_qualifiers = [
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

    converter = MeSHRDMConverter(mesh_topics, mesh_qualifiers)
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
