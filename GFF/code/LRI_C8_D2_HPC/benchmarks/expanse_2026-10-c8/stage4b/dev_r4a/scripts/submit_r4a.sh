#!/bin/bash
# Mac-side driver for the R4a development jobs on Expanse (Stage 4b; run in the opt-r4a worktree):
#   bash benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/scripts/submit_r4a.sh              # export HEAD, build, node
#   JOBS=node bash .../submit_r4a.sh                                                       # node job on the built export
#   C8_R4A_EXTRA="pf=/path/to/other/export/bin" JOBS=node bash .../submit_r4a.sh           # extra speed variants
#   JOBS=trace [C8_R4A_BINS=<built export>/bin] bash .../submit_r4a.sh                      # tracer of HEAD on built binaries
# 1. Needs the existing ControlMaster (`ssh -O check expanse` says "Master running"); never opens a login.
# 2. "build": exports HEAD with git archive into $C8_DATA/pkg/<sha12> (refused if it exists) and checks it against the
#    archive (../../../ckpt_fix/scripts/{tree_manifest,export_check}.py -> setup/export_check_<sha12>.json).
# 3. Before EVERY sbatch: the H7E-R admission (../../../stage4a/scripts/h7_admit.py on a fresh `squeue -A <ACCOUNT>`)
#    and this agent's Develop-phase caps: at most 1 compute node and 8 live shared jobs of its own (c8d2-r4a-*).
# 4. build: shared, 16 CPUs, 32 GB, 1 h (~0.3-0.5 SU); node: compute exclusive, 30 min (<= 64 SU), afterok on the
#    build when both are submitted. Prints every job id with its log and evidence paths.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
JOBS=${JOBS:-build node}
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster for expanse; nothing done" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=<SCRATCH>/temp_project/c8d2; X=$D/pkg/$T
L8=${C8_L8_PACKS:-$D/pkg/7aac898add43/inputs/packs}; BASE=${C8_BASELINE_BIN:-$D/pkg/c17688158e2b/bin}
dirty=$(git status --porcelain -- src Makefile tools tests benchmarks/fixtures8 benchmarks/expanse_2026-10-c8/stage4b/dev_r4a ':(exclude)benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/admission')
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_r4a.XXXXXX")
ADM=benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/admission; mkdir -p "$ADM"
echo "commit under test $H; export $X; jobs: $JOBS"
admit() {  # admit <job name> <partition>
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$ADM/squeue_$(date +%Y%m%dT%H%M%S)_$1.txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes 1 < "$LT/squeue.txt" | tee -a "$ADM/h7e_r_admission.jsonl"
  awk -F'|' -v p="$2" '$6=="<USER>" && $7 ~ /^c8d2-r4a-/ && $2 ~ /^(PENDING|RUNNING|CONFIGURING|COMPLETING)$/ {if ($3 ~ /compute/) n+=$5; if ($3 ~ /shared/) s++}
    END {if (p=="compute" && n+1>1) {print "agent cap: a c8d2-r4a compute node is already live" > "/dev/stderr"; exit 65}
         if (p=="shared" && s+1>8) {print "agent cap: 8 live c8d2-r4a shared jobs" > "/dev/stderr"; exit 65}
         printf "agent caps ok: c8d2-r4a compute nodes %d, shared jobs %d before this %s job\n", n, s, p}' "$LT/squeue.txt"
}
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -3
P=$X/benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/scripts; DEP=""
case " $JOBS " in *" build "*)
  ssh -T expanse "test ! -e $X" || { echo "$X exists; use JOBS=node or remove it" >&2; exit 64; }
  git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
  ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
  admit c8d2-r4a-build shared
  b=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 C8_BASELINE_BIN=$BASE sbatch --parsable --export=ALL $P/expanse_r4a_build.slurm")
  DEP="--dependency=afterok:$b"; echo "build $b: log $D/logs/c8d2-r4a-build_$b.out; evidence $D/evidence/$T/r4abuild.$b.0";;
esac
case " $JOBS " in *" node "*)
  ssh -T expanse "test -x $X/bin/c8d2_gmp" || [ -n "$DEP" ] || { echo "$X is not built" >&2; exit 64; }
  admit c8d2-r4a-node compute
  n=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_R4A_EXTRA='${C8_R4A_EXTRA:-}' sbatch --parsable --export=ALL $DEP $P/expanse_r4a_node.slurm")
  echo "node $n: log $D/logs/c8d2-r4a-node_$n.out; evidence $D/evidence/$T/r4anode.$n.0";;
esac
case " $JOBS " in *" trace "*)  # the tracer of HEAD on the executables of an export built earlier (C8_R4A_BINS)
  BINS=${C8_R4A_BINS:-$D/pkg/6bdc081cc8bd/bin}
  if ! ssh -T expanse "test -e $X"; then
    git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
    ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
    python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
  fi
  admit c8d2-r4a-trace shared
  t=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_BINS=$BINS C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/expanse_r4a_trace.slurm")
  echo "trace $t: log $D/logs/c8d2-r4a-trace_$t.out; evidence $D/evidence/$T/r4atrace.$t.0";;
esac
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'"
