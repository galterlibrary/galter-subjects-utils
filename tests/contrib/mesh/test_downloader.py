# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH-related download functionality."""

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from galter_subjects_utils.contrib.mesh.downloader import MeSHDownloader

# Helpers


@contextmanager
def fake_request_context(url, stream):
    """A faked requests.get context result."""
    filename = url.rsplit("/", 1)[-1]
    fp = Path(__file__).parent / f"data/fake_{filename}"

    FakeRequestContext = namedtuple("FakeRequestContext", ["raw"])

    with open(fp, "rb") as f:
        yield FakeRequestContext(raw=f)


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
