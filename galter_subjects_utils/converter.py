# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Term converter."""


class MeSHRDMConverter:
    """Convert MeSH term into RDM subject dict."""

    def __init__(self, topics, qualifiers=None):
        """Constructor.

        :param topics: MeSH Topics iterable
        :type topics: iterable[dict]
        :param qualifiers: MeSH qualifiers iterable, defaults to None
        :type qualifiers: iterable[dict], optional
        """
        self.topics = topics
        self._qualifier_map = {
            q.get("QA"): q for q in qualifiers
        } if qualifiers else {}

    def generate_id(self, identifier):
        """Generate URI id."""
        return f"https://id.nlm.nih.gov/mesh/{identifier}"

    def __iter__(self):
        """Iterate over converted entries."""
        for topic in self.topics:
            yield {
                "id": self.generate_id(topic['UI']),
                "scheme": "MeSH",
                "subject": topic['MH']
            }

            if not self._qualifier_map:
                continue

            for qid in topic.get("AQ", []):
                qualifier = self._qualifier_map.get(qid)

                if not qualifier:
                    continue

                yield {
                    "id": self.generate_id(topic['UI'] + qualifier['UI']),
                    "scheme": "MeSH",
                    "subject": topic['MH'] + "/" + qualifier['SH']
                }


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
