# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH subjects_mesh.jsonl writer."""

import csv
import json
from datetime import datetime
from io import StringIO
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


def write_csv(entries, filepath, writer_kwargs=None):
    """Write to CSV."""
    writer_kwargs = writer_kwargs or {}
    with open(filepath, "w") as f:
        writer = csv.DictWriter(f, **writer_kwargs)
        writer.writeheader()
        writer.writerows(entries)

    return filepath


class SubjectDeltaLogger:
    """Convenience logger for delta operations applied to records."""

    def __init__(self, filepath=None):
        """Constructor."""
        if not filepath:
            # In memory
            self.f = StringIO()
        else:
            self.f = open(filepath, "w+", newline='')

        self.header = ["pid", "time", "error", "deltas"]
        self.writer = csv.DictWriter(
            self.f, fieldnames=self.header
        )
        self.writer.writeheader()

        self.clear()

    def log(self, pid, delta=None, error=None):
        """Buffered log.

        Idea is to build up a log entry for pid with multiple deltas.
        The actual logging is only written out when flush() is called.
        An impromptu change in pid will clear out any accumulated data.
        `log(error=...)` is typically called on its own to fill the error
        portion.
        """
        if self.pid != pid:
            self.clear()

        self.pid = pid

        if delta:
            if delta["type"] == "replace":
                delta_msg = f"{delta['id']} -> {delta['new_id']}"
            elif delta["type"] == "remove":
                delta_msg = f"{delta['id']} -> X"
            elif delta["type"] == "rename":
                delta_msg = f"{delta['id']} {delta['subject']} -> {delta['new_subject']}"  # noqa
            else:
                return

            self.deltas.append(delta_msg)

        if error:
            self.error = error

    def flush(self):
        """Flush out the buffered entry."""
        if not self.pid:
            # do nothing
            return

        self.writer.writerow(
            {
                "pid": self.pid,
                "time": datetime.now(),
                "error": self.error,
                "deltas": " + ".join(self.deltas)
            }
        )

        self.clear()

    def clear(self):
        """Clear out the buffered data."""
        self.pid = None
        self.error = None
        self.deltas = []

    def close(self):
        """Close file."""
        self.f.close()

    def read(self):
        """Read file."""
        offset = self.f.tell()
        self.f.seek(0)
        result = [e for e in csv.DictReader(self.f)]
        self.f.seek(offset)
        return result
