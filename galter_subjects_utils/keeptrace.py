# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""KeepTrace."""

from dataclasses import dataclass


@dataclass
class KeepTrace:
    """Keeps trace of subject at field in record using template."""

    field: str  # dotted path to field
    template: str
    yes = "Y"
    no = "N"
    keep_trace_key = "keep_trace"

    @classmethod
    def mark(cls, ops_data, yes_logic):
        """Mark ops_data in-place to keep trace or not depending on yes_logic.

        :param ops_data: operation data
        :type ops_data: List[dict] (list of subject op data)
        :param yes_logic: function to determine if op_data should be marked
        :type yes_logic: function(op_data) -> Bool
        """
        for op_data in ops_data:
            op_data[cls.keep_trace_key] = cls.yes if yes_logic(op_data) else cls.no  # noqa

    def should_trace(self, op_data):
        """Determine if op_data should trace."""
        return op_data.get(self.keep_trace_key, "").lower() == self.yes.lower()

    def trace(self, record, subject):
        """Save expanded `self.template` at `self.field` in record."""
        if not self.field or not self.template or not subject:
            return

        final_dict = self.find_final_dict(record)
        self.assign_template(final_dict, subject)

    def find_final_dict(self, record):
        """Find or create final dict by following `field`."""
        obj = record
        keys = self.field.split(".")

        for key in keys[:-1]:
            got = obj.get(key)
            if isinstance(got, dict):
                obj = got
            elif got is None:
                new_dict = {}
                obj[key] = new_dict
                obj = new_dict
            elif isinstance(got, list):
                new_dict = {}
                got.append(new_dict)
                obj = new_dict
            else:
                break

        assert isinstance(obj, dict), f"KeepTrace.field '{self.field}' is invalid."  # noqa
        return obj

    def assign_template(self, dict_, subject):
        """Assign expanded template."""
        final_key = self.field.split(".")[-1]
        dict_[final_key] = self.template.format(subject=subject)
