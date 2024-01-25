# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test MeSH-related functionality."""

from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from galter_subjects_utils.converter import MeSHRDMConverter, \
    MeSHSubjectDeltasConverter, Subject
from galter_subjects_utils.downloader import MeSHDownloader
from galter_subjects_utils.reader import MeSHNewReader, MeSHReader, \
    MeSHReplaceReader, mapping_by, read_jsonl, topic_filter
from galter_subjects_utils.writer import write_jsonl

# Helpers


@contextmanager
def fake_request_context(url, stream):
    """A faked requests.get context result."""
    filename = url.rsplit("/", 1)[-1]
    fp = Path(__file__).parent / f"data/mesh/fake_{filename}"

    FakeRequestContext = namedtuple("FakeRequestContext", ["raw"])

    with open(fp, "rb") as f:
        yield FakeRequestContext(raw=f)


def assert_includes(dicts, dict_cores):
    """Checks that each dict in dicts has the corresponding dict_core."""
    for d, dc in zip(dicts, dict_cores):
        for key, value in dc.items():
            assert value == d[key]


# Tests


@mock.patch('galter_subjects_utils.downloader.requests.get')
def test_downloader(patched_get, tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    # patch requests.get to return files
    patched_get.side_effect = fake_request_context

    # Testing the current_year variant seemed like it would lead to a test
    # mirror, so it has been tested manually instead. This really just tests
    # that we have the right name, interfaces and final files written to disk
    # in right location.
    downloader = MeSHDownloader(
        year="2023",
        directory=downloads_dir
    )
    downloader.download()

    patched_get.assert_called()
    assert (downloads_dir / "d2023.bin").exists()
    assert (downloads_dir / "q2023.bin").exists()
    assert (downloads_dir / "meshnew2023.txt").exists()
    assert (downloads_dir / "replace2023.txt").exists()


def test_reader_descriptors_filter():
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_d2022.bin"

    reader = MeSHReader(filepath, filter=topic_filter)
    topics = [t for t in reader]

    expected_cores = [
        {
            'MH': 'Seed Bank',
            'DC': '1',
            'AQ': ['CL', 'EC'],
            'UI': 'D000068098'
        },
        {
            'MH': 'Abbreviations as Topic',
            'DC': '1',
            'UI': 'D000004'
        },
        {
            'MH': 'Abdomen',
            'DC': '1',
            'AQ': ['AB', 'AH'],
            'UI': 'D000005'
        },
        {
            'MH': 'American Indians or Alaska Natives',
            'DC': '1',
            'AQ': ['CL', 'ED', 'EH', 'GE', 'HI', 'LJ', 'PX', 'SN'],
            'UI': 'D000086562'
        }
    ]
    assert_includes(topics, expected_cores)


def test_reader_qualifiers():
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_q2023.bin"

    reader = MeSHReader(filepath)
    qualifiers = [q for q in reader]

    expected_cores = [
        {
            "QA": "AB",
            "SH": "abnormalities",
            "UI": "Q000002"
        },
        {
            "QA": "AH",
            "SH": "anatomy & histology",
            "UI": "Q000033"
        },
        {
            "QA": "CL",
            "SH": "classification",
            "UI": "Q000145"
        },
        {
            "QA": "EC",
            "SH": "economics",
            "UI": "Q000191"
        },
    ]
    assert_includes(qualifiers, expected_cores)


def test_converter():
    topics = [{
        'MH': 'Seed Bank',
        'DC': '1',
        'AQ': ['CL', 'EC'],
        'UI': 'D000068098'
    }]
    qualifiers = [
        {
            "QA": "CL",
            "SH": "classification",
            "UI": "Q000145"
        },
        {
            "QA": "EC",
            "SH": "economics",
            "UI": "Q000191"
        },
    ]
    qualifiers_mapping = mapping_by(qualifiers, by="QA")

    converter = MeSHRDMConverter(topics, qualifiers_mapping)
    objects = [o for o in converter]

    expected = [
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098',
            "scheme": "MeSH",
            "subject": "Seed Bank"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000145',
            "scheme": "MeSH",
            "subject": "Seed Bank/classification"
        },
        {
            "id": 'https://id.nlm.nih.gov/mesh/D000068098Q000191',
            "scheme": "MeSH",
            "subject": "Seed Bank/economics"
        },
    ]
    assert expected == objects


def test_write():
    filepath = Path(__file__).parent / "test_subjects_mesh.jsonl"
    entries = [
        {
            "id": 'D000015',
            "tags": ["mesh"],
            "title": {
                "en": 'Abnormalities, Multiple'
            }
        },
        {
            "id": 'D000068098',
            "tags": ["mesh"],
            "title": {
                "en": 'Seed Bank'
            }
        },
        {
            "id": 'D005368',
            "tags": ["mesh"],
            "title": {
                "en": 'Filariasis'
            }
        }
    ]

    write_jsonl(entries, filepath)

    read_entries = list(read_jsonl(filepath))
    assert entries == read_entries

    filepath.unlink(missing_ok=True)


def test_new_reader():
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_meshnew2023.txt"

    reader = MeSHNewReader(filepath)
    entries = [e for e in reader.read()]

    expected = [
        {
            "MH": "Document Analysis",
            "UI": "D000092002",
            "MN": "H1.770.644.241.850.375",
            "MS": "A form of qualitative research that uses a systematic procedure to analyze documentary evidence and answer specific research questions.",  # noqa
            "HN": "2023",
        },
        {
            "MH": "Family Structure",
            "UI": "D000092822",
            "MN": "F1.829.263.315.250",
            "MN": "I1.240.361.330",
            "MN": "I1.880.761.125",
            "MN": "I1.880.853.150.423.250",
            "MN": "N1.224.361.330",
            "MN": "N1.824.308.125",
            "MN": "N6.850.505.400.400.580",
            "MS": "Structural nature of relationships among members of a household typically in reference to a MINOR residing in the same home. More broadly any organizational framework that determines family membership, and the functions and hierarchical position of family members (https://eric.ed.gov/?qt=Family+Structure&ti=Family+Structure).",  # noqa
            "HN": "2023; for STEPFAMILY and FAMILY, RECONSTITUTED use FAMILY 1996-2022; for MATRIARCHY and PATRIARCHY use FAMILY CHARACTERISTICS 1995-2022",  # noqa
            "BX": "Family, Reconstituted",
            "BX": "Reconstituted Family",
            "BX": "Step-parent Family",
            "BX": "Stepfamily",
            "BX": "Stepparent Family",
        }
    ]
    assert expected == entries


def test_replace_reader():
    filepath = Path(__file__).parent / "data" / "mesh" / "fake_replace2023.txt"

    reader = MeSHReplaceReader(filepath)
    entries = [e for e in reader.read()]

    expected = [
        {
            "MH OLD": "Far East",
            "MH NEW": "Asia, Eastern",
            "delete": "",
            "status": "P",
        },
        {
            "MH OLD": "American Indians or Alaska Natives",
            "MH NEW": "American Indian or Alaska Native",
            "delete": "#",
            "status": "P",
        },
        {
            "MH OLD": "Asians",
            "MH NEW": "Asian People",
            "delete": "",
            "status": "N*",
        },
        {
            "MH OLD": "Whites",
            "MH NEW": "White People",
            "delete": "",
            "status": "P*",
        },
        {
            "MH OLD": "RNA, Guide",
            "MH NEW": "RNA, Guide, Kinetoplastida",
            "delete": "",
            "status": "",
        }
    ]
    assert expected == entries


# Start MeSHSubjectDeltasConverter tests
# ===

# Helpers


def subject_unqualified():
    """Subject without qualifier."""
    return Subject(id="D000068098", label="Seed Bank")


def subject_qualified():
    """Subject with qualifier."""
    return Subject(id="D044127Q000941", label="Epigenesis, Genetic/ethics")


def subject_unqualified_present_only_in_dst():
    """Subject: unqualified + present only in dst."""
    return Subject(id="D000092002", label="Document Analysis")


def subject_qualified_present_only_in_dst():
    """Subject: qualified + present only in dst.

    This is also a topic that is not identified as being new in meshnew file
    or modified in replace file. To be discovered, the d<year> file would have
    to be read.
    """
    return Subject(id="D005654Q000187", label="Fundus Oculi/drug effects")


def renamed_subjects():
    """Subject and its renamed version."""
    return (
        Subject(id="D017394", label="RNA, Guide"),
        Subject(id="D017394", label="RNA, Guide, Kinetoplastida"),
    )


def replaced_subjects_qualified_already_present():
    """Subject and its replaced version.

    This function doesn't enforce an already present replaced version, but
    rather expects it to be used this way.
    The replaced version should be passed as part of the original subjects.
    """
    return (
        Subject(
            id="D000086562Q000145",
            label="American Indians or Alaska Natives/classification"
        ),
        Subject(
            id="D044467Q000145",
            label="American Indian or Alaska Native/classification"
        )
    )


def replaced_subjects_newly_added():
    """Return a subject and its replaced version.

    This function doesn't enforce a newly added version, but
    rather expects it to be used this way. The replacement subject should not
    be passed as part of the original subjects.

    Subjects are made up because didn't find actual cases in last 3 years.
    """
    return (
        Subject(id="foo-before", label="Foo before"),
        Subject(id="foo-after", label="Foo after")
    )


# Tests


def test_converter_add():
    """Test only addition scenarios."""
    src = [
        subject_unqualified()
    ]
    dst = [
        subject_unqualified(),
        subject_unqualified_present_only_in_dst(),
        subject_qualified_present_only_in_dst()
    ]
    replacement = {}

    converter = MeSHSubjectDeltasConverter(src, dst, replacement)

    add_ops = converter.convert()

    expected = [
        # delta op that could have been generated from just looking at
        # meshnew file
        {
            "type": "add",
            "id": "https://id.nlm.nih.gov/mesh/D000092002",
            "scheme": "MeSH",
            "subject": "Document Analysis"
        },
        # delta op that could not have been generated from just looking at
        # meshnew file
        {
            "type": "add",
            "id": "https://id.nlm.nih.gov/mesh/D005654Q000187",
            "scheme": "MeSH",
            "subject": "Fundus Oculi/drug effects"
        },
    ]
    assert expected == add_ops


def test_converter_rename():
    """Test rename scenarios only."""
    orig_subject, renamed_subject = renamed_subjects()
    src = [
        orig_subject,
        subject_unqualified()
    ]
    dst = [
        subject_unqualified(),
        renamed_subject,
    ]
    replacement = {}
    converter = MeSHSubjectDeltasConverter(src, dst, replacement)

    rename_ops = converter.convert()

    expected = [
        {
            "type": "rename",
            "id": "https://id.nlm.nih.gov/mesh/D017394",
            "scheme": "MeSH",
            "new_subject": "RNA, Guide, Kinetoplastida"
        },
    ]
    assert expected == rename_ops


def test_converter_replace():
    """Test replace scenarios only (sort-of)."""
    orig_subject_1, replacement_subject_1 = (
        replaced_subjects_qualified_already_present()
    )
    orig_subject_2, replacement_subject_2 = replaced_subjects_newly_added()
    src = [
        orig_subject_1,
        subject_unqualified(),
        replacement_subject_1,
        orig_subject_2
    ]
    dst = [
        subject_unqualified(),
        replacement_subject_1,
        replacement_subject_2,
    ]
    replacements = {
        "American Indians or Alaska Natives": "American Indian or Alaska Native",  # noqa
        orig_subject_2.label: replacement_subject_2.label
    }
    converter = MeSHSubjectDeltasConverter(src, dst, replacements)

    ops = converter.convert()

    expected = [
        # contains add operation since replacement is new
        {
            "type": "add",
            "id": "https://id.nlm.nih.gov/mesh/foo-after",
            "scheme": "MeSH",
            "subject": "Foo after"
        },
        {
            "type": "replace",
            "id": "https://id.nlm.nih.gov/mesh/D000086562Q000145",
            "scheme": "MeSH",
            "new_id": "https://id.nlm.nih.gov/mesh/D044467Q000145"
        },
        {
            "type": "replace",
            "id": "https://id.nlm.nih.gov/mesh/foo-before",
            "scheme": "MeSH",
            "new_id": "https://id.nlm.nih.gov/mesh/foo-after"
        },
    ]
    assert expected == ops


def test_converter_remove():
    """Test remove scenarios only."""
    subject = subject_qualified()
    src = [subject]
    dst = []
    replacements = {}
    converter = MeSHSubjectDeltasConverter(src, dst, replacements)

    ops = converter.convert()

    expected = [
        {
            "type": "remove",
            "id": "https://id.nlm.nih.gov/mesh/" + subject.id,
            "scheme": "MeSH",
        },
    ]
    assert expected == ops


# End MeSHSubjectDeltasConverter tests
