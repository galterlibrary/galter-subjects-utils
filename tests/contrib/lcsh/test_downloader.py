# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from galter_subjects_utils.contrib.lcsh.downloader import LCSHDownloader

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
        downloader.terms_filepath
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
        downloader.terms_filepath
    )
