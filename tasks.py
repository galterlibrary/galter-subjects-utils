# Copyright (C) 2021-2022 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#!/usr/bin/env python

from invoke import task


@task
def test(c, color=True, passthru=""):
    """Run tests."""
    c.run(f"python -m pytest {passthru}", pty=color)


@task
def check_manifest(c):
    """Check manifest."""
    c.run("python -m check_manifest --no-build-isolation")
