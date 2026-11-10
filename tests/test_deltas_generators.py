#
# Copyright (C) 2026 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.


"""Test delta generators."""

import pytest

from galter_subjects_utils.deltas_generators import (
    DeltasGenerator as DeltasGeneratorV2,
)
from galter_subjects_utils.types_internal import Subject


@pytest.fixture()
def subject_A():
    """Subject without qualifier."""
    return Subject(
        id="https://id.example.org/subject_a",
        scheme="SCHEME_A",
        label="Subject A",
    )


@pytest.fixture()
def subject_A_scheme_and_label_changed(subject_A):
    """Subject without qualifier."""
    return Subject(
        id=subject_A.id,
        scheme="SCHEME_A_CHANGED",
        label="Subject A changed",
    )


@pytest.fixture()
def subject_B():
    """Subject with qualifier."""
    return Subject(
        id="https://id.example.org/subject_b",
        scheme="SCHEME_B",
        label="Subject B"
    )


def test_deltas_generator_v2_add(subject_A, subject_B):
    src = [subject_A]
    dst = [subject_A, subject_B]
    replacement = {}

    deltor = DeltasGeneratorV2(src, dst, replacement)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "add",
            "id_dst": "https://id.example.org/subject_b",
            "scheme_dst": "SCHEME_B",
            "subject_dst": "Subject B",
        },
    ]
    assert expected == deltas


def test_deltas_generator_v2_edit(
    subject_A,
    subject_A_scheme_and_label_changed,
):
    src = [subject_A]
    dst = [subject_A_scheme_and_label_changed]
    replacement = {}

    deltor = DeltasGeneratorV2(src, dst, replacement)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "edit",
            "id_src": subject_A.id,
            "scheme_src": subject_A.scheme,
            "subject_src": subject_A.label,
            "scheme_dst": subject_A_scheme_and_label_changed.scheme,
            "subject_dst": subject_A_scheme_and_label_changed.label,
        },
    ]
    assert expected == deltas


def test_deltas_generator_v2_replace_by_subject_with_other_scheme(
    subject_A,
    subject_B,
):
    # This also covers replacement in general
    src = [subject_A, subject_B]
    dst = [subject_B]
    replacements = {
        subject_A: subject_B,
    }

    deltor = DeltasGeneratorV2(src, dst, replacements)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "replace",
            "id_src": subject_A.id,
            "scheme_src": subject_A.scheme,
            "subject_src": subject_A.label,
            "id_dst": subject_B.id,
            "scheme_dst": subject_B.scheme,
            "subject_dst": subject_B.label,
        },
    ]
    assert expected == deltas


def test_deltas_generator_v2_add_from_replacement(subject_A, subject_B):
    src = [subject_A]
    dst = []
    replacements = {
        subject_A: subject_B,
    }

    deltor = DeltasGeneratorV2(src, dst, replacements)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "add",
            "id_dst": subject_B.id,
            "scheme_dst": subject_B.scheme,
            "subject_dst": subject_B.label,
        },
        {
            "type": "replace",
            "id_src": subject_A.id,
            "scheme_src": subject_A.scheme,
            "subject_src": subject_A.label,
            "id_dst": subject_B.id,
            "scheme_dst": subject_B.scheme,
            "subject_dst": subject_B.label,
        },
    ]
    assert expected == deltas


def test_deltas_generator_v2_replace_by_multiple_subjects():
    assert False


def test_deltas_generator_v2_remove(subject_A):
    src = [subject_A]
    dst = []
    replacements = {}

    deltor = DeltasGeneratorV2(src, dst, replacements)
    deltas = list(deltor.iter_deltas())

    expected = [
        {
            "type": "remove",
            "id_src": subject_A.id,
            "scheme_src": subject_A.scheme,
            "subject_src": subject_A.label,
        },
    ]
    assert expected == deltas
