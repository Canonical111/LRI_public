#!/bin/bash
# Mac-side driver of the Stage-4c R7 validation jobs on Expanse (A-FLAG-6; site deviation U1). Run from the repository
# root of the flag-r7 checkout. PKG is an export built by stage4c/scripts/submit_s4c.sh build (C8_S4C_TAG=r7); the
# work directory is $C8_DATA/r7-<sha12 of PKG>; J-SWEEP-1 ($C8_DATA/sweep1-81aa9770e6fe) stands in for the pilot.
#   bash .../dev_r7/scripts/submit_r7.sh prep PKG [--after JOB]           r7_prep.slurm (shared 8, 0:30)
#   bash .../dev_r7/scripts/submit_r7.sh sweep map|exact PKG [--after JOB] r7_sweep.slurm (ONE exclusive compute node, 1:00)
#   bash .../dev_r7/scripts/submit_r7.sh pilot PKG [--after JOB]          r7_pilot.slurm (shared 32, 1:00)
#   bash .../dev_r7/scripts/submit_r7.sh analysis PKG [--after JOB[:JOB]]  r7_analysis.slurm (shared 16, 1:00)
#   bash .../dev_r7/scripts/submit_r7.sh refreeze PKG [--after JOB]       r7_refreeze.slurm (shared 4, 0:45; a copy of the committed file)
# --after adds --dependency=afterok:JOB[:JOB...]. Seeds: r7_seeds.env. Rules as submit_s4c.sh: the existing
# ControlMaster only, and before EVERY sbatch a fresh `squeue -A <ACCOUNT>` with the H7E-R admission (h7_admit.py) and
# this agent's share (job names c8d2-s4c-r7-*: at most 1 compute node and 8 shared jobs live). Worst cases at the time
# limits: prep 8 x 0.5 = 4 SU, sweep 128 x 1 = 128 SU, pilot 32 SU, analysis 16 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2; PFX=c8d2-s4c-r7-; MAXN=1; MAXS=8
R=benchmarks/expanse_2026-10-c8/stage4c; A=$R/dev_r7/admission; mkdir -p "$A"
source "$S/r7_seeds.env"
SOURCE=$D/sweep1-81aa9770e6fe
APPROVAL='D1 (user, 2026-10-03): R7 opt-in, Stage-4c A-FLAG-6 test-only validation measurement; NOT a production approval'
LT=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_r7.XXXXXX")
admit() {  # admit <job name> <partition> <nodes>
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(date +%Y%m%dT%H%M%S).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
  python3 - "$2" "$3" "$LT/squeue.txt" "$PFX" "$MAXN" "$MAXS" <<'PY'
import sys
part, n, path, pfx, maxn, maxs = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
mine = [l.rstrip('\n').split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == '<USER>' and f[6].startswith(pfx)]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if set(f[2].split(',')) & {'compute', 'debug'})
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + n <= maxn) if part in ('compute', 'debug') else (shared + 1 <= maxs)
print(f'agent share {pfx}*: compute nodes {nodes}/{maxn}, shared jobs {shared}/{maxs}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
q() { printf '%q' "$1"; }
sub() {  # sub <name> <partition> <nodes> <env assignments> <sbatch args...>
  local name=$1 part=$2 n=$3 envs=$4; shift 4
  admit "$name" "$part" "$n" >&2
  local id; id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$(date -u +%FT%TZ) $name $id $part $envs $*" >> "$A/submitted.txt"; echo "$id"
}
cmd=${1:-}; shift || true
ARM=; if [ "$cmd" = sweep ]; then ARM=${1:?map or exact}; shift; fi
X=${1:?export path}; shift
AFTER=; if [ "${1:-}" = --after ]; then AFTER=${2:?job id}; shift 2; fi
ssh -T expanse "test -x $X/bin/c8d2_gmp" || [ -n "$AFTER" ] || { echo "$X has no bin/c8d2_gmp: build first (or pass --after its job)" >&2; exit 64; }
dep=${AFTER:+--dependency=afterok:$AFTER}
W=$D/r7-$(basename "$X"); SC=$X/$R/dev_r7/scripts
base="C8_PACKAGE=$X R7_DIR=$W"
case $cmd in
prep)
  id=$(sub "${PFX}prep" shared 1 "$base R7_SOURCE=$SOURCE R7_SEEDS=$(q "$R7_SEED_SWEEP_MAP $R7_SEED_SWEEP_EXACT $R7_SEED_PILOT_MAP $R7_SEED_PILOT_EXACT $R7_SEED_PLANCHECK")" $dep "$SC/r7_prep.slurm");;
sweep)
  case $ARM in map) seed=$R7_SEED_SWEEP_MAP;; exact) seed=$R7_SEED_SWEEP_EXACT;; *) echo "arm must be map or exact" >&2; exit 64;; esac
  id=$(sub "${PFX}sweep$ARM" compute 1 "$base R7_ARM=$ARM R7_SEED=$seed R7_APPROVAL=$(q "$APPROVAL")" $dep "$SC/r7_sweep.slurm");;
pilot)
  id=$(sub "${PFX}pilot" shared 1 "$base R7_SEED_MAP=$R7_SEED_PILOT_MAP R7_SEED_EXACT=$R7_SEED_PILOT_EXACT R7_APPROVAL=$(q "$APPROVAL")" $dep "$SC/r7_pilot.slurm");;
analysis)
  id=$(sub "${PFX}analysis" shared 1 "$base R7_SOURCE=$SOURCE R7_SEED_PLANCHECK=$R7_SEED_PLANCHECK R7_APPROVAL=$(q "$APPROVAL")" $dep "$SC/r7_analysis.slurm");;
refreeze)
  # r7_refreeze.slurm was added after the export: a copy of the committed file goes to $D/work/ (sha256 recorded)
  git diff --quiet HEAD -- "$R/dev_r7/scripts/r7_refreeze.slurm" && git ls-files --error-unmatch "$R/dev_r7/scripts/r7_refreeze.slurm" >/dev/null || { echo "commit r7_refreeze.slurm first" >&2; exit 64; }
  w=$D/work/r7-refreeze-$(date +%Y%m%dT%H%M%S); ssh -T expanse "test ! -e $w && mkdir -p $w"
  scp -q "$R/dev_r7/scripts/r7_refreeze.slurm" "expanse:$w/r7_refreeze.slurm"
  shasum -a 256 "$R/dev_r7/scripts/r7_refreeze.slurm" >&2; ssh -T expanse "sha256sum $w/r7_refreeze.slurm" >&2
  id=$(sub "${PFX}refreeze" shared 1 "$base R7_SOURCE=$SOURCE R7_SEED_PLANCHECK=$R7_SEED_PLANCHECK R7_APPROVAL=$(q "$APPROVAL")" $dep "$w/r7_refreeze.slurm");;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
echo "$cmd${ARM:+ $ARM} $id"
echo "log $D/logs/${PFX}${cmd}${ARM}_$id.out" >&2
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'" >&2
rm -rf "$LT"
