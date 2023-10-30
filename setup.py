# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2023 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Subject terms tooling for InvenioRDM"""

from setuptools import find_packages, setup

# readme = open('README.md').read()
# history = open('CHANGES.md').read()


packages = find_packages()

setup(
    description=__doc__,
    # long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    keywords='invenio inveniordm subjects MeSH',
    packages=packages,
)
