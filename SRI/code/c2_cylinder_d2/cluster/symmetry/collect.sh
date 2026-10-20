#!/bin/bash
# Symmetry wrapper of cluster/sitekit/collect.sh: fetch, verify and index the
# published records of a plan (default production_plan) from symmetry.
#   bash cluster/symmetry/collect.sh [--plan-name NAME] [--dest DIR] [--python PY]
exec bash "$(dirname "${BASH_SOURCE[0]}")/../sitekit/collect.sh" --site symmetry "$@"
