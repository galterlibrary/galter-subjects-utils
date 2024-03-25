# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic download functionality."""

import gzip
import shutil

import requests


def download_file(url, dest):
    """Download a file."""
    with requests.get(url, stream=True) as req:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(req.raw, f)

    return dest


def extract_file(in_filepath, out_filepath):
    """Extract gzipped file."""
    with gzip.open(in_filepath, 'rb') as f_in:
        with open(out_filepath, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    return out_filepath
