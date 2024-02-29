# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH-related conversion functionality."""

from galter_subjects_utils.contrib.mesh.converter import MeSHRDMConverter, \
    MeSHSubjectDeltasConverter, Subject


def test_converter():
    topics = [{
        'MH': 'Seed Bank',
        'DC': '1',
        'AQ': ['CL', 'EC'],
        'UI': 'D000068098'
    }]
    qualifiers_mapping = {
        "CL": {
            "QA": "CL",
            "SH": "classification",
            "UI": "Q000145"
        },
        "EC": {
            "QA": "EC",
            "SH": "economics",
            "UI": "Q000191"
        }
    }

    converter = MeSHRDMConverter(topics, qualifiers_mapping)
    objects = [o for o in converter]

    expected = [
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098',
            "scheme": "MeSH",
            "subject": "Seed Bank"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000145',
            "scheme": "MeSH",
            "subject": "Seed Bank/classification"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000191',
            "scheme": "MeSH",
            "subject": "Seed Bank/economics"
        },
    ]
    assert expected == objects


# MeSHSubjectDeltasConverter tests
# ===

# Helpers


def subject_unqualified():
    """Subject without qualifier."""
    return Subject(id="D000068098", label="Seed Bank")


def subject_qualified():
    """Subject with qualifier."""
    return Subject(id="D044127Q000941", label="Epigenesis, Genetic/ethics")


def subject_unqualified_present_only_in_dst():
    """Subject: unqualified + present only in dst."""
    return Subject(id="D000092002", label="Document Analysis")


def subject_qualified_present_only_in_dst():
    """Subject: qualified + present only in dst.

    This is also a topic that is not identified as being new in meshnew file
    or modified in replace file. To be discovered, the d<year> file would have
    to be read.
    """
    return Subject(id="D005654Q000187", label="Fundus Oculi/drug effects")


def subjects_renamed():
    """Subject and its renamed version."""
    return (
        Subject(
            id="D044467",
            label="American Native Continental Ancestry Group"
        ),
        Subject(id="D044467", label="American Indian or Alaska Native"),
    )


def subjects_qualified_renamed():
    """Qualified subject and its renamed version."""
    return (
        Subject(
            id="D044467Q000145",
            label="American Native Continental Ancestry Group/classification"
        ),
        Subject(
            id="D044467Q000145",
            label="American Indian or Alaska Native/classification"
        ),
    )


def subjects_qualified_replaced_already_present():
    """Subject and its replaced version.

    This function doesn't enforce an already present replaced version, but
    rather expects it to be used this way.
    The replaced version should be passed as part of the original subjects.
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


def subjects_replaced_newly_added():
    """Return a subject and its replaced version.

    This function doesn't enforce a newly added version, but
    rather expects it to be used this way. The replacement subject should not
    be passed as part of the original subjects.

    Subjects are made up because didn't find actual cases in last 3 years.
    """
    return (
        Subject(id="foo-before", label="Foo before"),
        Subject(id="foo-after", label="Foo after")
    )


def subjects_replaced_renamed():
    """Return a subject and its replaced version for the relabelled scenario.

    This is to be used for the case where a subject is replaced by
    a pre-existing but relabelled subject.
    """
    return (
        Subject(
            id="D018290Q000145",
            label="American Indians or Alaska Natives/classification"
        ),
        Subject(
            id="D044467Q000145",
            label="American Indian or Alaska Native/classification"
        )
    )


# Tests


def test_converter_add():
    """Test only addition scenarios."""
    src = [
        subject_unqualified()
    ]
    dst = [
        subject_unqualified(),
        subject_unqualified_present_only_in_dst(),
        subject_qualified_present_only_in_dst()
    ]
    replacement = {}

    converter = MeSHSubjectDeltasConverter(src, dst, replacement)

    add_ops = converter.convert()

    expected = [
        # delta op that could have been generated from just looking at
        # meshnew file
        {
            "type": "add",
            "id": "https://id.nlm.nih.gov/mesh/D000092002",
            "scheme": "MeSH",
            "subject": "Document Analysis"
        },
        # delta op that could not have been generated from just looking at
        # meshnew file
        {
            "type": "add",
            "id": "https://id.nlm.nih.gov/mesh/D005654Q000187",
            "scheme": "MeSH",
            "subject": "Fundus Oculi/drug effects"
        },
    ]
    assert expected == add_ops


def test_converter_rename():
    """Test rename scenarios only."""
    orig_subject, renamed_subject = subjects_renamed()
    src = [
        orig_subject,
        subject_unqualified()
    ]
    dst = [
        subject_unqualified(),
        renamed_subject,
    ]
    replacement = {}
    converter = MeSHSubjectDeltasConverter(src, dst, replacement)

    rename_ops = converter.convert()

    expected = [
        {
            "id": "https://id.nlm.nih.gov/mesh/D044467",
            "type": "rename",
            "scheme": "MeSH",
            "subject": "American Native Continental Ancestry Group",
            "new_subject": "American Indian or Alaska Native"
        },
    ]
    assert expected == rename_ops


def test_converter_replace():
    """Test replace scenarios only (sort-of)."""
    subject_replace_present_src, subject_replace_present_dst = (
        subjects_qualified_replaced_already_present()
    )
    subject_replace_add_src, subject_replace_add_dst = (
        subjects_replaced_newly_added()
    )
    subject_rename_src, subject_rename_dst = subjects_qualified_renamed()
    subject_replace_rename_src, subject_replace_rename_dst = (
        subjects_replaced_renamed()
    )
    src = [
        subject_replace_present_src,
        subject_unqualified(),
        subject_replace_present_dst,
        subject_replace_add_src,
        subject_replace_rename_src,
        subject_rename_src,
    ]
    dst = [
        subject_unqualified(),
        subject_replace_present_dst,
        subject_replace_add_dst,
        subject_replace_rename_dst,
        subject_rename_dst,
    ]
    replacements = {
        "Cervical Intraepithelial Neoplasia": "Uterine Cervical Dysplasia",
        "Foo before": "Foo after",
        "American Indians or Alaska Natives": "American Indian or Alaska Native",  # noqa
    }
    converter = MeSHSubjectDeltasConverter(src, dst, replacements)

    ops = converter.convert()

    expected = [
        # contains add and rename operations to account for replacement
        # scenarios
        {
            "id": "https://id.nlm.nih.gov/mesh/foo-after",
            "type": "add",
            "scheme": "MeSH",
            "subject": "Foo after"
        },
        {
            "id": "https://id.nlm.nih.gov/mesh/D044467Q000145",
            "type": "rename",
            "scheme": "MeSH",
            "subject": "American Native Continental Ancestry Group/classification",  # noqa
            "new_subject": "American Indian or Alaska Native/classification"
        },
        {
            "id": "https://id.nlm.nih.gov/mesh/D018290Q000145",
            "type": "replace",
            "scheme": "MeSH",
            "subject": "Cervical Intraepithelial Neoplasia/classification",
            "new_id": "https://id.nlm.nih.gov/mesh/D002578Q000145"
        },
        {
            "id": "https://id.nlm.nih.gov/mesh/foo-before",
            "type": "replace",
            "scheme": "MeSH",
            "subject": "Foo before",
            "new_id": "https://id.nlm.nih.gov/mesh/foo-after"
        },
        {
            "id": "https://id.nlm.nih.gov/mesh/D018290Q000145",
            "type": "replace",
            "scheme": "MeSH",
            "subject": "American Indians or Alaska Natives/classification",
            "new_id": "https://id.nlm.nih.gov/mesh/D044467Q000145"
        },
    ]
    assert expected == ops


def test_converter_remove():
    """Test remove scenarios only."""
    subject = subject_qualified()
    src = [subject]
    dst = []
    replacements = {}
    converter = MeSHSubjectDeltasConverter(src, dst, replacements)

    ops = converter.convert()

    expected = [
        {
            "id": "https://id.nlm.nih.gov/mesh/" + subject.id,
            "type": "remove",
            "scheme": "MeSH",
            "subject": "Epigenesis, Genetic/ethics",
        },
    ]
    assert expected == ops
