# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH term loader."""

import json


class MeSH:
    """MeSH term extractor."""

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
        """Iterate over terms."""
        yield from MeSH.load(self._filepath, self._filter)


def topic_filter(record):
    """Filters for topical terms."""
    return record.get("DC") == "1"


def read_jsonl(filepath):
    """KISS jsonl file reader."""
    with open(filepath) as f:
        for line in f:
            yield json.loads(line)
