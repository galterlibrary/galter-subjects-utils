# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Command line tool."""

from datetime import date
from pathlib import Path

import click

from .contrib.mesh.cli import mesh
from .converter import LCSHRDMConverter
from .downloader import LCSHDownloader
from .reader import read_jsonl
from .writer import write_jsonl


@click.group()
def main():
    """A subjects CLI utility (mostly for InvenioRDM)."""


main.add_command(mesh)


defaults = {
    "year": date.today().year,
    "filter": "topic-qualifier",
    "downloads-dir": Path.cwd(),
    "output-file": Path.cwd(),
}


def to_lcsh_downloader_kwargs(parameters):
    """To LCSHDownloader kwargs."""
    result = {
        "cache": not parameters["no_cache"],
        "directory": Path.cwd() / parameters["downloads_dir"]
    }
    return result


def to_lcsh_converter_kwargs(downloader):
    """Provide LCSH converter args from `downloader`."""
    result = {
        "topics": read_jsonl(downloader.extracted_filepath)
    }
    return result


@main.command()
@click.option(
    "--downloads-dir", "-d",
    type=click.Path(path_type=Path),
    default=defaults["downloads-dir"])
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "subjects_lcsh.jsonl",
)
@click.option("--no-cache", default=False)
def lcsh(**parameters):
    """Generate new MeSH terms file."""
    # Download
    downloader_kwargs = to_lcsh_downloader_kwargs(parameters)
    downloader = LCSHDownloader(**downloader_kwargs)
    downloader.download()

    # Convert
    converter_kwargs = to_lcsh_converter_kwargs(downloader)
    converter = LCSHRDMConverter(**converter_kwargs)

    # Write
    filepath = write_jsonl(converter, parameters["output_file"])

    print(f"LCSH terms written here {filepath}")
