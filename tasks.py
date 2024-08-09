# Copyright (C) 2024 Northwestern University.
#

"""Main project development commands.

Notes:
- `c.run` uses the bash shell by default.
- `c.run` runs the commands in an isolated subprocess.
"""

import re

from invoke import task
from invoke.exceptions import UnexpectedExit


def docker_services_cli_up(c):
    """Start services for tests.

    :param c: invoke.Context

    Returns dict of exported environment variables.
    """
    result = c.run(
        'docker-services-cli up --db postgresql --search opensearch2 --mq rabbitmq --cache redis --env',  # noqa
        hide=True
    )
    out = result.stdout
    envs_assignments = re.findall('^export (.+)$', out, flags=re.M)
    env = dict([ea.split("=", 1) for ea in envs_assignments])
    return env


def docker_services_cli_down(c, session=False, env=None):
    """Stop services for tests unless in a testing session."""
    if not session:
        c.run('docker-services-cli down', env=env)


@task
def test(c, color=True, passthru="", session=False):
    """Run tests."""
    env = docker_services_cli_up(c)
    try:
        c.run(f"python -m pytest {passthru}", pty=color, env=env)
    except UnexpectedExit:
        pass
    finally:
        docker_services_cli_down(c, session, env=env)


@task
def check_manifest(c, passthru=""):
    """Check manifest."""
    c.run(f"python -m check_manifest --no-build-isolation {passthru}")


@task
def clean(c):
    """Clean."""
    c.run("rm -rf *.egg-info/ */*.egg-info/ dist/ build/")
