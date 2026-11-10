#
# Copyright (C) 2026 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.


"""Test delta generators."""

from galter_subjects_utils.deltas_generators import (
    DeltasGenerator as DeltasGenerator2,
)
from galter_subjects_utils.types_internal import Subject


def test_deltas_generator_v2_replace_by_subject_with_other_scheme():
    subject_scheme_a_to_replace_by_subject_scheme_b = Subject(
        id="https://id.example.org/subject-scheme-A-to-replace-by-subject-scheme-B",  # noqa
        scheme="SCHEME A",
        label="Subject scheme A to replace by subject scheme B",
    )
    subject_scheme_b = Subject(
        id="https://id.example.org/subject-scheme-B",
        scheme="SCHEME B",
        label="Subject scheme B",
    )
    src = [subject_scheme_a_to_replace_by_subject_scheme_b, subject_scheme_b]
    dst = [subject_scheme_b]
    replacements = {
        subject_scheme_a_to_replace_by_subject_scheme_b: subject_scheme_b,
    }

    deltor = DeltasGenerator2(src, dst, replacements)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "replace",
            "id_src": "https://id.example.org/subject-scheme-A-to-replace-by-subject-scheme-B",  # noqa
            "scheme_src": "SCHEME A",
            "subject_src": "Subject scheme A to replace by subject scheme B",
            "id_dst": "https://id.example.org/subject-scheme-B",
            "scheme_dst": "SCHEME B",
            "subject_dst": "Subject scheme B",
        },
    ]
    assert expected == deltas


def test_deltas_generator_v2_add_from_replacement():
    assert False
    # Questions
    # what hapens when replacing by subject not in dst?
    # dst = []

    # deltor = DeltasGenerator2(src, dst, replacements)
    # ops = deltor.generate()

    # expected = [
    #     # contains add and rename operations to account for replacement
    #     # scenarios
    #     {
    #         "type": "add",
    #         "id_dst": "https://id.example.org/scheme/subject-scheme-B",
    #         "scheme_dst": "SCHEME B",
    #         "subject_dst": "Subject scheme B",
    #     },
    #     {
    #         "type": "replace",
    #         "id_src": "https://id.example.org/scheme/subject-scheme-A-to-replace-by-subject-scheme-B",  # noqa
    #         "scheme_src": "SCHEME A",
    #         "subject_src": "Subject scheme A to replace by subject scheme B",
    #         "id_dst": "https://id.example.org/scheme/subject-scheme-B",
    #         "scheme_dst": "SCHEME B",
    #         "subject_dst": "Subject scheme B",
    #     },
    # ]
    # assert expected == ops


def test_deltas_generator_v2_replace_by_multiple_subjects():
    assert False
