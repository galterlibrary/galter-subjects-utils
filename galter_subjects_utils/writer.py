#
# Copyright (C) 2021-2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Writing utilities."""

import csv
from datetime import datetime
from io import StringIO

import orjson as json


def write_jsonl(entries, filepath):
    """Write the jsonl file.

    Return filepath to written file.
    """
    with open(filepath, "wb") as f:
        for entry in entries:
            f.write(json.dumps(entry, f))
            f.write(b"\n")

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

    def clear(self):
        """Clear out the buffered data."""
        self.pid = None
        self.msg = None
        self.deltas = []

    def __init__(self, filepath=None):
        """Constructor."""
        if not filepath:
            # In memory
            self.f = StringIO()
        else:
            self.f = open(filepath, "w+", newline='')  # noqa

        self.header = ["pid", "time", "msg", "deltas"]
        self.writer = csv.DictWriter(
            self.f, fieldnames=self.header
        )
        self.writer.writeheader()

        self.clear()

    def log(self, pid, delta=None, msg=None):
        """Buffered log.

        Idea is to build up a log entry for pid with multiple deltas.
        The actual logging is only written out when flush() is called.
        An impromptu change in pid will clear out any accumulated data.
        `log(error=...)` is typically called on its own to fill the error
        portion.

        Args:
            pid (str) : persistent identifier of record being logged
            delta (Delta, optional) : delta operation
            msg (str, optional) : warning/problem with delta operation if any
        """
        if self.pid != pid:
            self.clear()

        self.pid = pid

        if delta:
            id_of_src = delta.subject_src.id
            if delta.type == "replace":
                replacements_joined = " ; ".join(s.id for s in delta.subjects_dst)  # noqa
                delta_msg = f"{id_of_src} -> [{replacements_joined}]"
            elif delta.type == "remove":
                delta_msg = f"{id_of_src} -> X"
            elif delta.type == "edit":
                from_msg = f"{id_of_src} {delta.subject_src.scheme} {delta.subject_src.label}"  # noqa
                to_msg = f"{delta.subjects_dst[0].scheme} {delta.subjects_dst[0].label}"  # noqa
                delta_msg = f"{from_msg} -> {to_msg}"
            else:
                return

            self.deltas.append(delta_msg)

        if msg:
            self.msg = msg

    def flush(self):
        """Flush out the buffered entry."""
        if not self.pid:
            # do nothing
            return

        self.writer.writerow(
            {
                "pid": self.pid,
                "time": datetime.now(),
                "msg": self.msg,
                "deltas": " + ".join(self.deltas),
            }
        )

        self.clear()

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
