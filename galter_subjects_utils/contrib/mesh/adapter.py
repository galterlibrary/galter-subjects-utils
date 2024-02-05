# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Adapters to convert between different outputs and inputs."""

from .converter import Subject


def generate_replacements(replace_iter):
    """Converts a replace iterable into a replacement dict.

    :param replace_iter: Iterable[ReplaceEntry]

    ReplaceEntry:

    {
        "MH OLD": "...",
        "MH NEW": "...",
        "delete": "...",
        "status": "...",
    }
    """
    return {
        e["MH OLD"]: e["MH NEW"] for e in replace_iter if e["delete"]
    }


def converted_to_subjects(rdm_iter):
    """Adapts an RDMSubject ("Converted") iterable into a Subject iterable.

    :param rdm_iter: Iterable[RDMSubject]

    RDMSubject:

    {
        "id": "https://id.nlm.nih.gov/mesh/...",
        "scheme": "...",
        "subject": "..."
    }

    :return: Iterable[Subject]

    Subject:

        id (minus the https://id.nlm.nih.gov/mesh/ part)
        label
    """
    prefix = "https://id.nlm.nih.gov/mesh/"
    len_prefix = len(prefix)
    return (
        Subject(
            id=e["id"][len_prefix:] if e["id"].startswith(prefix) else e["id"],
            label=e["subject"]
        ) for e in rdm_iter
    )
