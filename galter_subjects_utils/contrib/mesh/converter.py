# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Convert MeSH data to InvenioRDM/ops."""

from dataclasses import dataclass


def generate_id(identifier):
    """Generate URI id."""
    return f"https://id.nlm.nih.gov/mesh/{identifier}"


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

    def __iter__(self):
        """Iterate over converted entries.

        DEPRECATED.
        """
        yield from self.convert()

    def convert(self):
        """Iterator over converted entries."""
        for topic in self.topics:
            yield {
                "id": generate_id(topic['UI']),
                "scheme": "MeSH",
                "subject": topic['MH']
            }

            if not self.qualifiers_mapping:
                continue

            for qid in topic.get("AQ", []):
                qualifier = self.qualifiers_mapping.get(qid)

                if not qualifier:
                    continue

                yield {
                    "id": generate_id(topic['UI'] + qualifier['UI']),
                    "scheme": "MeSH",
                    "subject": topic['MH'] + "/" + qualifier['SH']
                }


@dataclass
class Subject:
    """Minimalist subject data."""

    id: str
    label: str


@dataclass
class Analysis:
    """Holds results of analyzing a src subject."""

    id: str
    seen: bool = False  # present in dst subjects
    relabelled: str = ""  # new label
    replaced: str = ""  # id of replacing subject


class MeSHSubjectDeltasConverter:
    """Converter between subjects in DB + new subject file to operations."""

    def __init__(self, src_subjects, dst_subjects, replacements):
        """Constructor.

        :param src_subjects: MeSH subjects found in the instance
        :type src_subjects: Iterable[Subject]
        :param dst_subjects: new subjects reader
        :type dst_subjects: Iterable[Subject]
        :param replacements: mapping of src labels to dst labels
        :type replacements: dict[str, str]
        """
        self.src_subjects = src_subjects
        self.dst_subjects = dst_subjects
        self.replacements = replacements

        # Will be filled out by _analyze_src(), _analyze_dst() and
        # _analyze_replace()
        self._id_to_analysis = {}
        self._label_to_analysis = {}
        self._additions = []

        self.scheme = "MeSH"

    def convert(self):
        """Generate operations."""
        self._analyze_src()
        self._analyze_dst()
        self._analyze_replace()
        return self._generate_ops()

    def _analyze_src(self):
        """Build internal analysis.

        The self.src_subjects iterable is completely iterated and kept in
        memory (in constituent parts). This allows us quick access and frees
        us from having to load all the self.dst_subjects as well.
        """
        for subject in self.src_subjects:
            analysis = Analysis(id=subject.id)
            self._id_to_analysis[subject.id] = analysis
            self._label_to_analysis[subject.label] = analysis

    def _analyze_dst(self):
        """Analyze through all dst subjects."""
        for dst_subject in self.dst_subjects:
            # A dst subject can be
            # added/new ?
            if dst_subject.id not in self._id_to_analysis:
                self._additions.append(dst_subject)
            # relabelled ?
            elif dst_subject.label not in self._label_to_analysis:
                analysis = self._id_to_analysis[dst_subject.id]
                analysis.seen = True
                analysis.relabelled = dst_subject.label
            # identical ?
            else:
                analysis = self._id_to_analysis[dst_subject.id]
                analysis.seen = True

    def _analyze_replace(self):
        """Determine which subjects have been replaced."""

        def find_replacement_label(label):
            """Return replacement label or None."""
            new_label = self.replacements.get(label)
            if new_label:
                return new_label

            # maybe label is qualified, so check if root is replaced
            root_label, slash, qualifier = label.rpartition("/")
            new_root_label = self.replacements.get(root_label)
            if not new_root_label:
                return None
            new_label = new_root_label + slash + qualifier
            return new_label

        def find_replacement_id(label):
            """Return replacement id or None if not replaced."""
            replacement_label = find_replacement_label(label)
            if not replacement_label:
                return None

            # is replacement_label for existing and kept subject?
            replacement_analysis = self._label_to_analysis.get(replacement_label)  # noqa
            if replacement_analysis and replacement_analysis.seen:
                return replacement_analysis.id

            # is replacement_label for newly added subject?
            replacement_subject = next(
                (s for s in self._additions if s.label == replacement_label),
                None
            )
            if replacement_subject:
                return replacement_subject.id

            # is replacement_label for relabelled existing and kept subject?
            replacement_analysis = next(
                (
                    a for a in self._label_to_analysis.values()
                    if a.relabelled == replacement_label
                ),
                None
            )
            if replacement_analysis:
                return replacement_analysis.id

            return None

        for label, analysis in self._label_to_analysis.items():
            if analysis.seen:
                continue

            replacement_id = find_replacement_id(label)
            if replacement_id:
                analysis.replaced = replacement_id

    def _generate_ops(self):
        """Generate delta operations."""
        result = []

        # Additions
        result.extend(
            {
                "type": "add",
                "scheme": self.scheme,
                "id": generate_id(a.id),
                "subject": a.label
            }
            for a in self._additions
        )

        # Renames
        result.extend(
            {
                "type": "rename",
                "scheme": self.scheme,
                "id": generate_id(analysis.id),
                "subject": label,
                "new_subject": analysis.relabelled
            }
            for label, analysis in self._label_to_analysis.items()
            if analysis.relabelled
        )

        # Replaces
        result.extend(
            {
                "type": "replace",
                "scheme": self.scheme,
                "id": generate_id(analysis.id),
                "subject": label,
                "new_id": generate_id(analysis.replaced)
            }
            for label, analysis in self._label_to_analysis.items()
            if analysis.replaced
        )

        # Removes
        result.extend(
            {
                "type": "remove",
                "scheme": self.scheme,
                "id": generate_id(analysis.id),
                "subject": label
            }
            for label, analysis in self._label_to_analysis.items()
            if not analysis.seen and not analysis.replaced
        )

        return result
