#!/bin/bash
# Expanse wrapper of cluster/sitekit/collect.sh: fetch, verify and index the
# published records of a plan (default production_plan) from expanse.
#   bash cluster/expanse/collect.sh [--plan-name NAME] [--dest DIR] [--python PY]
exec bash "$(dirname "${BASH_SOURCE[0]}")/../sitekit/collect.sh" --site expanse "$@"
