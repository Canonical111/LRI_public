#!/bin/bash
# Symmetry wrapper of cluster/sitekit/make_tarball.sh: build ONE package tarball
# (+ sha256) and, with --upload symmetry, put it on the site and unpack a code copy.
#   bash cluster/symmetry/make_tarball.sh --upload symmetry
exec bash "$(dirname "${BASH_SOURCE[0]}")/../sitekit/make_tarball.sh" "$@"
