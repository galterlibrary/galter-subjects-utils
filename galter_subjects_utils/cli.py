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
from flask.cli import with_appcontext

from .contrib.mesh.cli import mesh
from .converter import LCSHRDMConverter
from .downloader import LCSHDownloader
from .keeptrace import KeepTrace
from .reader import read_csv, read_jsonl
from .updater import SubjectDeltaUpdater
from .writer import SubjectDeltaLogger, write_jsonl


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
    """LCSH related commands."""
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


keep_trace_field_help = "Dotted field path to where trace should be kept."
keep_trace_tmpl_help = "Template with expandable '{subject}' to be saved."


@main.command("update")
@click.argument(
    "deltas-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "updated_records.csv",
)
@click.option("--keep-trace-field", "-f", help=keep_trace_field_help)
@click.option("--keep-trace-template", "-t", help=keep_trace_tmpl_help)
@with_appcontext
def update_subjects(**parameters):
    """Update subjects in running instance according to deltas file."""
    print(f"Updating subjects...")
    deltas = [d for d in read_csv(parameters["deltas_file"])]
    log_filepath = parameters["output_file"]
    logger = SubjectDeltaLogger(filepath=log_filepath)
    keep_trace = KeepTrace(
        field=parameters.get("keep_trace_field") or None,
        template=parameters.get("keep_trace_template") or None
    )
    updater = SubjectDeltaUpdater(deltas, logger, keep_trace)
    updater.update()
    print(f"Log of updated records written here {log_filepath}")
