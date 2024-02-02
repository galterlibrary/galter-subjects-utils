# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic conversion functionality."""


class LCSHRDMConverter:
    """Convert LCSH term into RDM subjects dict."""

    def __init__(self, topics):
        """Constructor.

        :param topics: LCSH Topics iterable
        :type topics: iterable[dict]
        """
        self.topics = topics

    def __iter__(self):
        """Iterate over terms."""
        for topic in self.topics:
            entry = self.extract_entry(topic)
            if entry:
                yield entry

    def extract_entry(self, topic):
        """Extract relevant dict from LCSH skos json-ld dict."""
        # Find id and label
        id_suffix = topic["@id"]
        info_entry = next(
            (
                e for e in topic["@graph"]
                if (
                    e.get("@id").endswith(id_suffix) and
                    e.get("@type") == "skos:Concept"
                )
            ),
            None
        )

        if not info_entry:
            return {}

        entry = {
            "id": info_entry["@id"].replace("http://", "https://"),
            "scheme": "LCSH"
        }
        pref_label = info_entry["skos:prefLabel"]
        if isinstance(pref_label, dict):
            subject = pref_label["@value"]
        elif isinstance(pref_label, list):
            subject = pref_label[-1]["@value"]
        else:
            raise Exception("invalid skos:prefLabel")
        entry["subject"] = subject

        return entry
