#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2022 Northwestern University.
#
# galter-subjects-utils is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.


# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

pytest_args=()
for arg in $@; do
	# from the CLI args, filter out some known values and forward the rest to "pytest"
	# note: we don't use "getopts" here b/c of some limitations (e.g. long options),
	#       which means that we can't combine short options (e.g. "./run-tests -Kk pattern")
	case ${arg} in
		*)
			pytest_args+=( ${arg} )
			;;
	esac
done


# Note: check_manifest is still incredibly slow! (w/ 12.86s and w/o 1.51s)
python -m check_manifest --no-build-isolation
# Note: expansion of pytest_args looks like below to not cause an unbound
# variable error when 1) "nounset" and 2) the array is empty.
python -m pytest ${pytest_args[@]}
tests_exit_code=$?
exit "$tests_exit_code"
