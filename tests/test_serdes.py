#
# Copyright (C) 2026 Northwestern University.
#
# invenio-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.


"""Test delta generators."""

import pytest

from galter_subjects_utils.serdes import DeltaSerdes, SubjectRDMSerdes
from galter_subjects_utils.types_internal import Delta, Subject


@pytest.fixture()
def subject_A():
    return Subject(
        id="https://id.example.org/subject_a",
        scheme="SCHEME_A",
        label="Subject A",
    )


@pytest.fixture()
def subject_A_scheme_and_label_changed(subject_A):
    return Subject(
        id=subject_A.id,
        scheme="SCHEME_A_CHANGED",
        label="Subject A changed",
    )


@pytest.fixture()
def subject_B():
    return Subject(
        id="https://id.example.org/subject_b",
        scheme="SCHEME_B",
        label="Subject B",
    )


@pytest.fixture()
def subject_C():
    return Subject(
        id="https://id.example.org/subject_c",
        scheme="SCHEME_A",
        label="Subject C",
    )


@pytest.fixture()
def subject_D():
    return Subject(
        id="https://id.example.org/subject_d",
        scheme="SCHEME_A",
        label="Subject D",
    )


@pytest.fixture()
def deltas_serialized():
    return


@pytest.fixture()
def deltas(
    subject_A,
    subject_A_scheme_and_label_changed,
    subject_B,
    subject_C,
    subject_D,
):
    return [
        Delta(type="add", subjects_dst=(subject_B,), keep_trace=False),
        Delta(
            type="edit",
            subject_src=subject_A,
            subjects_dst=(subject_A_scheme_and_label_changed,),
            keep_trace=True,
        ),
        Delta(
            type="replace",
            subject_src=subject_C,
            subjects_dst=(subject_A_scheme_and_label_changed, subject_B),
            keep_trace=False,
        ),
        Delta(
            type="remove",
            subject_src=subject_D,
            keep_trace=False,
        ),
    ]


def test_delta_serdes_deserialize(
    deltas,
):
    serdes = DeltaSerdes()
    deltas_serialized = [
        {
            "type": "add",
            # id_src, scheme_src, subject_src could be absent or present
            "id_src": "",
            "scheme_src": "",
            "subject_src": "",
            "id_dst": "https://id.example.org/subject_b",
            "scheme_dst": "SCHEME_B",
            "subject_dst": "Subject B",
            "keep_trace": "N",
        },
        {
            "type": "edit",
            "id_src": "https://id.example.org/subject_a",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject A",
            "id_dst": "",  # could be empty and rely on id_src
            "scheme_dst": "SCHEME_A_CHANGED",
            "subject_dst": "Subject A changed",
            "keep_trace": "Y",
        },
        {
            "type": "replace",
            "id_src": "https://id.example.org/subject_c",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject C",
            "id_dst": "https://id.example.org/subject_a\nhttps://id.example.org/subject_b",  # noqa
            "scheme_dst": "SCHEME_A_CHANGED\nSCHEME_B",
            "subject_dst": "Subject A changed\nSubject B",
            "keep_trace": "N",
        },
        {
            "type": "remove",
            "id_src": "https://id.example.org/subject_d",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject D",
            # unecessary keys can be absent or present:
            # "id_dst": "",
            # "scheme_dst": "",
            # "subject_dst": "",
            "keep_trace": "N",
        },
    ]

    result = [serdes.deserialize(d) for d in deltas_serialized]

    assert deltas == result


def test_delta_serdes_serialize(
    deltas,
):
    serdes = DeltaSerdes()

    result = [serdes.serialize(d) for d in deltas]

    # diferent than above, because serializes more compactly than what
    # a csv-read row looks like
    deltas_serialized = [
        {
            "type": "add",
            "id_dst": "https://id.example.org/subject_b",
            "scheme_dst": "SCHEME_B",
            "subject_dst": "Subject B",
            "keep_trace": "N",
        },
        {
            "type": "edit",
            "id_src": "https://id.example.org/subject_a",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject A",
            # "id_dst" absent from compact serialization
            "scheme_dst": "SCHEME_A_CHANGED",
            "subject_dst": "Subject A changed",
            "keep_trace": "Y",
        },
        {
            "type": "replace",
            "id_src": "https://id.example.org/subject_c",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject C",
            "id_dst": "https://id.example.org/subject_a\nhttps://id.example.org/subject_b",  # noqa
            "scheme_dst": "SCHEME_A_CHANGED\nSCHEME_B",
            "subject_dst": "Subject A changed\nSubject B",
            "keep_trace": "N",
        },
        {
            "type": "remove",
            "id_src": "https://id.example.org/subject_d",
            "scheme_src": "SCHEME_A",
            "subject_src": "Subject D",
            "keep_trace": "N",
        },
    ]
    assert deltas_serialized == result


def test_subjects_rdm_serdes():
    # list in case we want to add more cases down the road
    subjects_rdm = [
        {
            "id": "https://id.loc.gov/authorities/subjects/sh00000027",
            "scheme": "LCSH",
            "subject": "Beaver Creek (Yavapai County, Ariz.)",
        }
    ]

    serdes = SubjectRDMSerdes()
    deserialization = [serdes.deserialize(s) for s in subjects_rdm]

    expected = [
        Subject(
            id="https://id.loc.gov/authorities/subjects/sh00000027",
            scheme="LCSH",
            label="Beaver Creek (Yavapai County, Ariz.)",
        )
    ]
    assert expected == deserialization
