#!/bin/bash
# Mac-side driver of the R3b `dd` development jobs on Expanse (Stage 4c; PLAN A-FLAG-4; site deviation U1). Run from
# the repository root of the dd worktree. The export and its build are the framework's:
#   C8_S4C_TAG=dd C8_S4C_PROFILES=dd bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh precheck|build
# This script adds the dd development jobs on such an export (PKG = $C8_DATA/pkg/<sha12>):
#   ... dev PKG [--after JOB] [NAME=VALUE ...]     dd_dev.slurm (shared, 32 CPUs, 64 GB, 1:00): accuracy test,
#                                                   variants, F1 at F1_SCALE (0.25) with its own baseline, summary
#   ... speed PKG [--after JOB] [NAME=VALUE ...]   dd_speed.slurm (ONE exclusive compute node, 0:30): F4 of each
#                                                   executable of SPEED ("dd dd_direct"), F1 at F1_SCALE (1)
# NAME=VALUE pass through to the job (F1_SCALE, ACC_N, VARIANTS, SPEED, F1_EXTRA, F1_EXES, F1_BASELINE). Rules as submit_s4c.sh's: the existing
# ControlMaster only (never opens a login); before EVERY sbatch a fresh `squeue -A yun124` with the H7E-R admission
# (stage4a/scripts/h7_admit.py) and the agent share of C8_S4C_TAG=dd: its live jobs c8d2-s4c-dd-* use at most
# C8_S4C_MAX_NODES (1) compute nodes and C8_S4C_MAX_SHARED (8) shared jobs. Records: stage4c/admission/dd/.
# Worst cases at the time limits: dev 32 x 1 = 32 SU; speed 128 x 0.5 = 64 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=/expanse/lustre/scratch/zzheng8/temp_project/c8d2
TAGN=dd; MAXN=${C8_S4C_MAX_NODES:-1}; MAXS=${C8_S4C_MAX_SHARED:-8}; PFX=c8d2-s4c-$TAGN-
R=benchmarks/expanse_2026-10-c8/stage4c; A=$R/admission/$TAGN; mkdir -p "$A"
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_dd.XXXXXX")
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me zzheng8 --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" "$PFX" "$MAXN" "$MAXS" <<'PY'
import sys
part, n, path, pfx, maxn, maxs = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == 'zzheng8' and f[6].startswith(pfx)]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= maxn) if part in ('compute', 'debug') else (shared + 1 <= maxs)
print(f'agent share {pfx}*: compute nodes {nodes}/{maxn}, shared jobs {shared}/{maxs}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
cmd=${1:-}; shift || true
case $cmd in
dev|speed)
  X=${1:?export path}; shift; AFTER=
  if [ "${1:-}" = --after ]; then AFTER=${2:?job id}; shift 2; fi
  envs="C8_PACKAGE=$X"; for kv in "$@"; do [[ $kv =~ ^(F1_SCALE|ACC_N|VARIANTS|SPEED|F1_EXTRA|F1_EXES|F1_BASELINE)=.*$ ]] || { echo "unknown setting $kv" >&2; exit 64; }; envs="$envs $(printf '%q' "$kv")"; done
  ssh -T expanse "test -d $X/bin || test -n '$AFTER'" || { echo "$X has no bin/: build it first (or pass --after its job)" >&2; exit 64; }
  if [ "$cmd" = dev ]; then name=${PFX}dev; part=shared; script=dd_dev.slurm; else name=${PFX}speed; part=compute; script=dd_speed.slurm; fi
  admit "$name" "$part" 1 >&2
  id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL -J $name ${AFTER:+--dependency=afterok:$AFTER} $X/$R/dev_dd/scripts/$script")
  echo "$(date -u +%FT%TZ) $name $id $part $envs ${AFTER:+--dependency=afterok:$AFTER} $X/$R/dev_dd/scripts/$script" >> "$A/submitted.txt"
  echo "$cmd $id"
  ev=s4cdd; [ "$cmd" = speed ] && ev=s4cddspeed
  echo "log $D/logs/${name}_$id.out; evidence $D/evidence/$(basename "$X")/$ev.$id.0" >&2;;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
ssh -T expanse "squeue -u zzheng8 -h -o '%i %j %T %P %q %M %l %r'" >&2
rm -rf "$LT"
