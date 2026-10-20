#!/bin/bash
# Mac-side driver for Stage 4a on Expanse (J-PROF-1..4; PLAN "Performance plan", site deviation U1). Run in the checkout:
#   bash benchmarks/expanse_2026-10-c8/stage4a/scripts/submit_prof_expanse.sh            # build + prof1..prof4
#   JOBS="1 4" bash .../submit_prof_expanse.sh       # only these profiles, on an export that is already built
# 1. Needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login (MFA).
# 2. Exports HEAD with git archive into $C8_DATA/pkg/<sha12> and checks it against the archive (file list, content,
#    modes; ../../ckpt_fix/scripts/export_check.py -> setup/export_check_<sha12>.json). An existing export is refused
#    when the build is requested (it may hold an earlier build); without "build" in JOBS it must already hold
#    bin/c8d2_gmp at the Stage-3 sha256 5c5328af... and the profile jobs are submitted without a dependency.
# 3. Before EVERY sbatch: the H7E-R admission (h7_admit.py on a fresh `squeue -A yun124` snapshot): this session's
#    c8d2-* normal-QOS jobs <= 11 running and <= 27 submitted, the yun124 account <= 32 running, <= 4 c8d2 compute
#    nodes and <= 32 live c8d2 shared jobs, each counted with the new job; a failed or unparsable squeue refuses.
#    With the build and the four profiles, the four exclusive compute nodes are the whole H7E-R node budget.
# 4. Submits the build (shared, 16 CPUs, 32 GB, 30 min; its L8 packs hard-linked from C8_L8_PACKS, default the
#    7aac898 export's) and prof1..prof4 (compute, exclusive, 128 cores, 240 GB; 35/20/25/50 min; afterok on the build).
#    Worst case 128 SU/h x 130 min + the build: ~285 SU; expected ~150 SU.
# Prints every job id with its Slurm log path and evidence directory.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../.."
JOBS=${JOBS:-build 1 2 3 4}
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done (log in to expanse interactively first)" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=/expanse/lustre/scratch/zzheng8/temp_project/c8d2; X=$D/pkg/$T
L8=${C8_L8_PACKS:-$D/pkg/7aac898add43/inputs/packs}
dirty=$(git status --porcelain -- tools src Makefile benchmarks/fixtures8 benchmarks/probes benchmarks/expanse_2026-10-c8/stage4a)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_prof.XXXXXX")
echo "commit under test $H; export $X; jobs: $JOBS; local tmp $LT"
admit() {  # admit <job name> <partition>: a fresh squeue snapshot through h7_admit.py; exits 65/69 on refusal
  ssh -T expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  python3 "$S/h7_admit.py" --site expanse --me zzheng8 --job "$1" --partition "$2" --nodes 1 < "$LT/squeue.txt" | tee -a "$LT/admission.jsonl"
}
ssh -T expanse "lfs quota -u zzheng8 /expanse/lustre/scratch" | tail -3
if ssh -T expanse "test -e $X"; then
  case " $JOBS " in *" build "*) echo "$X exists; remove it to rebuild, or set JOBS to profiles only (e.g. JOBS='1 2 3 4')" >&2; exit 64;; esac
  got=$(ssh -T expanse "sha256sum $X/bin/c8d2_gmp" | cut -c1-64)
  [ "$got" = 5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3 ] || { echo "$X/bin/c8d2_gmp is not the Stage-3 baseline ($got)" >&2; exit 65; }
  DEP=""
else
  case " $JOBS " in *" build "*) ;; *) echo "$X does not exist: a fresh export needs the build; include build in JOBS" >&2; exit 64;; esac
  git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
  ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
  DEP=""
fi
P=$X/benchmarks/expanse_2026-10-c8/stage4a/scripts
for j in $JOBS; do
  if [ "$j" = build ]; then
    admit c8d2-prof-build shared
    b=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/expanse_prof_build.slurm")
    DEP="--dependency=afterok:$b"; echo "build $b: log $D/logs/c8d2-prof-build_$b.out; evidence $D/evidence/$T/profbuild.$b.0"
  else
    case "$j" in 1|2|3|4) ;; *) echo "unknown job '$j' in JOBS (build, 1, 2, 3, 4)" >&2; exit 64;; esac
    admit "c8d2-prof$j" compute
    id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $DEP $P/expanse_prof$j.slurm")
    echo "prof$j $id: log $D/logs/c8d2-prof${j}_$id.out; evidence $D/evidence/$T/prof$j.$id.0"
  fi
done
echo "admission records (one JSON line per submission): $LT/admission.jsonl"
ssh -T expanse "squeue -u zzheng8 -h -o '%i %j %T %P %q %M %l %r'"
