# galter-subjects-utils

*Subjects tooling for InvenioRDM.*

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
| 0.3.X                 | 11.X                    |
| 0.4.X                 | 11.X                    |
| 0.5.X                 | 12.X                    |

This just means for example that version 0.3 guarantees generation of subjects files and subject manipulation compatible with invenio-app-rdm v11. When there is a break in subjects format, this tool will bump its major version.

## Usage

```bash
pipenv run invenio galter-subjects --help
```

## Development

Install the project in editable mode with `dev` dependencies in an isolated virtualenv (`(venv)` denotes that going forward):

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
