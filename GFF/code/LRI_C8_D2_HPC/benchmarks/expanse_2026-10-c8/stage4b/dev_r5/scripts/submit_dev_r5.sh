#!/bin/bash
# Mac-side driver for the Stage-4b R5a/R5b development jobs on Expanse (branch opt-r5; site deviation U1). Run in the
# opt-r5 worktree:
#   bash benchmarks/expanse_2026-10-c8/stage4b/dev_r5/scripts/submit_dev_r5.sh            # export + build + bench
#   JOBS=bench bash .../submit_dev_r5.sh       # the bench job only, on an export that is already built
# 1. Needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login (MFA).
# 2. Exports HEAD with git archive into $C8_DATA/pkg/<sha12> and checks it against the archive (file list, content,
#    modes; ckpt_fix/scripts/{tree_manifest,export_check}.py -> setup/export_check_<sha12>.json). An existing export is
#    refused when the build is requested.
# 3. Before EVERY sbatch: the H7E-R admission (stage4a/scripts/h7_admit.py on a fresh `squeue -A <ACCOUNT>` snapshot), and
#    the Stage-4b Develop-phase share of this agent: at most 1 compute node and 8 live shared jobs named c8d2-r5-*.
# 4. Submits r5_build.slurm (shared, 16 CPUs, 32 GB, 45 min; the L8 packs hard-linked from C8_L8_PACKS, default the
#    c17688158e2b export's, which make re-hashes) and r5_bench.slurm (compute, exclusive, 128 cores, 240 GB, 30 min;
#    afterok on the build). Worst case 128 SU/h x 0.5 h + 16.4 SU/h x 0.75 h = ~76 SU.
# Prints every job id with its Slurm log path and evidence directory.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
JOBS=${JOBS:-build bench}
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=<SCRATCH>/temp_project/c8d2; X=$D/pkg/$T
L8=${C8_L8_PACKS:-$D/pkg/c17688158e2b/inputs/packs}
dirty=$(git status --porcelain -- tools src tests Makefile inputs benchmarks/fixtures8 benchmarks/expanse_2026-10-c8/stage4b/dev_r5/scripts)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_r5.XXXXXX")
echo "commit under test $H; export $X; jobs: $JOBS; local tmp $LT"
admit() {  # admit <job name> <partition>: fresh squeue snapshot; H7E-R through h7_admit.py, then this agent's share
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  python3 "$S/../../../stage4a/scripts/h7_admit.py" --site expanse --me <USER> --job "$1" --partition "$2" --nodes 1 < "$LT/squeue.txt" | tee -a "$LT/admission.jsonl"
  python3 - "$2" "$LT/squeue.txt" <<'PY'
import sys
part, path = sys.argv[1], sys.argv[2]
mine = [l.split('|', 6) for l in open(path) if l.strip()]
mine = [f for f in mine if f[5] == '<USER>' and f[6].startswith('c8d2-r5-')]
nodes = sum(int(f[4]) if f[4].isdigit() else 1 for f in mine if 'compute' in f[2].split(',') or 'debug' in f[2].split(','))
shared = sum(1 for f in mine if 'shared' in f[2].split(','))
ok = (nodes + 1 <= 1) if part in ('compute', 'debug') else (shared + 1 <= 8)
print(f'agent share: c8d2-r5 compute nodes {nodes}, shared jobs {shared}; new {part} job admitted: {ok}')
sys.exit(0 if ok else 65)
PY
}
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -3
if ssh -T expanse "test -e $X"; then
  case " $JOBS " in *" build "*) echo "$X exists; remove it to rebuild, or set JOBS=bench" >&2; exit 64;; esac
  ssh -T expanse "test -x $X/bin/c8d2_gmp" || { echo "$X has no bin/c8d2_gmp; run the build" >&2; exit 64; }
else
  case " $JOBS " in *" build "*) ;; *) echo "$X does not exist: a fresh export needs the build" >&2; exit 64;; esac
  git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
  ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/stage4b/dev_r5/export_check_$T.json"
fi
P=$X/benchmarks/expanse_2026-10-c8/stage4b/dev_r5/scripts; DEP=""
for j in $JOBS; do
  case "$j" in
    build) admit c8d2-r5-build shared
           b=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/r5_build.slurm")
           DEP="--dependency=afterok:$b"; echo "build $b: log $D/logs/c8d2-r5-build_$b.out; evidence $D/evidence/$T/r5build.$b.0";;
    bench) admit c8d2-r5-bench compute
           id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $DEP $P/r5_bench.slurm")
           echo "bench $id: log $D/logs/c8d2-r5-bench_$id.out; evidence $D/evidence/$T/r5bench.$id.0";;
    *) echo "unknown job '$j' in JOBS (build, bench)" >&2; exit 64;;
  esac
done
echo "admission records (one JSON line per submission): $LT/admission.jsonl"
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'"
