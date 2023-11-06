# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Download MeSH file."""

import gzip
import shutil

import requests


def download_file(url, dest):
    """Download a file."""
    with requests.get(url, stream=True) as req:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(req.raw, f)

    return dest


class MeSHDownloader:
    """Download MeSH files."""

    def __init__(self, directory, year, prefixes, cache=False):
        """Constructor."""
        self.directory = directory
        self.year = year
        self.prefix_to_filepath = {
            p: self.directory / f"{p}{year}.bin"
            for p in prefixes
        }
        self.cache = cache

        self.base_url = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/"  # noqa

    def download(self):
        """Download MeSH files of interest.

        :param year: str. year of the files to download.
        """
        for prefix in self.prefix_to_filepath.keys():
            if self.cache and self.prefix_to_filepath[prefix].exists():
                continue
            download_file(
                self.base_url + f"{prefix}{self.year}.bin",
                self.prefix_to_filepath[prefix],
            )


def extract_file(in_filepath, out_filepath):
    """Extract gzipped file."""
    with gzip.open(in_filepath, 'rb') as f_in:
        with open(out_filepath, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    return out_filepath


class LCSHDownloader:
    """Download LCSH file."""

    def __init__(self, directory, cache=False):
        """Constructor."""
        self.base_url = "https://id.loc.gov/download/authorities/subjects.skosrdf.jsonld.gz"  # noqa
        self.directory = directory
        self.filepath = self.directory / self.base_url.rsplit("/")[-1]
        self.cache = cache

    def download(self):
        """Download LCSH files of interest."""
        if not self.cache or not self.filepath.exists():
            download_file(self.base_url, self.filepath)
            # sneak extraction in caching: bit of a cheat, but ok for now
            extract_file(self.filepath, self.filepath.with_suffix(""))

        self.downloaded_filepath = self.filepath  # just a marker + future
        self.extracted_filepath = self.filepath.with_suffix("")
        return self.extracted_filepath
