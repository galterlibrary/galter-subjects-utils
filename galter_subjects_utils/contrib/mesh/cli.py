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

from galter_subjects_utils.reader import mapping_by
from galter_subjects_utils.writer import write_jsonl

from .converter import MeSHRDMConverter
from .downloader import MeSHDownloader
from .reader import MeSHReader, topic_filter

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
    filepath = write_jsonl(converter.convert(), parameters["output_file"])

    print(f"MeSH terms written here {filepath}")
