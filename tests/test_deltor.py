# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

from galter_subjects_utils.deltor import DeltasGenerator
from galter_subjects_utils.scheme import Scheme
from galter_subjects_utils.types_internal import Subject


def subject_A():
    """Subject without qualifier."""
    return Subject(id="subject_a", label="Subject A")


def subject_B():
    """Subject with qualifier."""
    return Subject(id="subject_b", label="Subject B")


class TestScheme(Scheme):
    """Test subjet kind."""

    def __init__(self):
        """Constructor"""
        super().__init__(
            name="SCHEME",
            prefix="https://id.example.org/scheme/",
        )


scheme_for_tests = TestScheme()


# Test Add


def test_deltor_add():
    """Test only addition scenarios."""
    src = [
        subject_A()
    ]
    dst = [
        subject_A(),
        subject_B(),
    ]
    replacement = {}

    deltor = DeltasGenerator(src, dst, scheme_for_tests, replacement)

    add_ops = deltor.generate()

    expected = [
        {
            "id": "https://id.example.org/scheme/subject_b",
            "type": "add",
            "scheme": "SCHEME",
            "subject": "Subject B"
        },
    ]
    assert expected == add_ops


# Test Rename


def subjects_renamed():
    """Subject and its renamed version."""
    return (
        Subject(id="subject_rename", label="Subject Before Rename"),
        Subject(id="subject_rename", label="Subject After Rename"),
    )


def test_deltor_rename():
    """Test rename scenarios only."""
    subject_original, subject_renamed = subjects_renamed()
    src = [
        subject_original,
        subject_A(),
    ]
    dst = [
        subject_A(),
        subject_renamed,
    ]
    replacement = {}
    deltor = DeltasGenerator(src, dst, scheme_for_tests, replacement)

    rename_ops = deltor.generate()

    expected = [
        {
            "id": "https://id.example.org/scheme/subject_rename",
            "type": "rename",
            "scheme": "SCHEME",
            "subject": "Subject Before Rename",
            "new_subject": "Subject After Rename"
        },
    ]
    assert expected == rename_ops


# Test remove


def test_deltor_remove():
    """Test remove scenarios only."""
    subject = subject_B()
    src = [subject]
    dst = []
    replacements = {}
    deltor = DeltasGenerator(src, dst, scheme_for_tests, replacements)

    ops = deltor.generate()

    expected = [
        {
            "id": "https://id.example.org/scheme/" + subject.id,
            "type": "remove",
            "scheme": "SCHEME",
            "subject": "Subject B",
        },
    ]
    assert expected == ops


# Test replace

def subjects_replaced_by_already_present():
    """Subject to be replaced and its replacer for the pre-existing scenario.

    This function doesn't enforce an already present replacer, but
    rather expects it to be used this way.
    The replacer should be passed as part of the source/original subjects.
    """
    return (
        Subject(
            id="D018290Q000145",
            label="Cervical Intraepithelial Neoplasia/classification"
        ),
        Subject(
            id="D002578Q000145",
            label="Uterine Cervical Dysplasia/classification"
        )
    )


def subjects_replaced_by_added():
    """Return a subject and its replacer for the added scenario.

    This function doesn't enforce a newly added replacer, but
    rather expects it to be used this way. The replacer subject should not
    be passed as part of the original subjects.

    Subjects are made up because didn't find actual cases in last 3 years.
    """
    return (
        Subject(
            id="subject-to-replace-by-added",
            label="Subject To Replace By Added"
        ),
        Subject(id="subject-replacer-added", label="Subject Replacer Added")
    )


def subjects_replaced_by_renamed():
    """Return a subject and its replacer for the relabelled scenario.

    This is to be used for the case where a subject is replaced by
    a pre-existing but relabelled subject.
    """
    subject_original, subject_renamed = subjects_renamed()
    return (
        Subject(
            id="subject-to-replace-by-renamed",
            label="Subject To Replace By Renamed"
        ),
        subject_renamed
    )


def test_deltor_replace():
    """Test replace scenarios only (sort-of)."""
    # Case 1: subject is replaced by already existing other subject
    subject_to_be_replaced_by_already_present, subject_replacer_already_present = (  # noqa
        subjects_replaced_by_already_present()
    )
    # Case 2: subject is replaced by newly added other subject
    subject_to_be_replaced_by_added, subject_replacer_added = (
        subjects_replaced_by_added()
    )
    # Case 3: subject is replaced by renamed other subject
    subject_original, subject_renamed = subjects_renamed()
    subject_to_be_replaced_by_renamed, subject_replacer_renamed = (
        subjects_replaced_by_renamed()
    )
    src = [
        subject_to_be_replaced_by_already_present,
        subject_replacer_already_present,
        subject_to_be_replaced_by_added,
        subject_to_be_replaced_by_renamed,
        subject_original,
    ]
    dst = [
        subject_replacer_already_present,
        subject_replacer_added,
        subject_replacer_renamed,
        subject_renamed,
    ]
    replacements = {
        subject_to_be_replaced_by_already_present.label: (
            subject_replacer_already_present.label
        ),
        subject_to_be_replaced_by_added.label: subject_replacer_added.label,
        subject_to_be_replaced_by_renamed.label: subject_replacer_renamed.label,  # noqa
    }
    deltor = DeltasGenerator(src, dst, scheme_for_tests, replacements)

    ops = deltor.generate()

    expected = [
        # contains add and rename operations to account for replacement
        # scenarios
        {
            "id": "https://id.example.org/scheme/subject-replacer-added",
            "type": "add",
            "scheme": "SCHEME",
            "subject": "Subject Replacer Added"
        },
        {
            "id": "https://id.example.org/scheme/subject_rename",
            "type": "rename",
            "scheme": "SCHEME",
            "subject": "Subject Before Rename",
            "new_subject": "Subject After Rename"
        },
        {
            # subject_to_be_replaced_by_already_present.id
            "id": "https://id.example.org/scheme/D018290Q000145",
            "type": "replace",
            "scheme": "SCHEME",
            # subject_to_be_replaced_by_already_present.label
            "subject": "Cervical Intraepithelial Neoplasia/classification",
            # subject_replacer_already_present.id
            "new_id": "https://id.example.org/scheme/D002578Q000145"
        },
        {
            "id": "https://id.example.org/scheme/subject-to-replace-by-added",
            "type": "replace",
            "scheme": "SCHEME",
            "subject": "Subject To Replace By Added",
            "new_id": "https://id.example.org/scheme/subject-replacer-added"
        },
        {
            "id": "https://id.example.org/scheme/subject-to-replace-by-renamed",  # noqa
            "type": "replace",
            "scheme": "SCHEME",
            "subject": "Subject To Replace By Renamed",
            "new_id": "https://id.example.org/scheme/subject_rename"
        },
    ]
    assert expected == ops
