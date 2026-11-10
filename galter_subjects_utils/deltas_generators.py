#
# Copyright (C) 2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Generate delta operations."""

from dataclasses import dataclass
from itertools import chain

from .types_internal import Subject


@dataclass
class Analysis:
    """Holds results of analyzing a src subject.

    Can't be a namedtuple because it needs to be mutable.
    """

    subject: Subject
    seen: bool = False  # present in dst subjects
    edited: bool = False  # id kept but something else changed
    replaced: Subject = None  # replacing subject


class DeltasGenerator:
    """Generates deltas between source subjects and destination subjects."""

    def __init__(self, src_subjects, dst_subjects, replacements=None):
        """Constructor.

        Args:
            src_subjects (iter[Subject]): Already present subjects
            dst_subjects (iter[Subject]): Target final subjects
            replacements (dict[Subject, Subject], optional):
                                        Src-Subject to Dst-Subject
                                        replacements.
                                        Defaults to None ({}).
        """
        self.src_subjects = src_subjects
        self.dst_subjects = dst_subjects
        self.replacements = replacements or {}

        # The below will be filled out by _analyze_src(), _analyze_dst() and
        # _analyze_replace()
        self._additions = set()
        self._src_subject_to_analysis = {}
        self._src_subject_id_to_analysis = {}

    def iter_deltas(self):
        """Generate operations."""
        self._analyze_src()
        self._analyze_dst()
        self._analyze_replace()
        yield from self._generate_ops()

    def _analyze_src(self):
        """Build internal analysis.

        The self.src_subjects iterable is completely iterated and kept in
        memory (in constituent parts). This allows us quick access and frees
        us from having to load all the self.dst_subjects as well.
        """
        for subject in self.src_subjects:
            analysis = Analysis(subject=subject)
            self._src_subject_to_analysis[subject] = analysis
            self._src_subject_id_to_analysis[subject.id] = analysis

    def _analyze_dst(self):
        """Analyze through all dst subjects."""
        for dst_subject in self.dst_subjects:
            # A dst subject can be ...

            # ... identical (most likely)
            if dst_subject in self._src_subject_to_analysis:
                analysis = self._src_subject_to_analysis[dst_subject]
                analysis.seen = True
            # ... added/new ?
            elif dst_subject.id not in self._src_subject_id_to_analysis:
                self._additions.add(dst_subject)
            # ... modified
            else:
                # The src subject has either scheme or label or both changed
                # in the destination. A scheme change is strange, but
                # maybe there was a typo and it is nothing more for us
                # to allow it.
                analysis = self._src_subject_id_to_analysis[dst_subject.id]
                analysis.seen = True
                analysis.edited = True
                analysis.replaced = dst_subject

    def _analyze_replace(self):
        """Determine which subjects have been replaced."""
        for src, dst in self.replacements.items():
            # Does this replacement entry actually replace a src subject?
            if src in self._src_subject_to_analysis:
                analysis = self._src_subject_to_analysis[src]
                analysis.replaced = dst

                # Is the replacement entry new (not even in additions)?
                if (
                    dst not in self._src_subject_to_analysis and
                    dst not in self._additions
                ):
                    self._additions.add(dst)

    def _generate_ops(self):
        """Generate delta operations."""
        # Additions
        deltas_additions =  (
            {
                "type": "add",
                "id_dst": s.id,
                "scheme_dst": s.scheme,
                "subject_dst": s.label,
            }
            for s in self._additions
        )

        # Edits
        deltas_edits = (
            {
                "type": "edit",
                "id_src": a.subject.id,
                "scheme_src": a.subject.scheme,
                "subject_src": a.subject.label,
                # "id_dst": "",  # same as id_src so omit
                "scheme_dst": a.replaced.scheme,  # may be different
                "subject_dst": a.replaced.label,  # may be different
            }
            for a in self._src_subject_to_analysis.values()
            if a.edited
        )

        # Replaces
        deltas_replacements = (
            {
                "type": "replace",
                "id_src": a.subject.id,
                "scheme_src": a.subject.scheme,
                "subject_src": a.subject.label,
                "id_dst": a.replaced.id,
                "scheme_dst": a.replaced.scheme,
                "subject_dst": a.replaced.label,
            }
            for a in self._src_subject_to_analysis.values()
            if a.replaced and not a.edited
        )

        # Removes
        deltas_removals = (
            {
                "type": "remove",
                "id_src": a.subject.id,
                "scheme_src": a.subject.scheme,
                "subject_src": a.subject.label,
            }
            for a in self._src_subject_to_analysis.values()
            if not a.seen and not a.replaced
        )

        return chain(
            deltas_additions,
            deltas_edits,
            deltas_replacements,
            deltas_removals,
        )
