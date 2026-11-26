#
# Copyright (C) 2024-2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test updater."""

import copy

import pytest
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_rdm_records.records import RDMDraft, RDMRecord
from invenio_records_resources.proxies import current_service_registry
from invenio_vocabularies.contrib.subjects.api import Subject as SubjectApi

from galter_subjects_utils.keeptrace import KeepTrace
from galter_subjects_utils.serdes import SubjectRDMSerdes
from galter_subjects_utils.types_internal import Delta, Subject
from galter_subjects_utils.updater import SubjectDeltaUpdater
from galter_subjects_utils.writer import SubjectDeltaLogger


# Fixtures
@pytest.fixture(scope="module")
def subjects_service(app):
    return current_service_registry.get("subjects")


@pytest.fixture(scope="module")
def subjects_internal():
    result = {
        f"http://example.org/foo/{i}": Subject(
            id=f"http://example.org/foo/{i}",
            scheme="foo",
            label=f"{i}",
        )
        for i in range(4)
    }
    # Relabelled foo1
    result.update({
        "http://example.org/foo/1-relabelled": Subject(
            id="http://example.org/foo/1",
            scheme="foo",
            label="One",
        ),
    })
    # Bars
    result.update({
        "http://example.org/bar/0": Subject(
            id="http://example.org/bar/0",
            scheme="bar",
            label="0",
        ),
    })
    # Zims
    result.update({
        "http://example.org/zim/0QA": Subject(
            id="http://example.org/zim/0QA",
            scheme="zim",
            label="0QA",
        ),
        "http://example.org/zim/0": Subject(
            id="http://example.org/zim/0",
            scheme="zim",
            label="0",
        ),
    })
    return result


@pytest.fixture(scope="module")
def subjects(app, subjects_service, subjects_internal):
    """A couple of subject records."""
    subject_rdm_serdes = SubjectRDMSerdes()
    result = [
        subjects_service.create(
            system_identity,
            subject_rdm_serdes.serialize(
                subjects_internal[f"http://example.org/foo/{i}"]
            )
        ) for i in range(3)
    ]

    result.append(
        subjects_service.create(
            system_identity,
            subject_rdm_serdes.serialize(
                subjects_internal["http://example.org/bar/0"]
            )
        )
    )

    # Need to make sure records are indexed before subsequent interactions
    SubjectApi.index.refresh()

    return result


@pytest.fixture(scope="module")
def operations_data(subjects_internal):
    """Operations in data form."""
    return [
        Delta(
            type="add",
            subjects_dst=(subjects_internal["http://example.org/foo/3"],),
            keep_trace=False,
        ),
        Delta(
            type="edit",
            subject_src=subjects_internal["http://example.org/foo/1"],
            subjects_dst=(
                subjects_internal["http://example.org/foo/1-relabelled"],
            ),
        ),
        Delta(
            type="remove",
            subject_src=subjects_internal["http://example.org/foo/0"],
        ),
        Delta(
            type="replace",
            subject_src=subjects_internal["http://example.org/foo/2"],
            subjects_dst=(subjects_internal["http://example.org/foo/3"],),
        ),
    ]


@pytest.fixture(scope="module")
def records_data_w_subjects(
    create_draft_data, create_record_data, minimal_record_input
):
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

    # draft
    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {"id": "http://example.org/foo/2"},  # will be replaced
    ]
    result += [create_draft_data(system_identity, record_input)]

    return result


@pytest.fixture(scope="module")
def delta_logger():
    """Log record deltas."""
    return SubjectDeltaLogger()


@pytest.fixture(scope="module")
def update_result(
    running_app, subjects, records_data_w_subjects, operations_data,
    delta_logger
):
    """Update results.

    This is actually the code under test. Because it does a lot, we create
    multiple tests that all test different aspects of its run.
    """
    noop_keep_trace = KeepTrace(None, None)
    executor = SubjectDeltaUpdater(
        operations_data, delta_logger, noop_keep_trace)
    result = executor.update()

    # Really just needed for tests: OS indices are refreshed on an interval
    # longer than the queries we make in tests, so we have to force a refresh.
    RDMDraft.index.refresh()
    RDMRecord.index.refresh()
    SubjectApi.index.refresh()

    return result


# Test utilities
def any_contains(dicts, dict_):
    """Return bool if any dict in `dicts` contains `dict_`."""
    return any(dict_.items() <= d.items() for d in dicts)


def get_subjects_of_record_from_db(pid, draft=False):
    """Return DB subjects of record with `pid`."""
    records_service = current_service_registry.get("records")
    record_result = (
        records_service.read_draft(system_identity, pid)
        if draft else
        records_service.read(system_identity, pid)
    )
    record_dict = record_result.to_dict()
    return record_dict["metadata"]["subjects"]


def get_records_from_de(draft=False):
    """Return DE hits."""
    records_service = current_service_registry.get("records")
    record_results = (
        records_service.search_drafts(system_identity)
        if draft else
        records_service.search(system_identity)
    )
    records_dict = record_results.to_dict()
    return records_dict["hits"]["hits"]


def get_subjects_of_record_from_de(records, pid):
    """Return subjects of record with `pid` in `records` .

    records is the output of `get_records_from_de`.
    """
    record_dict = next((r for r in records if r.get("id") == pid), {})
    return record_dict.get("metadata").get("subjects", [])


# Tests
def test_update_on_subjects(update_result, subjects_service):
    # update_result is under test

    # at DB
    # -----
    # add
    assert subjects_service.read(system_identity, "http://example.org/foo/3")

    # rename
    subject_result = subjects_service.read(
        system_identity, "http://example.org/foo/1"
    )
    subject_dict = subject_result.to_dict()
    assert "One" == subject_dict["subject"]

    # remove
    with pytest.raises(PIDDoesNotExistError):
        subjects_service.read(system_identity, "http://example.org/foo/0")

    # replace
    with pytest.raises(PIDDoesNotExistError):
        subjects_service.read(system_identity, "http://example.org/foo/2")

    # at index
    # --------
    # fields = None should give all fields
    subject_results = subjects_service.read_all(system_identity, fields=None)
    subjects_dict = subject_results.to_dict()
    hits = subjects_dict["hits"]["hits"]

    # add
    assert any_contains(hits, {"id": "http://example.org/foo/3"})
    # rename
    assert any_contains(hits, {"subject": "One"})
    # remove
    assert not any_contains(hits, {"id": "http://example.org/foo/0"})
    # replace
    assert not any_contains(hits, {"id": "http://example.org/foo/2"})


def test_update_on_records(update_result, records_data_w_subjects):
    # update_result is under test

    # at DB
    # -----
    # first record
    pid_0 = records_data_w_subjects[0].pid.pid_value
    subjects = get_subjects_of_record_from_db(pid_0)
    assert 4 == len(subjects)
    # replace
    assert not any_contains(subjects, {"id": "http://example.org/foo/2"})
    assert any_contains(subjects, {"id": "http://example.org/foo/3"})
    # rename
    assert any_contains(
        subjects,
        {"id": "http://example.org/foo/1", "subject": "One"},
    )
    # leave alone
    assert any_contains(subjects, {"id": "http://example.org/bar/0"})
    assert any_contains(subjects, {"subject": "a_keyword"})

    # second record
    pid_1 = records_data_w_subjects[1].pid.pid_value
    subjects = get_subjects_of_record_from_db(pid_1)
    # remove
    assert 0 == len(subjects)  # only had the one removed subject

    # at document engine
    # --------
    records = get_records_from_de()
    # first record
    subjects = get_subjects_of_record_from_de(records, pid_0)
    assert 4 == len(subjects)
    # replace
    assert not any_contains(subjects, {"id": "http://example.org/foo/2"})
    assert any_contains(subjects, {"id": "http://example.org/foo/3"})
    # rename
    assert any_contains(
        subjects,
        {"id": "http://example.org/foo/1", "subject": "One"},
    )
    # leave alone
    assert any_contains(subjects, {"id": "http://example.org/bar/0"})
    assert any_contains(subjects, {"subject": "a_keyword"})

    # second record
    subjects = get_subjects_of_record_from_de(records, pid_1)
    # remove
    assert 0 == len(subjects)  # only had the one removed subject


def test_update_on_drafts(update_result, records_data_w_subjects):
    # update_result is under test

    # at DB
    # -----
    pid = records_data_w_subjects[2].pid.pid_value
    subjects = get_subjects_of_record_from_db(pid, draft=True)
    assert not any_contains(subjects, {"id": "http://example.org/foo/2"})
    assert any_contains(subjects, {"id": "http://example.org/foo/3"})

    # at document engine
    # ---
    records = get_records_from_de(draft=True)
    subjects = get_subjects_of_record_from_de(records, pid)
    # Drafts don't keep trace
    assert 1 == len(subjects)
    assert any_contains(subjects, {"id": "http://example.org/foo/3"})


def test_update_logging(update_result, delta_logger, records_data_w_subjects):
    log_entries = delta_logger.read()

    # record 0 logging
    pid = records_data_w_subjects[0].pid.pid_value
    log_entry = next((e for e in log_entries if e.get("pid") == pid), None)
    assert log_entry and log_entry["time"]
    assert "" == log_entry["msg"]
    msg = (
        "http://example.org/foo/1 foo 1 -> foo One + " +
        "http://example.org/foo/2 -> [http://example.org/foo/3]"
    )
    assert msg == log_entry["deltas"]

    # record 1 logging
    pid = records_data_w_subjects[1].pid.pid_value
    log_entry = next(
        (e for e in log_entries if e.get("pid") == pid),
        None
    )
    assert log_entry["time"]
    assert "" == log_entry["msg"]
    msg = "http://example.org/foo/0 -> X"
    assert msg == log_entry["deltas"]

    # draft logging
    pid = records_data_w_subjects[2].pid.pid_value
    log_entry = next(
        (e for e in log_entries if e.get("pid") == pid),
        None
    )
    assert log_entry and log_entry["time"]
    assert "" == log_entry["msg"]
    msg = "http://example.org/foo/2 -> [http://example.org/foo/3]"
    assert msg == log_entry["deltas"]


def test_update_keep_trace(
    create_subject_data, minimal_record_input, create_record_data_fn,
):
    # Has its own set of subjects
    subjects_internal = {
        f"http://example.org/baz/{i}": Subject(
            id=f"http://example.org/baz/{i}",
            scheme="baz",
            label=f"{i}",
        )
        for i in range(3)
    }
    subjects_internal.update({
        "http://example.org/baz/2-relabelled": Subject(
            id="http://example.org/baz/2",
            scheme="baz",
            label="Baz-Two",
        ),
    })

    # Test that keep_trace template is placed in keep_trace field
    # if subject delta op is marked as keep_trace
    subject_rdm_serdes = SubjectRDMSerdes()
    [
        create_subject_data(
            system_identity,
            subject_rdm_serdes.serialize(
                subjects_internal[f"http://example.org/baz/{i}"]
            )
        )
        for i in range(3)
    ]

    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {
            "id": "http://example.org/baz/0",
        },
        {
            "id": "http://example.org/baz/1",
        }
    ]
    record_0_data = create_record_data_fn(system_identity, record_input)
    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {
            "id": "http://example.org/baz/2"
        }
    ]
    record_1_data = create_record_data_fn(system_identity, record_input)
    delta_ops = [
        Delta(
            type="remove",
            subject_src=subjects_internal["http://example.org/baz/0"],
            keep_trace=True,
        ),
        Delta(
            type="replace",
            subject_src=subjects_internal["http://example.org/baz/1"],
            subjects_dst=(subjects_internal["http://example.org/baz/2"],),
            keep_trace=False,
        ),
        Delta(
            type="edit",
            subject_src=subjects_internal["http://example.org/baz/2"],
            subjects_dst=(
                subjects_internal["http://example.org/baz/2-relabelled"],
            ),
            keep_trace=True,
        ),
    ]
    delta_logger = SubjectDeltaLogger()
    keep_trace = KeepTrace(
        field="metadata.subjects.subject",
        template="anything {subject} anything"
    )
    # make sure indices are refreshed
    RDMRecord.index.refresh()
    SubjectApi.index.refresh()

    updater = SubjectDeltaUpdater(delta_ops, delta_logger, keep_trace)
    updater.update()

    # at DB
    # -----
    # record 0
    subjects = get_subjects_of_record_from_db(record_0_data.pid.pid_value)
    assert 2 == len(subjects)
    # Contains keep_trace template due to removal
    assert any_contains(subjects, {"subject": "anything 0 anything"})
    # Doesn't contain keep_trace template due to replacement
    assert not any_contains(subjects, {"subject": "anything 1 anything"})
    assert any_contains(subjects, {"id": "http://example.org/baz/2"})

    # record 1
    subjects = get_subjects_of_record_from_db(record_1_data.pid.pid_value)
    assert 2 == len(subjects)
    # Contains keep_trace template due to rename
    assert any_contains(subjects, {"subject": "anything 2 anything"})
    assert any_contains(subjects, {"subject": "Baz-Two"})

    # at document engine
    # ---
    # This is done for completeness sake, just in case some changes are made
    # that would inadvertently skip updating the document engine.
    RDMRecord.index.refresh()
    records = get_records_from_de()

    # record 0
    subjects = get_subjects_of_record_from_de(
        records,
        record_0_data.pid.pid_value
    )
    assert 2 == len(subjects)
    # Contains keep_trace template due to removal
    assert any_contains(subjects, {"subject": "anything 0 anything"})
    # Doesn't contain keep_trace template due to replacement
    assert not any_contains(subjects, {"subject": "anything 1 anything"})
    assert any_contains(subjects, {"id": "http://example.org/baz/2"})

    # record 1
    subjects = get_subjects_of_record_from_de(
        records,
        record_1_data.pid.pid_value
    )
    assert 2 == len(subjects)
    # Contains keep_trace template due to rename
    assert any_contains(subjects, {"subject": "anything 2 anything"})
    assert any_contains(subjects, {"subject": "Baz-Two"})


def test_update_edge_case(
    create_subject_data, minimal_record_input, create_record_data_fn,
    subjects_internal,
):
    # Test any other edge case that pops up
    # - subjects of records are deduplicated after modifications

    subject_rdm_serdes = SubjectRDMSerdes()

    # Assignments (setup)
    create_subject_data(
        system_identity,
        subject_rdm_serdes.serialize(
            subjects_internal["http://example.org/zim/0"]
        ),
    )
    create_subject_data(
        system_identity,
        subject_rdm_serdes.serialize(
            subjects_internal["http://example.org/zim/0QA"]
        ),
    )
    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {"subject": "0QA"},
        {"id": "http://example.org/zim/0"},
        {"id": "http://example.org/zim/0QA"},
    ]
    record_0_data = create_record_data_fn(system_identity, record_input)
    delta_ops = [
        Delta(
            type="replace",
            subject_src=subjects_internal["http://example.org/zim/0QA"],
            subjects_dst=(
                subjects_internal["http://example.org/zim/0"],
            ),
            keep_trace=True,
        ),
    ]
    delta_logger = SubjectDeltaLogger()
    keep_trace = KeepTrace(
        field="metadata.subjects.subject",
        template="{subject}"
    )
    # make sure indices are refreshed
    RDMRecord.index.refresh()
    SubjectApi.index.refresh()

    # Actions
    updater = SubjectDeltaUpdater(delta_ops, delta_logger, keep_trace)
    updater.update()
    # make sure indices are refreshed
    RDMRecord.index.refresh()
    SubjectApi.index.refresh()

    # Assertions
    # at DB
    # -----
    # record 0
    subjects = get_subjects_of_record_from_db(record_0_data.pid.pid_value)
    assert 2 == len(subjects)
    assert any_contains(subjects, {"subject": "0QA"})
    assert any_contains(subjects, {"id": "http://example.org/zim/0"})

    # at document engine
    # ---
    # This is done for completeness sake, just in case some changes are made
    # that would inadvertently skip updating the document engine.
    RDMRecord.index.refresh()
    records = get_records_from_de()

    # record 0
    subjects = get_subjects_of_record_from_de(
        records,
        record_0_data.pid.pid_value
    )
    assert 2 == len(subjects)
    assert any_contains(subjects, {"subject": "0QA"})
    assert any_contains(subjects, {"id": "http://example.org/zim/0"})


def test_update_multi_replace(
    create_record_data_fn,
    create_subject_data,
    minimal_record_input
):
    # internal subjects
    subjects_internal = {
        f"http://example.org/zum/{i}": Subject(
            id=f"http://example.org/zum/{i}",
            scheme="zum",
            label=f"{i}",
        )
        for i in range(3)
    }
    # RDM Subject creation
    subject_rdm_serdes = SubjectRDMSerdes()
    [
        create_subject_data(
            system_identity,
            subject_rdm_serdes.serialize(
                subjects_internal[subject_key]
            ),
        ) for subject_key in subjects_internal
    ]

    # Record creation
    record_input = copy.deepcopy(minimal_record_input)
    record_input["metadata"]["subjects"] = [
        {"id": "http://example.org/zum/0"},
    ]
    record_0_data = create_record_data_fn(system_identity, record_input)
    # Delta with multi-replace
    deltas = [
        Delta(
            type="replace",
            subject_src=subjects_internal["http://example.org/zum/0"],
            subjects_dst=(
                subjects_internal["http://example.org/zum/1"],
                subjects_internal["http://example.org/zum/2"]
            ),
            keep_trace=True,
        ),
    ]
    # Logger
    logger = SubjectDeltaLogger()

    # Actions
    updater = SubjectDeltaUpdater(deltas, logger, KeepTrace(None, None))
    updater.update()

    # Assertions
    # ----------
    # Only DB is good enough
    pid_of_record_0 = record_0_data.pid.pid_value
    subjects = get_subjects_of_record_from_db(pid_of_record_0)
    assert 2 == len(subjects)
    assert any_contains(subjects, {"id": "http://example.org/zum/1"})
    assert any_contains(subjects, {"id": "http://example.org/zum/2"})

    # logging
    log_entries = logger.read()
    log_entry = next(
        (e for e in log_entries if e.get("pid") == pid_of_record_0),
        None,
    )
    msg = "http://example.org/zum/0 -> [http://example.org/zum/1 ; http://example.org/zum/2]"  # noqa
    assert msg == log_entry["deltas"]


def test_update_ignore_duplicate_subject_addition(
    create_subject_data,
    subjects_service,
):
    # Have a pre-existing subject and try to add it
    subject = Subject(
        id="https://example.org/baa/1",
        scheme="BAA",
        label="Baa 1",
    )
    subject_rdm_serdes = SubjectRDMSerdes()
    subject_data = create_subject_data(
        system_identity,
        subject_rdm_serdes.serialize(subject),
    )
    delta_ops = [Delta(
        type="add",
        subjects_dst=(subject,),
        keep_trace=False,
    )]
    delta_logger = SubjectDeltaLogger()
    noop_keep_trace = KeepTrace(None, None)

    # Actions
    updater = SubjectDeltaUpdater(delta_ops, delta_logger, noop_keep_trace)
    updater.update()
    # passing with no exception raised is a criteria

    # will raise if 2 rows found
    assert subjects_service.read(system_identity, "https://example.org/baa/1")

    # check message in log
    entries_of_log = delta_logger.read()
    pid_of_subject = subject_data.pid.pid_value
    log_entry = next(
        e for e in entries_of_log if e.get("pid") == pid_of_subject
    )
    expected = (
        "PID 'https://example.org/baa/1' already exists. Addition ignored."
    )
    assert expected == log_entry["msg"]
