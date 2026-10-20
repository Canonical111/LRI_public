#!/bin/bash
# Bring the published outputs of one plan back from a site and index them.
#
#   cluster/sitekit/collect.sh --site SITE [--host HOST] [--root PATH] [--plan-name NAME]
#                              [--dest DIR] [--python PY]
# (site wrappers: cluster/expanse/collect.sh, cluster/symmetry/collect.sh)
#
# On the host: outputs/<NAME>/ and receipts/ are packed into ONE tarball
#   <root>/collected/<NAME>_<UTC>.tar (+ .sha256) - small JSON/text files only.
# Here: the tarball is copied and its checksum verified, every task directory is
# verified strictly (cluster/sitekit/manifests.py), and two indexes are written:
#   <DEST>/record_index.json         cluster/collect_records.py --compare-overlaps
#   <DEST>/overlap_vs_archived.json  compare.py archive-overlaps against data/hamiltonian/raw
# Neither runs a continuum fit or claims a new C2. With --host "" the script
# works on the shared filesystem directly (run it on the site's login node).
# Records from several sites are merged with cluster/sitekit/merge_records.py.
# Defaults: host and root from cluster/SITE/profile.json, --plan-name
#   production_plan, --dest outputs/<SITE>/<NAME>_<UTC>, --python python3 (needs numpy).
set -eo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
SITE=""; HOST=__profile__; LUSTRE_ROOT=""; PLAN_NAME=production_plan
DEST=""; PY=${PYTHON:-python3}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --site) SITE=$2; shift 2 ;;
        --host) HOST=$2; shift 2 ;;
        --root|--lustre-root) LUSTRE_ROOT=$2; shift 2 ;;
        --plan-name) PLAN_NAME=$2; shift 2 ;;
        --dest) DEST=$2; shift 2 ;;
        --python) PY=$2; shift 2 ;;
        -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
        *) echo "unknown option $1" >&2; exit 64 ;;
    esac
done
[[ -f "$ROOT/cluster/$SITE/profile.json" ]] || { echo "--site must name a profile in cluster/<site>/profile.json" >&2; exit 64; }
read -r PROFILE_HOST PROFILE_ROOT < <(python3 -c '
import json, sys
p = json.load(open(sys.argv[1]))
print(p["ssh_host"], p["paths"]["persistent_root"].replace("{user}", "$USER"))' "$ROOT/cluster/$SITE/profile.json")
[[ "$HOST" == __profile__ ]] && HOST=$PROFILE_HOST
LUSTRE_ROOT=${LUSTRE_ROOT:-$PROFILE_ROOT}
[[ "$PLAN_NAME" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "bad plan name" >&2; exit 64; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
name="${PLAN_NAME}_${stamp}"
DEST=${DEST:-$ROOT/outputs/$SITE/$name}
if command -v sha256sum > /dev/null; then SHA=(sha256sum); else SHA=(shasum -a 256); fi

# GNU tar exits 1 when a file changed while it was read: only receipts of jobs
# that are still finishing can change (published outputs are immutable and are
# verified below), so that case is reported and accepted.
pack="cd $LUSTRE_ROOT && test -d outputs/$PLAN_NAME && mkdir -p collected || exit 66
tar -cf collected/$name.tar --exclude='.*.partial.*' outputs/$PLAN_NAME receipts; rc=\$?
if [ \$rc -eq 1 ]; then echo 'WARNING: some receipts changed while packing (jobs still finishing); collect again later' >&2
elif [ \$rc -ne 0 ]; then exit 74; fi
(cd collected && sha256sum $name.tar > $name.tar.sha256) && echo \$PWD/collected/$name.tar"
mkdir -p "$DEST"
if [[ -n "$HOST" ]]; then
    remote_tar=$(ssh -T -o BatchMode=yes "$HOST" "$pack" | tail -1)
    [[ "$remote_tar" == /*.tar ]] || { echo "packing on $HOST failed" >&2; exit 74; }
    scp -q -o BatchMode=yes "$HOST:$remote_tar" "$HOST:$remote_tar.sha256" "$DEST/"
else
    remote_tar=$(bash -c "$pack" | tail -1)
    [[ "$remote_tar" == /*.tar ]] || { echo "packing failed" >&2; exit 74; }
    cp "$remote_tar" "$remote_tar.sha256" "$DEST/"
fi
( cd "$DEST" && "${SHA[@]}" -c "$name.tar.sha256" )
tar -xf "$DEST/$name.tar" -C "$DEST"
# Strict verification (manifests.py): non-empty, well-formed SHA256SUMS whose entries
# all verify, no unlisted files or subdirectories, required receipts and one record
# per lambda, and nothing else in the plan directory. Only the verified record
# paths it lists are indexed and compared (no globbing).
"$PY" "$ROOT/cluster/sitekit/manifests.py" verify-rows "$DEST/outputs/$PLAN_NAME" \
    --list-records "$DEST/verified_records.txt" \
    || { echo "incomplete, corrupt or stray content in $DEST/outputs/$PLAN_NAME (see above)" >&2; exit 74; }
"$PY" "$ROOT/cluster/collect_records.py" --records-from "$DEST/verified_records.txt" --compare-overlaps \
    --output "$DEST/record_index.json"
"$PY" "$ROOT/cluster/sitekit/compare.py" archive-overlaps "$DEST/outputs/$PLAN_NAME" "$ROOT/data/hamiltonian/raw" \
    --records-from "$DEST/verified_records.txt" --out "$DEST/overlap_vs_archived.json" > /dev/null
echo "COLLECTED $DEST (record_index.json, overlap_vs_archived.json)"
