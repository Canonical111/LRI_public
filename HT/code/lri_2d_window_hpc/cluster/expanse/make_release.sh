#!/bin/bash
# Build an immutable release from the committed HEAD (run in the repo, e.g. on the Mac).
# usage: cluster/expanse/make_release.sh OUTDIR REMOTE_RELEASES_DIR
# Writes OUTDIR/ht2d_<commit>.tar, .sha256 (per-file, `sha256sum -c` format, paths ht2d/...)
# and .json (record with the REMOTE paths, tar/manifest sha256 and source_sha256).
set -euo pipefail
repo=$(git rev-parse --show-toplevel); cd "$repo"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "refusing: uncommitted tracked changes" >&2; exit 1; }
out=$1; remote=$2; c=$(git rev-parse --short=12 HEAD)
mkdir -p "$out"; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
tar_=$out/ht2d_$c.tar; man=$out/ht2d_$c.sha256
[[ ! -e "$tar_" ]] || { echo "refusing: $tar_ exists" >&2; exit 1; }
git archive --format=tar --prefix=ht2d/ HEAD > "$tar_"
tar -xf "$tar_" -C "$tmp"
sum(){ if command -v sha256sum >/dev/null; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
( cd "$tmp" && find ht2d -type f -print0 | LC_ALL=C sort -z | while IFS= read -r -d '' f; do sum "$f"; done ) > "$man"
src=$(cd "$tmp/ht2d" && python3 -c 'import sys;sys.path.insert(0,"code");from ht2d.hpc import source_hash;print(source_hash())')
tsha=$(sum "$tar_" | cut -d' ' -f1); msha=$(sum "$man" | cut -d' ' -f1)
python3 - "$out/ht2d_$c.json" <<PY
import json,sys
json.dump({"commit":"$c","tar":"$remote/ht2d_$c.tar","tar_sha256":"$tsha","manifest":"$remote/ht2d_$c.sha256",
 "manifest_sha256":"$msha","source_sha256":"$src","files":$(wc -l < "$man")},open(sys.argv[1],"w"),indent=1)
PY
echo "release $c: tar $tsha source $src"
