# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""LCSH Command line tool."""

from functools import wraps
from pathlib import Path

import click
from flask.cli import with_appcontext

from galter_subjects_utils.adapter import converted_to_subjects
from galter_subjects_utils.deltor import DeltasGenerator
from galter_subjects_utils.keeptrace import KeepTrace
from galter_subjects_utils.reader import get_rdm_subjects, read_csv, read_jsonl
from galter_subjects_utils.writer import write_csv

from .adapter import generate_replacements
from .converter import LCSHRDMConverter, deprecated_to_replacements
from .downloader import LCSHDownloader
from .scheme import LCSHScheme

defaults = {
    "downloads-dir": Path.cwd(),
    "output-file": Path.cwd(),
}


@click.group()
def lcsh():
    """LCSH related commands."""


def lcsh_download_options(f):
    """Encapsulate common LCSH download options."""

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


def to_lcsh_downloader_kwargs(parameters):
    """To LCSHDownloader kwargs."""
    result = {
        "cache": not parameters["no_cache"],
        "directory": Path.cwd() / parameters["downloads_dir"]
    }
    return result


@lcsh.command("download")
@lcsh_download_options
def lcsh_download(**parameters):
    """Download LCSH files."""
    downloader_kwargs = to_lcsh_downloader_kwargs(parameters)
    downloader = LCSHDownloader(**downloader_kwargs)
    downloader.download()

    print(f"Raw LCSH files written in {parameters['downloads_dir']}/")


def to_lcsh_converter_kwargs(downloader):
    """Provide LCSH converter args from `downloader`."""
    return {
        "topics": read_jsonl(downloader.terms_filepath)
    }


@lcsh.command("file")
@lcsh_download_options
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "subjects_lcsh.csv",
)
def lcsh_file(**parameters):
    """Generate new LCSH subjects file."""
    # Download
    downloader_kwargs = to_lcsh_downloader_kwargs(parameters)
    downloader = LCSHDownloader(**downloader_kwargs)
    downloader.download()

    # Convert
    converter_kwargs = to_lcsh_converter_kwargs(downloader)
    converter = LCSHRDMConverter(**converter_kwargs)

    # Write
    header = ["id", "scheme", "subject"]
    filepath = write_csv(
        converter.convert(),
        parameters["output_file"],
        writer_kwargs={
            "fieldnames": header
        }
    )

    print(f"LCSH terms written here {filepath}")


@lcsh.command("deprecated")
@click.argument(
    "downloads-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
)
def lcsh_deprecated(**parameters):
    """Generate CSV file of raw deprecated LCSH topics.

    This file is then parsed by a metadata expert and filled out for future
    use in lcsh_deltas.
    """
    downloads_dir = parameters["downloads_dir"].expanduser()

    fp_of_subjects = downloads_dir / f"subjects.skosrdf.jsonld"
    topics_raw = read_jsonl(fp_of_subjects)
    replacements_raw = deprecated_to_replacements(topics_raw)

    header = ["id", "time", "subject", "new_id", "new_subject", "notes"]
    fp_of_replacements = downloads_dir / "lcsh_replacements.csv"
    write_csv(
        replacements_raw,
        fp_of_replacements,
        writer_kwargs={
            "fieldnames": header
        }
    )


@lcsh.command("deltas")
@click.option(
    "--downloads-dir", "-d",
    type=click.Path(path_type=Path),
    default=defaults["downloads-dir"]
)
@click.option(
    "--output-file", "-o",
    type=click.Path(path_type=Path),
    default=defaults["output-file"] / "deltas.csv",
)
@with_appcontext
def lcsh_deltas(**parameters):
    """Write LCSH subject delta operations to file."""
    print("Generating deltas...")
    downloads_dir = parameters["downloads_dir"].expanduser()
    lcsh = LCSHScheme()

    # Source subjects
    subjects_rdm_preexisting = get_rdm_subjects(scheme=lcsh.name)
    src = converted_to_subjects(
        subjects_rdm_preexisting,
        prefix=lcsh.prefix,
    )

    # Destination subjects
    fp_of_subjects = downloads_dir / "subjects.skosrdf.jsonld"
    topics_raw = read_jsonl(fp_of_subjects)
    converted = LCSHRDMConverter(topics_raw).convert()
    dst = converted_to_subjects(converted, prefix=lcsh.prefix)

    # Replacements
    fp_of_replacements = downloads_dir / "lcsh_replacements.csv"
    replacements_lcsh = read_csv(fp_of_replacements)
    replacements = generate_replacements(replacements_lcsh)

    ops = (
        DeltasGenerator(
            src_subjects=src,
            dst_subjects=dst,
            scheme=lcsh,
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

    fp_of_deltas = parameters["output_file"]
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
        fp_of_deltas,
        writer_kwargs={
            "fieldnames": header
        }
    )

    print(f"LCSH deltas written here {fp_of_deltas}")
