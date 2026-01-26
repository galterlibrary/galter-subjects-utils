# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2026 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Command line tool."""

import importlib
from datetime import date
from pathlib import Path

import click
from flask.cli import with_appcontext

from .keeptrace import KeepTrace
from .reader import read_csv
from .updater import SubjectDeltaUpdater
from .writer import SubjectDeltaLogger


class ClickGroupEnhancedByEntrypointGroup(click.Group):
    """Dynamically registers commands from entrypoint_group under it."""

    def __init__(
        self, name=None, entrypoint_group=None, **kwargs
    ):
        """Constructor."""
        super().__init__(name=name, **kwargs)
        self.entrypoint_group = entrypoint_group

    def _load_sub_clis(self):
        """Load sub clis."""
        entrypoints = importlib.metadata.entry_points(
            group=self.entrypoint_group
        )
        for ep in entrypoints:
            command = ep.load()
            self.add_command(command)

    def list_commands(self, ctx):
        """List commands (e.g., when --help is passed)."""
        self._load_sub_clis()
        return super().list_commands(ctx)

    def get_command(self, ctx, name):
        """Retrieve command (e.g., when galter_subjects <subject> called)."""
        self._load_sub_clis()
        return super().get_command(ctx, name)


@click.group(
    cls=ClickGroupEnhancedByEntrypointGroup,
    entrypoint_group="galter_subjects_utils.cli",
)
def main():
    """A subjects CLI utility (mostly for InvenioRDM)."""


# --- Shared ---
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
