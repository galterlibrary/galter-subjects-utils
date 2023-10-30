# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH term converter."""


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
