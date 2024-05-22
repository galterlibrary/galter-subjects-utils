# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""MeSH Command line tool."""

from datetime import date
from functools import wraps
from pathlib import Path

import click
from flask.cli import with_appcontext

from galter_subjects_utils.adapter import converted_to_subjects
from galter_subjects_utils.deltor import DeltasGenerator
from galter_subjects_utils.keeptrace import KeepTrace
from galter_subjects_utils.reader import get_rdm_subjects, mapping_by
from galter_subjects_utils.writer import write_csv

from .adapter import generate_replacements
from .converter import MeSHRDMConverter
from .downloader import MeSHDownloader
from .reader import MeSHReader, MeSHReplaceReader, topic_filter
from .scheme import MeSHScheme

defaults = {
    "year": date.today().year,
    "filter": "topic-qualifier",
    "downloads-dir": Path.cwd(),
    "output-file": Path.cwd(),
}


def to_mesh_downloader_kwargs(parameters):
    """To MeSHDownloader kwargs."""
    result = {
        "year": parameters["year"],
        "cache": not parameters["no_cache"],
        "directory": Path.cwd() / parameters["downloads_dir"]
    }

    return result


def to_mesh_converter_kwargs(parameters, downloader):
    """Convert."""
    result = {}

    if parameters["filter"] in ["topic", "topic-qualifier"]:
        result["topics"] = (
            MeSHReader(
                downloader.terms_filepath,
                filter=topic_filter,
            )
            .read()
        )
    if parameters["filter"] in ["topic-qualifier"]:
        result["qualifiers_mapping"] = (
            mapping_by(
                MeSHReader(downloader.qualifiers_filepath).read(),
                by="QA"
            )
        )

    return result


def mesh_download_options(f):
    """Encapsulate common MeSH download options."""

    @click.option("--year", "-y", default=defaults["year"])
    @click.option(
        "--filter", "-f",
        type=click.Choice(["topic", "topic-qualifier"]),
        default=defaults["filter"],
    )
    @click.option(
        "--downloads-dir", "-d",
        type=click.Path(path_type=Path),
        default=defaults["downloads-dir"]
    )
    @click.option(
        "--no-cache",
        default=False,
        help="Re-download even if already downloaded.",
        is_flag=True
    )
    @wraps(f)
    def _wrapped(*args, **kwargs):
        """Wrap f with common download options."""
        return f(*args, **kwargs)

    return _wrapped


@click.group()
def mesh():
    """MeSH related commands."""


@mesh.command("download")
@mesh_download_options
def mesh_download(**parameters):
    """Download MeSH files."""
    downloader_kwargs = to_mesh_downloader_kwargs(parameters)
    downloader = MeSHDownloader(**downloader_kwargs)
    downloader.download()

    print(f"Raw MeSH files written in {parameters['downloads_dir']}/")


@mesh.command("file")
@mesh_download_options
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "subjects_mesh.jsonl",
)
def mesh_file(**parameters):
    """Generate new MeSH subjects file."""
    # Download
    downloader_kwargs = to_mesh_downloader_kwargs(parameters)
    downloader = MeSHDownloader(**downloader_kwargs)
    downloader.download()

    # Convert
    converter_kwargs = to_mesh_converter_kwargs(parameters, downloader)
    converter = MeSHRDMConverter(**converter_kwargs)

    # Write
    header = ["id", "scheme", "subject"]
    filepath = write_csv(
        converter.convert(),
        parameters["output_file"],
        writer_kwargs={
            "fieldnames": header
        }
    )

    print(f"MeSH terms written here {filepath}")


@mesh.command("deltas")
@click.option(
    "--downloads-dir", "-d",
    type=click.Path(path_type=Path),
    default=defaults["downloads-dir"])
@click.option("--year", "-y", type=int, default=defaults["year"])
@click.option(
    "--filter", "-f",
    type=click.Choice(["topic", "topic-qualifier"]),
    default=defaults["filter"],
)
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "deltas.csv",
)
@with_appcontext
def mesh_deltas(**parameters):
    """Write MeSH subject delta operations to file."""
    print("Generating deltas...")
    downloads_dir = parameters["downloads_dir"].expanduser()
    year = parameters["year"]
    filter_ = parameters["filter"]
    mesh = MeSHScheme()

    # Source subjects
    subject_rdm_preexisting = get_rdm_subjects(scheme=mesh.name)
    src = converted_to_subjects(subject_rdm_preexisting, mesh.prefix)

    # Destination subjects
    subjects_fp = downloads_dir / f"d{year}.bin"
    topics = MeSHReader(subjects_fp, filter=topic_filter).read()

    if filter_ == "topic-qualifier":
        qualifiers_fp = downloads_dir / f"q{year}.bin"
        qualifiers_mapping = mapping_by(
            MeSHReader(qualifiers_fp).read(),
            by="QA"
        )
    else:
        qualifiers_mapping = {}

    converted = MeSHRDMConverter(topics, qualifiers_mapping).convert()
    dst = converted_to_subjects(converted, mesh.prefix)

    # Replacements
    replace_fp = downloads_dir / f"replace{year}.txt"
    replacements = generate_replacements(
        MeSHReplaceReader(replace_fp).read()
    )

    ops = (
        DeltasGenerator(
            src_subjects=src,
            dst_subjects=dst,
            scheme=mesh,
            replacements=replacements
        )
        .generate()
    )
    # in-place
    KeepTrace.mark(
        ops,
        # only can keep trace of *those* anyway
        yes_logic=lambda op: op["type"] in ["rename", "replace", "remove"]
    )

    deltas_fp = parameters["output_file"]
    header = [
        "id",
        "type",
        "scheme",
        "subject",
        "new_id",
        "new_subject",
        "keep_trace"
    ]
    write_csv(
        ops,
        deltas_fp,
        writer_kwargs={
            "fieldnames": header
        }
    )

    print(f"MeSH deltas written here {deltas_fp}")
