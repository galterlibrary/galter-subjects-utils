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
    replaced: list[Subject] = None  # replacing subject(s)

    @property
    def edited(self):
        """Edited record property (rather than more memory usage).

        Returns:
            boolean: subject was edited or not.
        """
        return (
            self.replaced and
            len(self.replaced) == 1 and
            self.replaced[0].id == self.subject.id
        )

    def append_replaced(self, subject):
        """Append Subject to list of ones that replace self.subject.

        Takes care of initial None start.

        Args:
            subject (Subject): subject to append
        """
        if self.replaced is None:
            self.replaced = []
        self.replaced.append(subject)


class DeltasGenerator:
    """Generates deltas between source subjects and destination subjects."""

    def __init__(self, src_subjects, dst_subjects, replacements=None):
        """Constructor.

        Args:
            src_subjects (iter[Subject]): Already present subjects
            dst_subjects (iter[Subject]): Target final subjects
            replacements (dict[Subject, Subject|list[Subject]], optional):
                Src-Subject to Dst-Subject(s) replacements.
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
        """Iterate over deltas.

        Yields:
            dict (delta shaped): delta to get from self.src_subjects to
                                 self.dst_subjects using self.replacements if
                                 any.
        """
        self._analyze_src()
        self._analyze_dst()
        self._analyze_replacements()
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
                analysis.append_replaced(dst_subject)

    def _analyze_replacement(self, subject_src, subject_dst):
        """Process 1-to-1 replacement.

        Args:
            subject_src (Subject): subject to replace
            subject_dst (Subject): subject to replace by
        """
        # Does this replacement entry actually replace a src subject?
        if subject_src in self._src_subject_to_analysis:
            analysis = self._src_subject_to_analysis[subject_src]
            analysis.append_replaced(subject_dst)

            # Is the replacement entry new (not even in additions)?
            if (
                subject_dst not in self._src_subject_to_analysis and
                # by now, all additions will have been computed
                subject_dst not in self._additions
            ):
                self._additions.add(subject_dst)

    def _analyze_replacements(self):
        """Determine which subjects have been replaced."""
        for to_replace, replacement_s in self.replacements.items():
            if not isinstance(replacement_s, list):
                replacements = [replacement_s]
            else:
                replacements = replacement_s

            [
                self._analyze_replacement(to_replace, replacement)
                for replacement in replacements
            ]

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
                "scheme_dst": a.replaced[0].scheme,  # may be different
                "subject_dst": a.replaced[0].label,  # may be different
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
                "id_dst": [r.id for r in a.replaced],
                "scheme_dst": [r.scheme for r in a.replaced],
                "subject_dst": [r.label for r in a.replaced],
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
