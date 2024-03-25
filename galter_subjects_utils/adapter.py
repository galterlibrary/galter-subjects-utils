# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic download functionality."""

from .types_internal import Subject


def converted_to_subjects(rdm_iter, prefix):
    """Adapts an RDMSubject ("Converted") iterable into a Subject iterable.

    :param rdm_iter: Iterable[RDMSubject]

    RDMSubject:

    {
        "id": "<prefix>...",
        "scheme": "...",
        "subject": "..."
    }

    :return: Iterable[Subject]

    Subject:

        id (minus the <prefix> part)
        label
    """
    len_prefix = len(prefix)
    return (
        Subject(
            id=e["id"][len_prefix:] if e["id"].startswith(prefix) else e["id"],
            label=e["subject"]
        ) for e in rdm_iter
    )
