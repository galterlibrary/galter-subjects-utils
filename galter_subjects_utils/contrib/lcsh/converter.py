# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generic conversion functionality."""

import re
from datetime import datetime

from .scheme import LCSHScheme


class LCSHRDMConverter:
    """Convert LCSH term into RDM subjects dict."""

    def __init__(self, topics):
        """Constructor.

        :param topics: LCSH Topics iterable
        :type topics: iterable[dict]
        """
        self.topics = topics
        self.lcsh = LCSHScheme()

    def __iter__(self):
        """Iterate over terms.

        DEPRECATED.
        """
        yield from self.convert()

    def convert(self):
        """Iterator over converted entries."""
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
            "scheme": self.lcsh.name
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


def find_main_node(topic):
    """Find main topic node among topic's skos graph.

    :param topic: skos topic
    :type topic: dict
    """
    id_suffix = topic["@id"]
    node_main = next(
        (
            n for n in topic["@graph"]
            if n.get("@id", "").endswith(id_suffix)
        ),
        None
    )
    if not node_main:
        raise Exception("No main node for {id_suffix}.")
    return node_main


def find_deprecation_node(topic, node_main):
    """Find deprecation node among topic's skos graph.

    :param topic: skos topic
    :type topic: dict
    :param node_main: main skos graph node
    :type node_main: dict
    """
    for node in topic["@graph"]:
        is_deprecated = node.get("cs:changeReason") == "deprecated"
        subject_of_change = node.get("cs:subjectOfChange", {}).get("@id")
        # just to be sure
        if is_deprecated and node_main.get("@id") == subject_of_change:
            return node
    return {}


def is_deprecated(topic):
    """Filter for deprecated topics.

    :param topic: skos topic
    :type topic: dict
    """
    # Find main node
    node_main = find_main_node(topic)

    # Find deprecation
    return bool(find_deprecation_node(topic, node_main))


def happened_since(topic, since=None):
    """Filter for topic having happened after since.

    :param topic: skos topic
    :type topic: dict
    :param since: date since to filter by (included)
    :type since: datetime.datetime
    """
    if not since:
        return True
    node_main = find_main_node(topic)
    node_deprecation = find_deprecation_node(topic, node_main)
    date_created_str = node_deprecation.get("cs:createdDate", {}).get("@value")
    date_created = datetime.strptime(date_created_str, "%Y-%m-%dT%H:%M:%S")
    return since <= date_created


def find_explanation(nodes_of_change_note):
    """Find explaination among skos:changeNote nodes."""
    for n in nodes_of_change_note:
        explanation = n.get("@value")
        if explanation:
            return explanation
    return ""


pattern = r"covered by .+ subject heading( {(?P<subject_new>.+)})? .+(?P<id_new>sh\s?\d+)$"  # noqa
regex_for_replacement = re.compile(pattern)


def extract_replacement_id_subject(notes):
    """Returns (id_new, subject_new) tuple from notes or ("", "") else."""
    matches = regex_for_replacement.search(notes)
    if not matches:
        return "", ""
    id_new = matches.group("id_new") or ""
    id_new = id_new.replace(" ", "")  # get rid of potential space after 'sh'
    lcsh = LCSHScheme()
    id_new = lcsh.generate_id(id_new) if id_new else id_new
    subject_new = matches.group("subject_new") or ""
    return id_new, subject_new


def to_raw_replacement(topic):
    """Fill out replacement dict.

    :param topic: skos topic
    :type topic: dict
    """
    node_main = find_main_node(topic)
    node_deprecation = find_deprecation_node(topic, node_main)
    notes = find_explanation(node_main.get("skos:changeNote"))
    id_new, subject_new = extract_replacement_id_subject(notes)
    return {
        "id": node_main.get("@id").replace("http://", "https://"),
        "time": node_deprecation.get("cs:createdDate", {}).get("@value"),
        "subject": node_main.get("skosxl:literalForm", {}).get("@value"),
        "new_id": id_new,
        "new_subject": subject_new,
        "notes": notes,
    }


def raw_to_deprecated(topics, since=None):
    """Iterator over deprecated topics and their relevant information.

    :param topics: LCSH Topics iterable
    :type topics: iterable[dict]
    :param since: filter for this date (included) and later
    :type since: datetime.datetime

    :yields: Replacement dicts of the shape:
        {
            "id": ...,
            "time": ...,
            "subject": ...,
            "new_id": ...,
            "new_subject": ...,
            "notes": ...
        }
    """
    for topic in topics:
        # filter for deprecated
        if not is_deprecated(topic):
            continue

        # filter for date
        if not (happened_since(topic, since)):
            continue

        # fill out result
        yield to_raw_replacement(topic)
