# galter-subjects-utils

*Subjects tooling for InvenioRDM.*

When a new list of terms (e.g. MeSH) comes out, this tool can be used to update the list in a dedicated subject distribution package.
This tool is typically required by the dedicated subject distribution packages under the `[dev]` extra.

The tool follows the same typical pattern for any subject:

1. Download the new list
2. Read it with optional filters
3. Convert vocabulary entries to InvenioRDM subjects format
4. Write those to file

## Installation

```bash
pip install galter-subjects-utils
```

### Versions

This repository follows [semantic versioning](https://semver.org/) indexed on invenio-app-rdm compatibility according to the table below:

| This Version | invenio-app-rdm version |
| ------------ | ----------------------- |
| 0.X          | 11.X                    |
| 1.X          | 11.X                    |

This just means for example that version 1.X guarantees generation of subjects files compatible with invenio-app-rdm v11. When there is a break in subjects format, this tool will bump its major version.

## Usage

```bash
galter-subjects-utils --help
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
