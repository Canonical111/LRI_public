#!/bin/bash
# The two-log rule (docs/HPC.md, "The seed log"): make symmetry's and Expanse's $C8_SEEDS and the package mirror
# designs/forbidden_seeds.json each the union of ALL THREE logs, with tools/seeds.py merge (under each log's lock;
# nothing removed or reordered). Run from the Mac after every seeds.py add on either site:
#   bash seedsync.sh <label>
# Each round snapshots both site logs, stops when the two snapshots and the mirror hold the same seed set, and otherwise
# builds the union of the three (locally) and merges it into each site log and into the mirror; a seed added on a site
# while a round runs (after its snapshot) is picked up by the next round. The script exits 0 only when a final
# snapshot of both logs and the mirror hold identical seed sets; after C8_SEEDSYNC_ROUNDS (5) rounds without that it
# exits 1, naming the seeds each log lacks (X21; before, a seed added on symmetry after its snapshot never reached
# Expanse, mirror-only seeds never left the mirror, and unequal logs still exited 0).
# Needs the Expanse ControlMaster (`ssh -O check expanse` must say "Master running"; never opens a login). Copies of
# both logs after the sync go to stage5/seeds/<label>_{symmetry,expanse}.json with their sha256.
# C8_SEEDSYNC_PYTHON: the local Python (default /Users/zheng/anaconda3/bin/python3); tests/unit_orchestration.py runs
# this script on fake ssh/scp.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); R=$(cd "$S/.." && pwd); PKG=$(cd "$R/../../.." && pwd); label=${1:?label}
LPY=${C8_SEEDSYNC_PYTHON:-/Users/zheng/anaconda3/bin/python3}; ROUNDS=${C8_SEEDSYNC_ROUNDS:-5}
[[ "$ROUNDS" =~ ^[1-9][0-9]*$ ]] || { echo "C8_SEEDSYNC_ROUNDS must be a positive integer" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no Expanse ControlMaster; nothing done" >&2; exit 69; }
SYM=/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json; XD=/expanse/lustre/scratch/zzheng8/temp_project/c8d2; XL=$XD/forbidden_seeds.json
XW=$XD/work/s5sym-seeds-5d7586e9f1ab; YW=/mnt/beegfs/zzheng1/c8d2/work/s5-seeds; YT=/mnt/beegfs/zzheng1/c8d2/pkg/5d7586e9f1ab/tools/seeds.py
MIRROR=$PKG/designs/forbidden_seeds.json
T=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_seedsync.XXXXXX"); trap 'rm -rf "$T"' EXIT; ts=$(date -u +%Y%m%dT%H%M%SZ)
if ! ssh -T expanse "test -f $XW/tools/seeds.py"; then
  (cd "$PKG" && git archive --format=tar 5d7586e9f1ab0b7f9e4bdf7226a62e09c8a04e3a tools/seeds.py tools/common.py tools/production.py) | ssh -T expanse "mkdir -p $XW && tar -x -C $XW"
fi
ssh -T symmetry "mkdir -p $YW"
fetch() { scp -q "symmetry:$SYM" "$T/sym.$1.json"; scp -q "expanse:$XL" "$T/exp.$1.json"; }
# exit 0 when the logs hold the same seed set; else print what each log lacks and exit 1
compare() {
  "$LPY" - "$@" <<'PY'
import json,sys
names=('symmetry','expanse','mirror');sets=[{int(e['seed'])for e in (json.load(open(f)).get('seeds')or json.load(open(f)).get('entries')or[])}for f in sys.argv[1:]]
u=set().union(*sets)
print('seed counts',dict(zip(names,map(len,sets))),'union',len(u),'equal sets:',all(s==u for s in sets))
for n,s in zip(names,sets):
    if s!=u:print(f'  {n} lacks {sorted(u-s)}')
sys.exit(0 if all(s==u for s in sets)else 1)
PY
}
ok=0; round=0
while :; do
  round=$((round+1)); fetch "$round"
  if compare "$T/sym.$round.json" "$T/exp.$round.json" "$MIRROR"; then ok=1; break; fi
  if (( round > ROUNDS )); then break; fi
  # the union of the three logs, then into each log (seeds.py merge: under the log's own lock, append-only)
  u="union_${ts}_$round.json"
  (cd "$PKG" && "$LPY" -B tools/seeds.py merge "$T/sym.$round.json" "$T/exp.$round.json" "$MIRROR" --log "$T/$u")
  scp -q "$T/$u" "symmetry:$YW/$u"
  ssh -T symmetry "source ~/c8d2/env.sh; python3 -B $YT merge $YW/$u --log $SYM"
  scp -q "$T/$u" "expanse:$XW/$u"
  ssh -T expanse "source ~/c8d2/env_expanse.sh >/dev/null 2>&1; cd $XW && python3 -B tools/seeds.py merge $u --log $XL"
  (cd "$PKG" && "$LPY" -B tools/seeds.py merge "$T/$u" --log "$MIRROR")
done
mkdir -p "$R/seeds"
cp "$T/sym.$round.json" "$R/seeds/${label}_symmetry.json"; cp "$T/exp.$round.json" "$R/seeds/${label}_expanse.json"
sha256() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$@"; else sha256sum "$@"; fi; }
(cd "$R/seeds" && sha256 "${label}_symmetry.json" "${label}_expanse.json" ../../../../designs/forbidden_seeds.json | tee -a sha256.txt)
if (( ok )); then echo "seedsync: the symmetry and Expanse logs and the mirror hold the same seeds (round $round)"; exit 0; fi
echo "seedsync: the logs still differ after $ROUNDS merge round(s) (concurrent additions?); rerun, and plan nothing until they agree" >&2
exit 1
