# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Subject's Scheme."""


class Scheme:
    """Parent class to specific subject kinds.

    Meant as a way to get the template method generate_id, and scheme + prefix
    interface.
    """

    def __init__(self, name=None, prefix=None):
        """Constructor."""
        self.name = name
        self.prefix = prefix

    def generate_id(self, identifier):
        """Generate full URL id as expected by InvenioRDM."""
        return f"{self.prefix}{identifier}"
