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
from datetime import date

import requests


def download_file(url, dest):
    """Download a file."""
    with requests.get(url, stream=True) as req:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(req.raw, f)

    return dest


class MeSHDownloader:
    """Download MeSH files."""

    terms_filename_tmpl = "d{year}.bin"
    qualifiers_filename_tmpl = "q{year}.bin"
    new_filename_tmpl = "meshnew{year}.txt"
    replace_filename_tmpl = "replace{year}.txt"

    def __init__(self, directory, year, cache=False):
        """Constructor."""
        self.directory = directory
        self.year = str(year)
        self.cache = cache

        self.base_url = "https://nlmpubs.nlm.nih.gov/projects/mesh"

    def file_urls(self):
        """List of files to download."""
        current_year = date.today().year
        url_parent_segment = "MESH_FILES" if self.year == current_year else self.year  # noqa
        base_url = self.base_url + "/" + url_parent_segment

        urls = []

        # asciimesh files
        base_url_asciimesh = base_url + "/" + "asciimesh"
        urls += [
            base_url_asciimesh + "/" + fn_tmpl.format(year=self.year)
            for fn_tmpl in [
                self.terms_filename_tmpl,
                self.qualifiers_filename_tmpl
            ]
        ]

        # newterms files
        base_url_newterms = base_url + "/" + "newterms"
        urls += [
            base_url_newterms + "/" + fn_tmpl.format(year=self.year)
            for fn_tmpl in [
                self.new_filename_tmpl,
                self.replace_filename_tmpl
            ]
        ]

        return urls

    def download(self):
        """Download MeSH files of interest.

        :param year: str. year of the files to download.
        """
        # files to download
        urls = self.file_urls()

        for url in urls:
            dest_path = self.directory / url.rsplit("/", 1)[-1]
            if self.cache and dest_path.exists():
                continue
            download_file(url, dest_path)

    @property
    def terms_filepath(self):
        """Downloaded terms filepath."""
        return self.directory / self.terms_filename_tmpl.format(year=self.year)

    @property
    def qualifiers_filepath(self):
        """Downloaded qualifiers filepath."""
        return self.directory / self.qualifiers_filename_tmpl.format(year=self.year)  # noqa

    @property
    def new_filepath(self):
        """Downloaded meshnew filepath."""
        return self.directory / self.new_filename_tmpl.format(year=self.year)

    @property
    def replace_filepath(self):
        """Downloaded replace filepath."""
        return self.directory / self.replace_filename_tmpl.format(year=self.year)  # noqa


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
