# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Convert MeSH data to InvenioRDM/ops."""

from .scheme import MeSHScheme


class MeSHRDMConverter:
    """Convert MeSH term into RDM subject dict."""

    def __init__(self, topics, qualifiers_mapping=None):
        """Constructor.

        :param topics: MeSH Topics iterable
        :type topics: iterable[dict]
        :param qualifiers: MeSH qualifiers iterable, defaults to None
        :type qualifiers: iterable[dict], optional
        """
        self.topics = topics
        self.qualifiers_mapping = qualifiers_mapping
        self.mesh = MeSHScheme()

    def __iter__(self):
        """Iterate over converted entries.

        DEPRECATED.
        """
        yield from self.convert()

    def convert(self):
        """Iterator over converted entries."""
        for topic in self.topics:
            yield {
                "id": self.mesh.generate_id(topic['UI']),
                "scheme": self.mesh.name,
                "subject": topic['MH']
            }

            if not self.qualifiers_mapping:
                continue

            for qid in topic.get("AQ", []):
                qualifier = self.qualifiers_mapping.get(qid)

                if not qualifier:
                    continue

                yield {
                    "id": self.mesh.generate_id(topic['UI'] + qualifier['UI']),
                    "scheme": self.mesh.name,
                    "subject": topic['MH'] + "/" + qualifier['SH']
                }
