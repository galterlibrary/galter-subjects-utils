#
# Copyright (C) 2024-2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic download functionality."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Subject:
    """Minimalist subject data."""

    id: str
    label: str
    scheme: str = ""  # just for transition
