# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic reader functionality."""

import json


def read_jsonl(filepath):
    """KISS jsonl file reader."""
    with open(filepath) as f:
        for line in f:
            yield json.loads(line)


def mapping_by(iterable, by, keys=None):
    """Return dict out of `iterable` mapped by `by` with only `keys` chosen.

    If multiple entries in iterable have same `by` value, the last one will
    take precedence.

    :param iterable: iterable of dict
    :param by: key used to group
    :param keys: keys of each dict in iterable that should be kept
                 (with their values)
    :return: dict
    """
    return {
        d.get(by): {k: d.get(k) for k in keys} if keys else d
        for d in iterable
    }
