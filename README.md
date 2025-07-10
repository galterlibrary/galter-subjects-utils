# galter-subjects-utils

*Subjects tooling for InvenioRDM.*

<a href="https://pypi.org/project/galter-subjects-utils/">
  <img src="https://img.shields.io/pypi/v/galter-subjects-utils.svg">
</a>

This distribution package provides an invenio subcommand group to manage controlled vocabulary subjects.

In particular, it provides functionality to

- generate and update the initial list of subject terms for a vocabulary distribution package.
- update a running instance's subjects by analyzing the delta between the instance and the updated target list of terms.

Although it contributes MeSH and LCSH terms functionality (those may be extracted out in the future), the goal is for this package to provide a framing for any subjects operations/CLI tooling. See https://github.com/galterlibrary/invenio-subjects-mesh for an example
of how it fits in the ecosystem.

## Installation

```bash
pip install galter-subjects-utils
```

### Versions

This repository follows [semantic versioning](https://semver.org/) indexed on invenio-app-rdm compatibility according to the table below:

| galter-subjects-utils | invenio-app-rdm version |
| --------------------- | ----------------------- |
| 0.7.X                 | 13.X                    |
| 0.5.X, 0.6.x          | 12.X                    |

This just means for example that version 0.7 guarantees generation of subjects files and subject manipulation compatible with invenio-app-rdm v13. When there is a break in subjects format, this tool will bump its major version.

## Usage

In virtualenv (`(venv)` denotes that going forward):

```bash
(venv) invenio galter-subjects --help
```

## Development

Install the project in editable mode with `dev` dependencies in an isolated virtualenv:

```bash
(venv) pip install -e .[dev]
```

Run tests:

```bash
(venv) invoke test
# or shorter
(venv) inv test
```

Check manifest:

```bash
(venv) inv check-manifest
```

To check compatibility with the pre-release version of InvenioRDM (invenio-app-rdm):

```bash
# Step 1 - install the pre-release dependencies
(venv) pip install --pre -e .[dev_pre]
# Step 2 - Run the pre-release tests
(venv) inv test
# if using uv run:
uv run --extra dev_pre --prerelease=allow inv test
```
