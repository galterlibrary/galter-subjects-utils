# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Adapters to convert between different outputs and inputs."""


def generate_replacements(replace_iter):
    """Converts a replace iterable into a replacement dict.

    :param replace_iter: Iterable[LCSHReplaceEntry]

    LCSHReplaceEntry:

    {
        "id": "...",
        "time": "...",
        "subject": "...",
        "new_id": "...",
        "new_subject": "...",
        "notes": "...",
    }
    """
    return {
        e["subject"]: e["new_subject"] for e in replace_iter
        if e["new_subject"]
    }
