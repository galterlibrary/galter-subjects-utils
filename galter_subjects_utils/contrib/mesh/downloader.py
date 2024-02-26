# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Download MeSH files."""

from datetime import date

from galter_subjects_utils.downloader import download_file


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
        current_year = str(date.today().year)
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
        """Download MeSH files of interest."""
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
