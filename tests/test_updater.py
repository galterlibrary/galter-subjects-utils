# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Conftest."""

import copy

import pytest
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDeletedError
from invenio_rdm_records.records import RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.contrib.subjects.api import Subject

from galter_subjects_utils.updater import SubjectDeltaUpdater


# Fixtures
@pytest.fixture(scope="module")
def subjects_service():
    return current_service_registry.get("subjects")


@pytest.fixture(scope="module")
def subjects(app, subjects_service):
    """A couple of subject records."""
    result = [
        subjects_service.create(
            system_identity,
            {
                "id": "http://example.org/foo/0",
                "scheme": "foo",
                "subject": "0",
            },
        ),
        subjects_service.create(
            system_identity,
            {
                "id": "http://example.org/foo/1",
                "scheme": "foo",
                "subject": "1",
            },
        ),
        subjects_service.create(
            system_identity,
            {
                "id": "http://example.org/foo/2",
                "scheme": "foo",
                "subject": "2",
            },
        ),
        subjects_service.create(
            system_identity,
            {
                "id": "http://example.org/bar/0",
                "scheme": "bar",
                "subject": "0",
            },
        )
    ]

    # Need to make sure records are indexed before subsequent interactions
    Subject.index.refresh()

    return result


@pytest.fixture(scope="module")
def operations_data():
    """Operations in data form."""
    return [
        {
            "type": "add",
            "scheme": "foo",
            "id": "http://example.org/foo/4",
            "subject": "4"
        },
        {
            "type": "rename",
            "scheme": "foo",
            "id": "http://example.org/foo/1",
            "new_subject": "One"
        },
        {
            "type": "remove",
            "scheme": "foo",
            "id": "http://example.org/foo/0",
        },
        {
            "type": "replace",
            "scheme": "foo",
            "id": "http://example.org/foo/2",
            "new_id": "http://example.org/foo/4",
            "new_subject": "4"
        },
    ]


@pytest.fixture(scope="module")
def records_data_w_subjects(create_record_data, minimal_record_input):
    """Records tagged with subjects."""
    result = []

    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {"id": "http://example.org/foo/1"},  # will be renamed
        {"id": "http://example.org/foo/2"},  # will be replaced
        {"id": "http://example.org/bar/0"},  # will be left alone
        {"subject": "a_keyword"},
    ]
    result += [create_record_data(system_identity, record_input)]

    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {"id": "http://example.org/foo/0"},  # will be removed
    ]
    result += [create_record_data(system_identity, record_input)]

    return result


@pytest.fixture(scope="module")
def update_result(
        running_app, subjects, records_data_w_subjects, operations_data):
    """Update results.

    This is actually the code under test. Because it does a lot, we create
    multiple tests that all test different aspects of its run.
    """
    executor = SubjectDeltaUpdater(operations_data)
    result = executor.update()

    # Really just needed for tests: OS indices are refreshed on an interval
    # longer than the queries we make in tests, so we have to force a refresh.
    RDMRecord.index.refresh()
    Subject.index.refresh()

    return result


# Test utilities
def any_contains(dict_, dicts):
    """Return bool if any dict in `dicts` contains `dict_`."""
    return any(dict_.items() <= d.items() for d in dicts)


# Tests
def test_update_on_subjects(update_result, subjects_service):
    # update_result is under test

    # at DB
    # -----
    # add
    assert subjects_service.read(system_identity, "http://example.org/foo/4")

    # rename
    subject_result = subjects_service.read(
        system_identity, "http://example.org/foo/1"
    )
    subject_dict = subject_result.to_dict()
    assert "One" == subject_dict["subject"]
    # what happens with other changes?

    # remove
    with pytest.raises(PIDDeletedError):
        subjects_service.read(system_identity, "http://example.org/foo/0")

    # replace
    with pytest.raises(PIDDeletedError):
        subjects_service.read(system_identity, "http://example.org/foo/2")

    # at index
    # --------
    # fields = None should give all fields
    subject_results = subjects_service.read_all(system_identity, fields=None)
    subjects_dict = subject_results.to_dict()
    hits = subjects_dict["hits"]["hits"]

    # add
    assert any_contains({"id": "http://example.org/foo/4"}, hits)
    # rename
    assert any_contains({"subject": "One"}, hits)
    # remove
    assert not any_contains({"id": "http://example.org/foo/0"}, hits)
    # replace
    assert not any_contains({"id": "http://example.org/foo/2"}, hits)


def test_update_on_records(update_result, records_data_w_subjects):
    records_service = current_service_registry.get("records")

    # at DB
    # -----
    # first record
    record_pid_0 = records_data_w_subjects[0].pid.pid_value
    record_result = records_service.read(system_identity, record_pid_0)
    record_dict = record_result.to_dict()
    subjects = record_dict["metadata"]["subjects"]
    assert 4 == len(subjects)
    # replace
    assert not any_contains({"id": "http://example.org/foo/2"}, subjects)
    assert any_contains({"id": "http://example.org/foo/4"}, subjects)
    # rename
    assert any_contains(
        {"id": "http://example.org/foo/1", "subject": "One"},
        subjects
    )
    # leave alone
    assert any_contains({"id": "http://example.org/bar/0"}, subjects)
    assert any_contains({"subject": "a_keyword"}, subjects)

    # second record
    # remove
    record_pid_1 = records_data_w_subjects[1].pid.pid_value
    record_result = records_service.read(system_identity, record_pid_1)
    record_dict = record_result.to_dict()
    subjects = record_dict["metadata"]["subjects"]
    assert 0 == len(subjects)  # only had the one removed subject

    # at index
    # --------
    record_results = records_service.read_all(system_identity, None)
    records_dict = record_results.to_dict()
    hits = records_dict["hits"]["hits"]
    # first record
    record_dict = next((r for r in hits if r.get("id") == record_pid_0), None)
    assert record_dict
    subjects = record_dict["metadata"]["subjects"]
    assert 4 == len(subjects)
    # replace
    assert not any_contains({"id": "http://example.org/foo/2"}, subjects)
    assert any_contains({"id": "http://example.org/foo/4"}, subjects)
    # rename
    assert any_contains(
        {"id": "http://example.org/foo/1", "subject": "One"},
        subjects
    )
    # leave alone
    assert any_contains({"id": "http://example.org/bar/0"}, subjects)
    assert any_contains({"subject": "a_keyword"}, subjects)

    # second record
    # remove
    record_dict = next((r for r in hits if r.get("id") == record_pid_1), None)
    assert record_dict
    subjects = record_dict["metadata"]["subjects"]
    assert 0 == len(subjects)  # only had the one removed subject


# def test_update_output(running_app, subjects):
