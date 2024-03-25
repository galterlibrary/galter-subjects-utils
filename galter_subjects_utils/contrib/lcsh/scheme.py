# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""LCSH Scheme."""

from galter_subjects_utils.scheme import Scheme


class LCSHScheme(Scheme):
    """LCSH scheme."""

    def __init__(self):
        """Constructor."""
        super().__init__(
            name="LCSH",
            prefix="https://id.loc.gov/authorities/subjects/"
        )
