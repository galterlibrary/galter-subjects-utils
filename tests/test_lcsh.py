# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from galter_subjects_utils.converter import LCSHRDMConverter
from galter_subjects_utils.downloader import LCSHDownloader
from galter_subjects_utils.reader import read_jsonl
from galter_subjects_utils.writer import write_jsonl

# Helpers


@contextmanager
def fake_request_context(url, stream):
    fp = Path(__file__).parent / "data/fake_lcsh.skosrdf.jsonld.gz"
    FakeRequestContext = namedtuple("FakeRequestContext", ["raw"])
    with open(fp, "rb") as f:
        yield FakeRequestContext(raw=f)


# Tests


@mock.patch('galter_subjects_utils.downloader.requests.get')
def test_downloader(patched_get, tmp_path):
    # patch requests.get to return files
    patched_get.side_effect = fake_request_context
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    # No cache by default
    downloader = LCSHDownloader(directory=downloads_dir)
    downloader.download()

    patched_get.assert_called()
    assert (
        downloads_dir / "subjects.skosrdf.jsonld.gz" ==
        downloader.downloaded_filepath
    )
    assert (
        downloads_dir / "subjects.skosrdf.jsonld" ==
        downloader.extracted_filepath
    )

    # With cache
    patched_get.reset_mock()
    downloader = LCSHDownloader(directory=downloads_dir, cache=True)
    downloader.download()

    patched_get.assert_not_called()
    assert (
        downloads_dir / "subjects.skosrdf.jsonld.gz" ==
        downloader.downloaded_filepath
    )
    assert (
        downloads_dir / "subjects.skosrdf.jsonld" ==
        downloader.extracted_filepath
    )


def test_converter():
    # File is setup to test
    # - regular entries
    # - deprecated entry that is ignored
    # - entry with multiple labels (take the last)
    filepath = Path(__file__).parent / "data" / "fake_lcsh.skosrdf.jsonld"
    topics = list(read_jsonl(filepath))
    converter = LCSHRDMConverter(topics)

    objects = [o for o in converter]

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
    assert expected == objects


def test_write():
    filepath = Path(__file__).parent / "test_subjects_lcsh.jsonl"
    entries = [
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
            "id": 'https://id.loc.gov/authorities/subjects/sh00000275',
            "scheme": "LCSH",
            "subject": "Shell Lake (Wis. : Lake)"
        },
        {
            "id": 'https://id.loc.gov/authorities/subjects/sh00008126',
            "scheme": "LCSH",
            "subject": "Half-Circle \"V\" Ranch (Wyo.)"
        },
    ]

    write_jsonl(entries, filepath)

    read_entries = list(read_jsonl(filepath))
    assert entries == read_entries

    filepath.unlink(missing_ok=True)
