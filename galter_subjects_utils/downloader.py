# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Download MeSH file."""

import shutil

import requests


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
            self.download_file(
                self.base_url + f"{prefix}{self.year}.bin",
                self.prefix_to_filepath[prefix],
            )

    def download_file(self, url, dest):
        """Download a file."""
        with requests.get(url, stream=True) as req:
            with open(dest, 'wb') as f:
                shutil.copyfileobj(req.raw, f)

        return dest
