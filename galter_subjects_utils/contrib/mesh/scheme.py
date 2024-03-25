# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH scheme."""

from galter_subjects_utils.scheme import Scheme


class MeSHScheme(Scheme):
    """MeSH scheme."""

    def __init__(self):
        """Constructor."""
        super().__init__(
            name="MeSH",
            prefix="https://id.nlm.nih.gov/mesh/"
        )
