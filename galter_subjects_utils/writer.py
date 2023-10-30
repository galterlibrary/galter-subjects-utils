# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH subjects_mesh.jsonl writer."""

import json
from pathlib import Path


def write_jsonl(
    entries,
    filepath=Path(__file__).parent / "vocabularies/subjects_mesh.jsonl"
):
    """Write the MeSH jsonl file.

    Return filepath to written file.
    """
    with open(filepath, "w") as f:
        for entry in entries:
            json.dump(entry, f)
            f.write("\n")

    return filepath
