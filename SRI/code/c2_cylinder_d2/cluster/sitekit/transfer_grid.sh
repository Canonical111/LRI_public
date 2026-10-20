#!/bin/bash
# Copy ONE published coefficient grid from one site to another, streaming through
# this machine (scp -3, nothing stored locally), then verify and publish it
# atomically at the destination. Grids depend only on N, oversampling, radius
# and the scientific sources (the _src<tag> suffix), not on the site, so a grid
# built where node-local scratch is fast can serve row jobs on the other site.
#
#   cluster/sitekit/transfer_grid.sh --from expanse --to symmetry --grid N1024_o4_r4p5_src<tag>
#
# Hosts and roots come from cluster/<site>/profile.json (--from-root/--to-root
# override). The destination directory appears only after every file was verified
# there (cluster/sitekit/manifests.py run with the site's pinned Python); an
# existing complete destination grid is left alone, an incomplete or corrupt one
# stops the transfer.
set -eo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
FROM=""; TO=""; GRID=""; FROM_ROOT=""; TO_ROOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) FROM=$2; shift 2 ;;
        --to) TO=$2; shift 2 ;;
        --grid) GRID=$2; shift 2 ;;
        --from-root) FROM_ROOT=$2; shift 2 ;;
        --to-root) TO_ROOT=$2; shift 2 ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "unknown option $1" >&2; exit 64 ;;
    esac
done
[[ -n "$FROM" && -n "$TO" && "$GRID" =~ ^N[0-9]+_o[0-9]+_r[0-9p]+_src[0-9a-f]{12}$ ]] \
    || { echo "usage: $0 --from SITE --to SITE --grid N<n>_o<o>_r<r>_src<tag>" >&2; exit 64; }
profile() {   # profile SITE -> "host root python" with root and python expanded on that host
    local host root env
    read -r host root env < <(python3 -c '
import json, sys
p = json.load(open(sys.argv[1]))
fmt = lambda s: s.replace("{user}", "$USER").replace("{home}", "$HOME")
print(p["ssh_host"], fmt(p["paths"]["persistent_root"]), fmt(p["paths"]["env"]))' "$ROOT/cluster/$1/profile.json")
    echo "$host $(ssh -T -o BatchMode=yes "$host" "echo $root $env/bin/python")"
}
# remote_status HOST PYTHON DIR [--size-only]: manifests.py grid-status on HOST with the
# site's pinned Python; prints the status, exit 0 complete / 3 absent / 74 corrupt.
remote_status() {
    ssh -T -o BatchMode=yes "$1" "$2 - grid-status $3 ${4:-}" < "$ROOT/cluster/sitekit/manifests.py"
}
read -r FROM_HOST FROM_DEFAULT FROM_PY < <(profile "$FROM")
read -r TO_HOST TO_DEFAULT TO_PY < <(profile "$TO")
FROM_DIR=${FROM_ROOT:-$FROM_DEFAULT}/grids/$GRID
TO_GRIDS=${TO_ROOT:-$TO_DEFAULT}/grids
# Destination first: complete means every listed file verifies (array included, so
# this reads the whole grid on the destination's login node: minutes at N=1024).
set +e
remote_status "$TO_HOST" "$TO_PY" "$TO_GRIDS/$GRID" > /dev/null; rc=$?
set -e
case $rc in
    0) echo "already published and verified on $TO: $TO_GRIDS/$GRID"; exit 0 ;;
    3) ;;
    *) echo "a grid at $TO:$TO_GRIDS/$GRID exists but is incomplete or corrupt (see above); inspect it" >&2; exit 74 ;;
esac
# Source: manifest, receipt, small files and the array size (its hash is checked
# against the same manifest at the destination after copying).
set +e
remote_status "$FROM_HOST" "$FROM_PY" "$FROM_DIR" --size-only > /dev/null; rc=$?
set -e
(( rc == 0 )) || { echo "no complete published grid $FROM_DIR on $FROM" >&2; exit 74; }
# Snapshot the manifest at the destination, validate its names there, then copy
# exactly those files (never names read from an unvalidated manifest).
PART="$TO_GRIDS/.$GRID.partial.transfer$$"
ssh -T -o BatchMode=yes "$TO_HOST" "mkdir -p $PART"
scp -3 -q -o BatchMode=yes "$FROM_HOST:$FROM_DIR/SHA256SUMS" "$TO_HOST:$PART/SHA256SUMS"
NAMES=$(ssh -T -o BatchMode=yes "$TO_HOST" "$TO_PY - names $PART" < "$ROOT/cluster/sitekit/manifests.py") \
    || { echo "the manifest of $FROM_DIR is invalid; $PART left for inspection" >&2; exit 74; }
while IFS= read -r f; do
    echo "copying $f"
    scp -3 -q -o BatchMode=yes "$FROM_HOST:$FROM_DIR/$f" "$TO_HOST:$PART/$f"
done <<< "$NAMES"
set +e
remote_status "$TO_HOST" "$TO_PY" "$PART" > /dev/null; rc=$?
set -e
(( rc == 0 )) || { echo "verification at the destination failed; $PART left for inspection" >&2; exit 74; }
ssh -T -o BatchMode=yes "$TO_HOST" "mv -T $PART $TO_GRIDS/$GRID" \
    || { echo "could not publish $PART as $TO_GRIDS/$GRID" >&2; exit 74; }
echo "PUBLISHED $TO:$TO_GRIDS/$GRID (copied from $FROM, every file verified)"
