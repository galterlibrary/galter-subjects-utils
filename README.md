# galter-subjects-utils

*Subjects tooling for InvenioRDM.*

When a new list of terms (e.g. MeSH) comes out, this tool can be used to update the list in a dedicated subject distribution package.
This tool is typically required-in by the distribution packages.

The tool follows the same typical pattern for any subject:

1- Download the new list
2- Read it with optional filters
3- Convert vocabulary entries to InvenioRDM subjects format
4- Write those to file

## Installation

```bash
pip install galter-subjects-utils
```

### Versions

This repository follows [semantic versioning](https://calver.org/) indexed on invenio-app-rdm compatibility according to table below:

| This Version | invenio-app-rdm version |
| ------------ | ----------------------- |
| 1.X          | 11.X                    |

This just means that version 1.X guarantees generation of subjects files compatible with invenio-app-rdm v11. When there is a break in subjects format, this tool will bump its major version.

## Usage

```bash
pipenv run galter-subjects-utils --help
```
