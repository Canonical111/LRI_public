#!/bin/bash
# Expanse wrapper of cluster/sitekit/make_tarball.sh: build ONE package tarball
# (+ sha256) and, with --upload expanse, put it on the site and unpack a code copy.
#   bash cluster/expanse/make_tarball.sh --upload expanse
exec bash "$(dirname "${BASH_SOURCE[0]}")/../sitekit/make_tarball.sh" "$@"
