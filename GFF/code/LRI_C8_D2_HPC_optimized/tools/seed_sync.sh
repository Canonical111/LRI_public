#!/bin/bash
# The Mac-side union of our forbidden-seed registry (docs/SITES.md, "Seeds"), modelled on LRI_C8_D2_HPC's
# benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh. The registry is three logs (schema c8-d2-seeds-1):
# symmetry's, Expanse's and the mirror LRI_C8_D2_HPC/designs/forbidden_seeds.json. Run on the Mac:
#   tools/seed_sync.sh                                         make the three logs the union of all three
#   tools/seed_sync.sh --owner SOURCE --seed S [--site X]      the same, then check ownership and issue the receipt
# Each round snapshots both site logs and stops when the two snapshots and the mirror hold the same set of (seed, source)
# entries, the key our seeds.py merge uses (so a second owner of a seed reaches every log); otherwise
# it builds the union of the three locally (our seeds.py merge) and merges it into each site log and the mirror, each
# under that log's own lock (append-only); a seed added on a site after its snapshot is picked up by the next round.
# After C8_SEEDSYNC_ROUNDS (5) rounds without equal entry sets it exits 1, naming what each log lacks.
# With --owner/--seed (after `node_runner.py seed reserve RUN` on site X, which prints SOURCE = c8ind:<RUN>:<sha12>):
# in the union of the converged snapshots and the mirror, S and each of its derived group seeds must have exactly one
# owner, SOURCE (node_runner.py seed receipt). Any other entry is a conflict (e.g. the same seed reserved under another
# source on the other site meanwhile; merge keys on (seed, source), so a merge alone never rejects it): exit 1 and
# re-plan with a new seed. On success seed_receipt.json (seed, owner, the three logs' sha256, the union's sha256, UTC)
# is written to C8_SEEDSYNC_OUT and copied to <RUN>/seed_receipt.json on site X (X from --site, else from RUN's
# filesystem: /expanse/ or /mnt/beegfs/), after checking that RUN's manifest still has the sha256 prefix of SOURCE.
# Needs the Expanse ControlMaster (`ssh -O check expanse` must say "Master running"; never opens a login).
# Environment: C8_SEEDSYNC_PYTHON (default /Users/zheng/anaconda3/bin/python3), C8_SEEDS_TOOL_DIR (our pinned seeds.py
# and common.py, LRI_C8_D2_HPC aafa8a4; default ~/c8ind/c8d2_seedtool/tools; the same path on both sites),
# C8_SEEDS_MIRROR, C8_SEEDSYNC_OUT (default ~/c8ind/seedsync), C8_SEEDSYNC_ROUNDS.
# Exit codes: 0 equal logs (and a receipt), 1 no convergence or an ownership conflict, 64 usage or a pinned-hash
# mismatch, 69 no Expanse ControlMaster.
set -euo pipefail
PKG=$(cd "$(dirname "$0")/.." && pwd)
LPY=${C8_SEEDSYNC_PYTHON:-/Users/zheng/anaconda3/bin/python3}; ROUNDS=${C8_SEEDSYNC_ROUNDS:-5}
TOOL=${C8_SEEDS_TOOL_DIR:-$HOME/c8ind/c8d2_seedtool/tools}
# shellcheck disable=SC2088  # the remote shell expands this tilde (the sites' home directories)
RTOOL='~/c8ind/c8d2_seedtool/tools'
MIRROR=${C8_SEEDS_MIRROR:-/Users/zheng/Documents/Agent_LRI/LRI_C8_D2_HPC/designs/forbidden_seeds.json}
OUTD=${C8_SEEDSYNC_OUT:-$HOME/c8ind/seedsync}
SYM_LOG=/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json; SYM_WORK=/mnt/beegfs/zzheng1/c8-d2-indep/seedsync
EXP_LOG=/expanse/lustre/scratch/zzheng8/temp_project/c8d2/forbidden_seeds.json; EXP_WORK=/expanse/lustre/scratch/zzheng8/temp_project/c8-d2-indep/seedsync
PIN_SEEDS=e65d22232a828429155ae4cc959a4f2600c16e812b723f8ef6957f67f6c1669f; PIN_COMMON=643fdecfd30213a5022e344a5d6042708c78406a20d93564cd916628d395cfef
OWNER=""; SEED=""; SITE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --owner) OWNER=${2:?--owner SOURCE}; shift 2 ;;
    --seed) SEED=${2:?--seed S}; shift 2 ;;
    --site) SITE=${2:?--site expanse|symmetry}; shift 2 ;;
    *) echo "usage: seed_sync.sh [--owner SOURCE --seed S [--site expanse|symmetry]]" >&2; exit 64 ;;
  esac
done
[[ "$ROUNDS" =~ ^[1-9][0-9]*$ ]] || { echo "C8_SEEDSYNC_ROUNDS must be a positive integer" >&2; exit 64; }
if [ -n "$OWNER$SEED" ]; then
  [[ -n "$OWNER" && "$SEED" =~ ^[0-9]+$ ]] || { echo "--owner and --seed go together (--seed a non-negative integer)" >&2; exit 64; }
  [[ "$OWNER" == c8ind:/*:* ]] || { echo "--owner must be a c8ind:<abs RUN>:<sha12> source (node_runner.py seed source RUN)" >&2; exit 64; }
  RUN=${OWNER#c8ind:}; SHA12=${RUN##*:}; RUN=${RUN%:*}
  # RUN reaches remote shells: a plain absolute path only (no spaces, quotes or shell metacharacters), quoted anyway
  [[ "$RUN" =~ ^/[A-Za-z0-9._/+-]+$ && "$SHA12" =~ ^[0-9a-f]{12}$ ]] || { echo "--owner must be c8ind:<abs RUN>:<sha12> with RUN made of [A-Za-z0-9._/+-] and a 12-hex sha; got $OWNER" >&2; exit 64; }
  QRUN=$(printf '%q' "$RUN")
  if [ -z "$SITE" ]; then case "$RUN" in /expanse/*) SITE=expanse ;; /mnt/beegfs/*) SITE=symmetry ;; esac; fi
  [[ "$SITE" == expanse || "$SITE" == symmetry ]] || { echo "cannot tell the site of $RUN; give --site expanse|symmetry" >&2; exit 64; }
fi
sha256() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
pins_ok() { [ "$(printf '%s\n' "$1" | awk '{print $1}' | tr '\n' ' ')" = "$PIN_SEEDS $PIN_COMMON " ]; }
pins_ok "$(sha256 "$TOOL/seeds.py" "$TOOL/common.py")" || { echo "local $TOOL/{seeds,common}.py differ from the pinned LRI_C8_D2_HPC aafa8a4 files; nothing done" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no Expanse ControlMaster; nothing done" >&2; exit 69; }
for h in symmetry expanse; do
  pins_ok "$(ssh -T "$h" "sha256sum $RTOOL/seeds.py $RTOOL/common.py")" || { echo "$h: $RTOOL/{seeds,common}.py differ from the pinned files; nothing done" >&2; exit 64; }
done
T=$(mktemp -d "${TMPDIR:-/tmp}/c8ind_seedsync.XXXXXX"); trap 'rm -rf "$T"' EXIT; ts=$(date -u +%Y%m%dT%H%M%SZ)
ssh -T symmetry "mkdir -p $SYM_WORK"; ssh -T expanse "mkdir -p $EXP_WORK"
fetch() { scp -q "symmetry:$SYM_LOG" "$T/sym.$1.json"; scp -q "expanse:$EXP_LOG" "$T/exp.$1.json"; }
# exit 0 when the three logs hold the same (seed, source) entries; else print what each lacks and exit 1
compare() {
  "$LPY" - "$@" <<'PY'
import json,sys
names=('symmetry','expanse','mirror');docs=[json.load(open(f))for f in sys.argv[1:]]
sets=[{(int(e['seed']),e.get('source'))for e in (d.get('seeds')or d.get('entries')or[])}for d in docs];u=set().union(*sets)
print('(seed, source) entries',dict(zip(names,map(len,sets))),'union',len(u),'distinct seeds',len({x for x,_ in u}),'equal:',all(s==u for s in sets))
for n,s in zip(names,sets):
    if s!=u:print(f'  {n} lacks {len(u-s)}: '+'; '.join(f'{x} ({str(o)[:60]})'for x,o in sorted(u-s,key=str)[:10]))
sys.exit(0 if all(s==u for s in sets)else 1)
PY
}
remote_merge() {  # remote_merge HOST WORKDIR LOG UNION
  scp -q "$T/$4" "$1:$2/$4"
  ssh -T "$1" "source ~/c8ind/LRI_C8_D2_HPC_optimized/slurm/env_$1.sh >/dev/null 2>&1 && python3 -B $RTOOL/seeds.py merge $2/$4 --log $3"
}
ok=0; round=0
while :; do
  round=$((round+1)); fetch "$round"
  if compare "$T/sym.$round.json" "$T/exp.$round.json" "$MIRROR"; then ok=1; break; fi
  if (( round > ROUNDS )); then break; fi
  u="union_${ts}_$round.json"
  "$LPY" -B "$TOOL/seeds.py" merge "$T/sym.$round.json" "$T/exp.$round.json" "$MIRROR" --log "$T/$u"
  remote_merge symmetry "$SYM_WORK" "$SYM_LOG" "$u"
  remote_merge expanse "$EXP_WORK" "$EXP_LOG" "$u"
  "$LPY" -B "$TOOL/seeds.py" merge "$T/$u" --log "$MIRROR"
done
mkdir -p "$OUTD"
cp "$T/sym.$round.json" "$OUTD/${ts}_symmetry.json"; cp "$T/exp.$round.json" "$OUTD/${ts}_expanse.json"; cp "$MIRROR" "$OUTD/${ts}_mirror.json"
(cd "$OUTD" && sha256 "${ts}_symmetry.json" "${ts}_expanse.json" "${ts}_mirror.json" | tee -a sha256.txt)
if (( ! ok )); then
  echo "seed_sync: the logs still differ after $ROUNDS merge round(s) (concurrent additions?); rerun, and plan nothing until they agree" >&2; exit 1
fi
echo "seed_sync: the symmetry and Expanse logs and the mirror hold the same (seed, source) entries (round $round)"
[ -n "$OWNER" ] || exit 0
# Ownership in the union of the converged snapshots and the mirror, then the receipt on site X.
"$LPY" -B "$TOOL/seeds.py" merge "$OUTD/${ts}_symmetry.json" "$OUTD/${ts}_expanse.json" "$OUTD/${ts}_mirror.json" --log "$T/union_final.json" >/dev/null
cp "$T/union_final.json" "$OUTD/${ts}_union.json"
got=$(ssh -T "$SITE" "sha256sum $QRUN/manifest.json" | awk '{print substr($1,1,12)}') || got=""
[ "$got" = "$SHA12" ] || { echo "seed_sync: $SITE:$RUN/manifest.json has sha256 prefix ${got:-none}, not $SHA12 of $OWNER; no receipt" >&2; exit 1; }
receipt="$OUTD/${ts}_seed_receipt.json"
"$LPY" -B "$PKG/tools/node_runner.py" seed receipt --union "$OUTD/${ts}_union.json" --owner "$OWNER" --seed "$SEED" --site "$SITE" \
  --log "symmetry=$OUTD/${ts}_symmetry.json" --log "expanse=$OUTD/${ts}_expanse.json" --log "mirror=$OUTD/${ts}_mirror.json" --rounds "$round" --output "$receipt" >/dev/null \
  || { echo "seed_sync: seed $SEED does not have $OWNER as its single owner (above); no receipt. Re-plan with a new seed" >&2; exit 1; }
scp -q "$receipt" "$SITE:$QRUN/seed_receipt.json.tmp.$$"
ssh -T "$SITE" "mv -f $QRUN/seed_receipt.json.tmp.$$ $QRUN/seed_receipt.json"
echo "seed_sync: seed $SEED is owned by $OWNER alone; receipt $receipt, copied to $SITE:$RUN/seed_receipt.json"
