# Copyright (C) 2024-2026 Northwestern University.
#

"""Main project development commands.

Notes:
- `c.run` uses the bash shell by default.
- `c.run` runs the commands in isolated subprocesses.
"""

from invoke import task
from invoke.exceptions import UnexpectedExit


@task
def test(c, color=True, passthru="", session=False):
    """Run tests."""
    c.run("ruff check", pty=color)
    # docker-services-cli outputs bash export commands meant to be eval'ed
    # to get environment variables . Because c (Invoke Context object) is
    # not stateful, we need to extract the **evaluated** environment
    # variables into a dict that can be passed around to subsequent
    # commands.
    result = c.run(
        'eval "$(docker-services-cli up --db postgresql --search opensearch2 --mq rabbitmq --cache redis --env)"'  # noqa
        " && env",
        hide=True,
    )
    env = dict(
        [line.split("=", 1) for line in result.stdout.split("\n") if line]
    )

    try:
        c.run(f"python -m pytest {passthru}", pty=color, env=env)
    except UnexpectedExit:
        pass
    finally:
        if not session:
            c.run('docker-services-cli down', env=env)


@task
def clean(c):
    """Clean."""
    c.run("rm -rf *.egg-info/ */*.egg-info/ dist/ build/")
