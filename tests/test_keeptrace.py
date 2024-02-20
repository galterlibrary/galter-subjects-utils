# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test KeepTrace."""

from galter_subjects_utils.keeptrace import KeepTrace


def test_mark():
    delta_ops = [
        {
            "type": "remove",
            "id": "http://example.org/baz/0",
            "scheme": "baz",
            "subject": "0",
        },
        {
            "type": "replace",
            "id": "http://example.org/baz/1",
            "scheme": "baz",
            "subject": "1",
            "new_id": "http://example.org/baz/2",
        },
        {
            "type": "rename",
            "id": "http://example.org/baz/2",
            "scheme": "baz",
            "subject": "2",
            "new_subject": "Baz-Two",
        }
    ]

    KeepTrace.mark(
        delta_ops,
        yes_logic=lambda o: o["type"] in ["remove", "rename"]
    )

    assert "Y" == delta_ops[0][KeepTrace.keep_trace_key]
    assert "N" == delta_ops[1][KeepTrace.keep_trace_key]
    assert "Y" == delta_ops[2][KeepTrace.keep_trace_key]


def test_should_trace():
    op_no_key = {
        "type": "rename",
        "id": "http://example.org/baz/2",
        "scheme": "baz",
        "subject": "2",
        "new_subject": "Baz-Two",
    }
    keep_trace = KeepTrace(field="any", template="any")

    assert keep_trace.should_trace(op_no_key) is False

    op_random_value = {**op_no_key, KeepTrace.keep_trace_key: "random"}
    assert keep_trace.should_trace(op_random_value) is False

    op_yes = {**op_no_key, KeepTrace.keep_trace_key: "Y"}
    assert keep_trace.should_trace(op_yes)

    op_lower = {**op_no_key, KeepTrace.keep_trace_key: "y"}
    assert keep_trace.should_trace(op_lower)

    op_no = {**op_no_key, KeepTrace.keep_trace_key: "n"}
    assert keep_trace.should_trace(op_no) is False
