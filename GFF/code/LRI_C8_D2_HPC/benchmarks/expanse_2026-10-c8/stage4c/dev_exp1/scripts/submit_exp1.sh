#!/bin/bash
# Mac-side driver of the R4c `exp1` development jobs on Expanse (Stage 4c; agent tag exp1). Run from the root of the
# flag-exp1 checkout:
#   bash benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/scripts/submit_exp1.sh probecheck TREE [--after JOB]
#       TREE: the work directory of `submit_s4c.sh precheck` (pass --after its job): copies this directory's probe
#       files into it and runs exp1_probecheck.slurm (shared, 4 CPUs, 0:15), which compiles exp1_probe.cpp with the
#       build commands of the tree's bin/c8d2_gmp and bin/c8d2_gmp_exp1. No commit needed.
# After `submit_s4c.sh build` of a commit that contains these scripts (PKG = the export):
#   bash benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/scripts/submit_exp1.sh smoke PKG [--after JOB]
#       exp1_smoke.slurm (shared, 32 CPUs, 64 GB, 0:30): the probe and numerics_flags.py F1/F4 at smoke sizes.
#   ... node PKG [--after JOB]
#       exp1_node.slurm (ONE exclusive compute node, 0:30): the probe at full development sizes (the bound on every
#       graph), F1 at --f1-scale 0.25 and F4 on the full L8 sweep sample.
# The admission is submit_s4c.sh's: the existing ControlMaster only, then before EVERY sbatch a fresh `squeue -A <ACCOUNT>`
# through stage4a/scripts/h7_admit.py (H7E-R) and the agent share (jobs c8d2-s4c-exp1-*: <= 1 compute node, <= 8
# shared jobs). Records: stage4c/admission/exp1/.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2; TAGN=exp1; MAXN=1; MAXS=8; PFX=c8d2-s4c-$TAGN-
R=benchmarks/expanse_2026-10-c8/stage4c; A=$R/admission/$TAGN; mkdir -p "$A"; X1=$R/dev_exp1/scripts
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_exp1.XXXXXX")
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
sub() {  # sub <name> <partition> <nodes> <env assignments> <sbatch args...>: admission, then sbatch; prints the job id
  local name=$1 part=$2 n=$3 envs=$4; shift 4
  admit "$name" "$part" "$n" >&2
  local id; id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL -J $name $*")
  echo "$(date -u +%FT%TZ) $name $id $part $envs $*" >> "$A/submitted.txt"; echo "$id"
}
q() { printf '%q' "$1"; }
cmd=${1:-}; shift || true
X=${1:?export path}; shift
AFTER=; if [ "${1:-}" = --after ]; then AFTER=${2:?job id}; shift 2; fi
dep=${AFTER:+--dependency=afterok:$AFTER}
[ "$cmd" = probecheck ] || ssh -T expanse "test -f $X/$X1/exp1_probe.py" || { echo "$X has no $X1/exp1_probe.py: build an export of a commit with these scripts" >&2; exit 64; }
case $cmd in
probecheck)
  ssh -T expanse "test -d $X/src && mkdir -p $X/$X1"
  COPYFILE_DISABLE=1 tar --no-mac-metadata --no-xattrs -cf - "$X1/exp1_probe.cpp" "$X1/exp1_probe.py" "$X1/exp1_probecheck.slurm" | ssh -T expanse "tar -x -C $X"
  id=$(sub "${PFX}probecheck" shared 1 "C8_PRECHECK=$X" $dep "$X/$X1/exp1_probecheck.slurm")
  echo "probecheck $id"; echo "log $D/logs/${PFX}probecheck_$id.out; record $X/probecheck_$id/exp1_probe.json" >&2;;
smoke)
  P=${PROBE_ARGS:---bound-graphs 20 --census-graphs 6 --census-points 256 --lxcensus-points 4096 --forced-graphs 4 --forced-points 2 --timing-graphs 2 --timing-points 1 --timing-rounds 1 --timing-reps 2}
  F=${FLAGS_ARGS:---f4-sample 10 --f4-repeats 1}
  id=$(sub "${PFX}smoke" shared 1 "C8_PACKAGE=$X PROBE_ARGS=$(q "$P") F1_SCALE=${F1_SCALE:-0.05} FLAGS_ARGS=$(q "$F")" $dep "$X/$X1/exp1_smoke.slurm")
  echo "smoke $id"; echo "log $D/logs/${PFX}smoke_$id.out; evidence $D/evidence/$(basename "$X")/s4cexp1smoke.$id.0" >&2;;
node)
  id=$(sub "${PFX}node" compute 1 "C8_PACKAGE=$X${PROBE_ARGS:+ PROBE_ARGS=$(q "$PROBE_ARGS")} F1_SCALE=${F1_SCALE:-0.25}${FLAGS_ARGS:+ FLAGS_ARGS=$(q "$FLAGS_ARGS")}${FLAGS2_ARGS:+ FLAGS2_ARGS=$(q "$FLAGS2_ARGS")}" $dep "$X/$X1/exp1_node.slurm")
  echo "node $id"; echo "log $D/logs/${PFX}node_$id.out; evidence $D/evidence/$(basename "$X")/s4cexp1.$id.0" >&2;;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'" >&2
rm -rf "$LT"
