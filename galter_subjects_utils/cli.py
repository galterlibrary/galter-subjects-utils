# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Command line tool."""

from datetime import date
from pathlib import Path

import click

from .converter import MeSHRDMConverter
from .downloader import MeSHDownloader
from .reader import MeSHReader, topic_filter
from .writer import write_jsonl


@click.group()
def main():
    """A subjects CLI utility (mostly for InvenioRDM)."""


defaults = {
    "year": date.today().year,
    "filter": "topic-qualifier",
    "downloads-dir": Path.cwd(),
    "output-file": Path.cwd(),
}


def to_downloader_kwargs(parameters):
    """To MeSHDownloader kwargs."""
    filter_to_prefixes = {
        "topic": ["d"],
        "topic-qualifier": ["d", "q"],
    }

    result = {
        "year": parameters["year"],
        "prefixes": filter_to_prefixes[parameters["filter"]],
        "cache": not parameters["no_cache"],
        "directory": Path.cwd() / parameters["downloads-dir"]
    }

    return result


def to_converter_kwargs(parameters, downloader):
    """Convert."""
    result = {}
    if parameters["filter"] in ["topic", "topic-qualifier"]:
        result["topics"] = MeSHReader(
            downloader.prefix_to_filepath["d"],
            filter=topic_filter,
        )
    if parameters["filter"] in ["topic-qualifier"]:
        result["qualifiers"] = MeSHReader(downloader.prefix_to_filepath["q"])

    return result


@main.command()
@click.option("--year", "-y", default=defaults["year"])
@click.option(
    "--filter", "-f",
    type=click.Choice(["topic", "topic-qualifier"]),
    default=defaults["filter"],
)
@click.option(
    "--downloads-dir", "-d",
    type=click.Path(path_type=Path),
    default=defaults["downloads-dir"])
@click.option(
    "--ouput-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "subjects_mesh.jsonl",
)
@click.option("--no-cache", default=False)
def mesh(**parameters):
    """Generate new MeSH terms file."""
    # Download
    downloader_kwargs = to_downloader_kwargs(parameters)
    downloader = MeSHDownloader(**downloader_kwargs)
    downloader.download()

    converter_kwargs = to_converter_kwargs(parameters, downloader)
    converter = MeSHRDMConverter(**converter_kwargs)

    filepath = write_jsonl(converter)

    print(f"MeSH terms written here {filepath}")
