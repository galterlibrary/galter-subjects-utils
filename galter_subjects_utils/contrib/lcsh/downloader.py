# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Download LCSH files."""

from galter_subjects_utils.downloader import download_file, extract_file


class LCSHDownloader:
    """Download LCSH file."""

    def __init__(self, directory, cache=False):
        """Constructor."""
        self.base_url = "https://id.loc.gov/download/authorities/subjects.skosrdf.jsonld.gz"  # noqa
        self.directory = directory
        self.cache = cache

    @property
    def downloaded_filepath(self):
        """Filepath of downloaded gzipped file."""
        return self.directory / self.base_url.rsplit("/")[-1]

    @property
    def terms_filepath(self):
        """Filepath of unzipped terms file."""
        return self.downloaded_filepath.with_suffix("")

    def download(self):
        """Download LCSH files of interest."""
        if not self.cache or not self.downloaded_filepath.exists():
            download_file(self.base_url, self.downloaded_filepath)
            # sneak extraction in caching: bit of a cheat, but ok for now
            extract_file(
                self.downloaded_filepath, self.terms_filepath
            )
