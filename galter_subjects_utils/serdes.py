#
# Copyright (C) 2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Serializers / Deserializers."""

import warnings

from .types_internal import Delta, Subject


class SubjectRDMSerdes:
    """Serializer/Deserializer for RDM subject."""

    def deserialize(self, subject_rdm_serialized):
        """Deserialize."""
        return Subject(
            id=subject_rdm_serialized.get("id", ""),
            scheme=subject_rdm_serialized.get("scheme", ""),
            label=subject_rdm_serialized.get("subject", ""),
        )

    def serialize(self, subject):
        """Serialize."""
        return {
            "id": subject.id,
            "scheme": subject.scheme,
            "subject": subject.label,
        }


class SubjectSrcSerdes:
    """Serializer/Deserializer for source subject."""

    def deserialize(self, subject_src_serialized):
        """Deserialize."""
        return Subject(
            id=subject_src_serialized.get("id_src", ""),
            scheme=subject_src_serialized.get("scheme_src", ""),
            label=subject_src_serialized.get("subject_src", ""),
        )

    def serialize(self, subject):
        """Serialize.

        Args:
            subject (Subject): Subject object to serialize

        Returns:
            dict - subject src shape: serialization
        """
        return {
            "id_src": subject.id,
            "scheme_src": subject.scheme,
            "subject_src": subject.label,
        }


class SubjectsDstSerdes:
    """Serializer/Deserializer for destination subjects."""

    def deserialize(self, subjects_dst_serialized):
        """Deserialize."""
        type_ = subjects_dst_serialized["type"]
        if type_ == "edit":
            # Allow storage saving by not writing down id_dst and relying
            # on id_src in edit case
            id_dst_lines = [subjects_dst_serialized.get("id_src", "")]
        else:
            id_dst_lines = (
                subjects_dst_serialized.get("id_dst", "").splitlines()
            )

        return [
            Subject(
                id=id_dst,
                scheme=scheme_dst,
                label=label_dst,
            )
            for id_dst, scheme_dst, label_dst in
            zip(
                id_dst_lines,
                subjects_dst_serialized.get("scheme_dst", "").splitlines(),
                subjects_dst_serialized.get("subject_dst", "").splitlines(),
            )
        ]

    def serialize(self, subjects_dst):
        """Serialize."""
        return {
            "id_dst": "\n".join(s.id for s in subjects_dst),
            "scheme_dst": "\n".join(s.scheme for s in subjects_dst),
            "subject_dst": "\n".join(s.label for s in subjects_dst),
        }


class DeltaSerdes:
    """Serializer/Deserializer for Deltas coming from deltas file."""

    def __init__(self):
        """Constructor."""
        self._serdes_for_subject_src = SubjectSrcSerdes()
        self._serdes_for_subjects_dst = SubjectsDstSerdes()

    def deserialize(self, delta_serialized):
        """Deserialize serialized delta.

        Args:
            delta_serialized (dict - serialized shape): dict from deltas file

        Returns:
            Delta: Delta object for corresponding delta
        """
        type_ = delta_serialized["type"]
        keep_trace = delta_serialized.get("keep_trace", "N").strip() == "Y"

        if type_ == "add":
            return Delta(
                type="add",
                subjects_dst=tuple(
                    self._serdes_for_subjects_dst.deserialize(delta_serialized)
                ),
                keep_trace=keep_trace,
            )
        elif type_ == "edit":
            return Delta(
                type="edit",
                subject_src=self._serdes_for_subject_src.deserialize(
                    delta_serialized
                ),
                subjects_dst=tuple(
                    self._serdes_for_subjects_dst.deserialize(delta_serialized)
                ),
                keep_trace=keep_trace,
            )
        elif type_ == "replace":
            return Delta(
                type="replace",
                subject_src=self._serdes_for_subject_src.deserialize(
                    delta_serialized
                ),
                subjects_dst=tuple(
                    self._serdes_for_subjects_dst.deserialize(delta_serialized)
                ),
                keep_trace=keep_trace,
            )
        elif type_ == "remove":
            return Delta(
                type="remove",
                subject_src=self._serdes_for_subject_src.deserialize(
                    delta_serialized
                ),
                keep_trace=keep_trace,
            )
        else:
            warnings.warn(f"Unknown delta type {type_}")
            return None

    def serialize(self, delta):
        """Serialize delta.

        Args:
            delta (Delta): dict from deltas file

        Returns:
            dict - serialized shape: serialization for deltas file
        """
        type_ = delta.type
        keep_trace = "Y" if delta.keep_trace else "N"
        serialization = {"type": type_, "keep_trace": keep_trace}

        if type_ == "add":
            serialization.update(
                self._serdes_for_subjects_dst.serialize(delta.subjects_dst)
            )
        elif type_ == "edit":
            serialization.update(
                self._serdes_for_subject_src.serialize(delta.subject_src)
            )
            # arguably silly but sparser csv is often easier to read
            subjects_dst_serialized = (
                self._serdes_for_subjects_dst.serialize(delta.subjects_dst)
            )
            del subjects_dst_serialized["id_dst"]
            serialization.update(subjects_dst_serialized)
        elif type_ == "replace":
            serialization.update(
                self._serdes_for_subject_src.serialize(delta.subject_src)
            )
            serialization.update(
                self._serdes_for_subjects_dst.serialize(delta.subjects_dst)
            )
        elif type_ == "remove":
            serialization.update(
                self._serdes_for_subject_src.serialize(delta.subject_src)
            )
        else:
            warnings.warn(f"Unknown delta type {type_}")

        return serialization
