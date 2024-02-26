# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Read MeSH files."""

import re

# Utilities


def topic_filter(record):
    """Filters for topical terms."""
    return record.get("DC") == "1"


# Readers


class MeSH:
    """MeSH term extractor.

    DEPRECATED. Will be removed in following versions.
    """

    @classmethod
    def load(cls, filepath, filter=lambda r: True):
        """Iterate over selected MeSH terms."""
        with open(filepath, 'r') as f:
            record = {}

            for line in f.readlines():
                if "=" not in line:
                    continue

                key, value = [p.strip() for p in line.split("=", maxsplit=1)]
                cls.update_record(record, key, value)

                # Assumes always ends with UI
                if key == "UI":
                    if filter(record):
                        yield record
                    record = {}

    @classmethod
    def update_record(cls, record, key, value):
        """Update the value of a key in the MeSH record.

        We deal with special cases of interest here.
        """
        if key == "AQ":
            record[key] = [q.strip() for q in value.split()]
        else:
            record[key] = value


class MeSHReader:
    """MeSH Reader."""

    def __init__(self, filepath, filter=lambda r: True):
        """Constructor."""
        self._filepath = filepath
        self._filter = filter

    def __iter__(self):
        """Iterate over terms.

        Deprecated.
        """
        yield from self.read()

    def read(self):
        """Alias for __iter__ (for now)."""
        with open(self._filepath, 'r') as f:
            record = {}

            for line in f:
                if "=" not in line:
                    continue

                key, value = [p.strip() for p in line.split("=", maxsplit=1)]
                self.update_record(record, key, value)

                # Assumes always ends with UI
                if key == "UI":
                    if self._filter(record):
                        yield record
                    record = {}

    def update_record(cls, record, key, value):
        """Update the value of a key in the MeSH record.

        We deal with special cases of interest here.
        """
        if key == "AQ":
            record[key] = [q.strip() for q in value.split()]
        else:
            record[key] = value


class MeSHNewReader:
    """Parser for MeSH new file."""

    def __init__(self, filepath):
        """Constructor."""
        self.filepath = filepath

    def read(self):
        """Read iteratively 'meshnew' file.

        This is a very simple parser that takes advantage of the
        structure of 'meshnew' files.

        Design:
        - lazy load file to reduce memory footprint during read
        """
        with open(self.filepath, 'r') as f:
            entry = {}
            for line in f:
                line = line.strip()
                # partition always yields 3-tuple, values may be '' though
                lv, dash, rv = line.partition("-")
                if dash == "-":
                    entry.update({lv.strip(): rv.strip()})
                else:
                    if entry:
                        yield entry
                        entry = {}
            if entry:
                yield entry


class MeSHReplaceReader:
    """Parser for MeSH replace file."""

    def __init__(self, filepath):
        """Constructor."""
        self.filepath = filepath

    def read(self):
        """Read 'replace' file.

        This is a very simple parser that takes advantage of the
        structure of 'replace' files.

        Design:
        - lazy load file to reduce memory footprint during read
        Output:
            yield
            {
                "MH OLD": "...",
                "MH NEW": "...",
                "delete": "...",
                "status": "...",
            }
        """
        with open(self.filepath, 'r') as f:
            entry = {}
            for line in f:
                line = line.strip()
                valid_start = (
                    line.startswith("MH OLD =") or
                    line.startswith("MH NEW =")
                )
                if valid_start:
                    lv, eq, rv = line.partition("=")
                    lv = lv.strip()
                    rv = rv.strip()

                    if line.startswith("MH OLD ="):
                        m = re.search(r"(#?) \[(\w\*?)?\]$", rv)
                        if not m:
                            raise Exception(f"Malformed line: {line}")
                        piece = {
                            lv: rv[:m.start()].strip(),
                            "delete": m.group(1) or "",
                            "status": m.group(2) or "",
                        }
                    else:
                        piece = {lv: rv}

                    entry.update(piece)

                else:
                    if entry:
                        yield entry
                        entry = {}

            if entry:
                yield entry
