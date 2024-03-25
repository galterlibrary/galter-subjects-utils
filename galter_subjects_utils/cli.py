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

from .contrib.lcsh.cli import lcsh
from .contrib.mesh.cli import mesh
from .keeptrace import KeepTrace
from .reader import read_csv
from .updater import SubjectDeltaUpdater
from .writer import SubjectDeltaLogger


@click.group()
def main():
    """A subjects CLI utility (mostly for InvenioRDM)."""


main.add_command(lcsh)
main.add_command(mesh)


defaults = {
    "year": date.today().year,
    "filter": "topic-qualifier",
    "downloads-dir": Path.cwd(),
    "output-file": Path.cwd(),
}


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
