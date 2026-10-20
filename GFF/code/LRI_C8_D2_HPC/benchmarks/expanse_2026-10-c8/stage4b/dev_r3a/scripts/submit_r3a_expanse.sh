#!/bin/bash
# Mac-side driver for the R3a development jobs on Expanse (Stage 4b, wf_f7916ef0-f06). Run in the opt-r3a worktree:
#   bash benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts/submit_r3a_expanse.sh            # build + val + speed
#   JOBS="val" bash .../submit_r3a_expanse.sh       # only these, on an export that is already built
# 1. Needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login (MFA).
# 2. Exports HEAD with git archive into $C8_DATA/pkg/<sha12> and checks it against the archive (export_check.py ->
#    ../../../setup/export_check_<sha12>.json). An existing export is refused when the build is requested.
# 3. Before EVERY sbatch: the H7E-R admission (stage4a's h7_admit.py on a fresh `squeue -A <ACCOUNT>`), appended to
#    ../admission/h7e_r_admission.jsonl. Development limits of this agent: at most 1 compute node and 8 live shared jobs.
# 4. Submits the build (shared 16 CPUs, 32 GB, 40 min; L8 packs hard-linked from the 7aac898 export), then the
#    validation (shared 32 CPUs, 64 GB, 2 h) and the speed job (compute, exclusive, 30 min), both afterok on the build.
#    Worst case 0.27 + 66 + 64 SU = ~130 SU; expected ~60 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
JOBS=${JOBS:-build val speed}
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=<SCRATCH>/temp_project/c8d2; X=$D/pkg/$T
L8=${C8_L8_PACKS:-$D/pkg/7aac898add43/inputs/packs}
dirty=$(git status --porcelain -- src tests tools Makefile benchmarks/fixtures8 benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_r3a.XXXXXX"); ADM=$S/../admission/h7e_r_admission.jsonl
echo "commit under test $H; export $X; jobs: $JOBS; local tmp $LT"
admit() {
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$S/../admission/squeue_before_$1.txt"
  python3 "$S/../../../stage4a/scripts/h7_admit.py" --site expanse --me <USER> --job "$1" --partition "$2" --nodes 1 < "$LT/squeue.txt" | tee -a "$ADM"
}
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -3
if ssh -T expanse "test -e $X"; then
  case " $JOBS " in *" build "*) echo "$X exists; remove it to rebuild, or set JOBS without build" >&2; exit 64;; esac
  DEP=""
else
  case " $JOBS " in *" build "*) ;; *) echo "$X does not exist: a fresh export needs the build" >&2; exit 64;; esac
  git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
  ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
  DEP=""
fi
P=$X/benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts
for j in $JOBS; do
  case "$j" in
    build) admit c8d2-r3a-build shared
      b=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/r3a_build.slurm")
      DEP="--dependency=afterok:$b"; echo "build $b: log $D/logs/c8d2-r3a-build_$b.out; evidence $D/evidence/$T/r3abuild.$b.0";;
    val) admit c8d2-r3a-val shared
      v=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $DEP $P/r3a_validate.slurm")
      echo "val $v: log $D/logs/c8d2-r3a-val_$v.out; evidence $D/evidence/$T/r3aval.$v.0";;
    speed) admit c8d2-r3a-speed compute
      s=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $DEP $P/r3a_speed.slurm")
      echo "speed $s: log $D/logs/c8d2-r3a-speed_$s.out; evidence $D/evidence/$T/r3aspeed.$s.0";;
    *) echo "unknown job '$j' (build, val, speed)" >&2; exit 64;;
  esac
done
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %M %l %r'"
