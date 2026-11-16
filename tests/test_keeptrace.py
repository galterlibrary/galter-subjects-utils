#
# Copyright (C) 2024-2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test KeepTrace."""

from galter_subjects_utils.keeptrace import KeepTrace


def any_contains(dicts, dict_):
    """Return bool if any dict in `dicts` contains `dict_`."""
    return any(dict_.items() <= d.items() for d in dicts)


def test_trace():
    # Same interface as a Record
    record = {
        "metadata": {
            "subjects": [
                {"subject": "0QA"},
                {"id": "http://example.org/zim/0"},
                {"id": "http://example.org/zim/0QA"},
            ]
        }
    }
    keep_trace = KeepTrace(
        field="metadata.subjects.subject", template="Template with {subject}",
    )

    label_of_subject = "a trace"
    keep_trace.trace(record, label_of_subject)
    assert any_contains(
        record["metadata"]["subjects"], {"subject": "Template with a trace"}
    )
