#!/bin/bash
# Mac-side driver of the Stage-4b R4f development probe on Expanse (site deviation U1). Run in the checkout (worktree):
#   bash benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts/submit_r4f_expanse.sh
#   JOBS="speed" bash .../submit_r4f_expanse.sh     # only these jobs, on an export that already exists
# Jobs (JOBS, default all, in this order): def (r4f_default_build: the default build, == Stage 3), gmpfat and gmphost
# (r4f_gmp_build: GMP 6.2.1 --enable-fat / --host=<config.guess>, make check, install, the workers with GMP_PREFIX),
# valfat and valhost (r4f_validate: replay subset, G-L8SELF, perf and tier timers; afterok def + their gmp job), speed
# (r4f_speed: one exclusive compute node, <= 30 min; afterok def, gmpfat, gmphost). A predecessor not submitted in the
# same call must have finished already. control (r4f_control: the layout control; not in the default JOBS) needs only
# the installed host GMP and builds its own workers, so JOBS=control runs on a fresh export without def.
# 1. Needs the existing ControlMaster (`ssh -O check expanse` must say "Master running"); never opens a login (MFA).
# 2. Exports HEAD with git archive into $C8_DATA/pkg/<sha12> and checks it against the archive (export_check.py ->
#    setup/export_check_<sha12>.json); an existing export is refused when def is requested.
# 3. Before EVERY sbatch: the H7E-R admission (stage4a/scripts/h7_admit.py on a fresh `squeue -A yun124`) and the
#    per-agent caps of the Stage-4b development phase: at most R4F_MAX_SHARED=8 live c8d2-r4f-* shared jobs and
#    R4F_MAX_NODES=1 live c8d2-r4f-* compute node, each counted with the new job. A failed squeue refuses.
# Worst case: shared 16 CPUs x (0.67 + 2 x 1 h) + 2 x 32.8 x 1 h + one node x 0.5 h = about 151 SU; expected about 110.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
# git archive and git status act on the current directory's subtree: refuse unless this is the repository root.
[ "$(git rev-parse --show-toplevel)" = "$(pwd -P)" ] || { echo "not at the repository root: $(pwd -P)" >&2; exit 64; }
JOBS=${JOBS:-def gmpfat gmphost valfat valhost speed}
R4F_MAX_SHARED=8; R4F_MAX_NODES=1
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "ssh -O check expanse: no ControlMaster running; nothing done" >&2; exit 69; }
H=$(git rev-parse HEAD); T=${H:0:12}; D=/expanse/lustre/scratch/zzheng8/temp_project/c8d2; X=$D/pkg/$T
L8=${C8_L8_PACKS:-$D/pkg/c17688158e2b/inputs/packs}
dirty=$(git status --porcelain -- tools src Makefile tests benchmarks/fixtures8 benchmarks/probes benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_r4f.XXXXXX")
echo "commit under test $H; export $X; jobs: $JOBS; local tmp $LT"
admit() {  # admit <job name> <partition>: H7E-R (h7_admit.py) plus the per-agent caps, on one fresh squeue snapshot
  ssh -T expanse "squeue -A yun124 -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing more submitted" >&2; exit 69; }
  python3 "$S/../../../stage4a/scripts/h7_admit.py" --site expanse --me zzheng8 --job "$1" --partition "$2" --nodes 1 < "$LT/squeue.txt" | tee -a "$LT/admission.jsonl"
  local sh nd
  sh=$(awk -F'|' '$6=="zzheng8" && $7 ~ /^c8d2-r4f-/ && $3 ~ /shared/' "$LT/squeue.txt" | wc -l)
  nd=$(awk -F'|' '$6=="zzheng8" && $7 ~ /^c8d2-r4f-/ && $3 ~ /compute|debug/ {n+=$5} END {print n+0}' "$LT/squeue.txt")
  if [ "$2" = shared ] && [ $((sh + 1)) -gt $R4F_MAX_SHARED ]; then echo "per-agent cap: $sh live c8d2-r4f shared jobs; refused $1" >&2; exit 65; fi
  if [ "$2" = compute ] && [ $((nd + 1)) -gt $R4F_MAX_NODES ]; then echo "per-agent cap: $nd live c8d2-r4f compute nodes; refused $1" >&2; exit 65; fi
  echo "{\"job\": \"$1\", \"r4f_shared_live\": $sh, \"r4f_nodes_live\": $nd, \"r4f_caps\": [$R4F_MAX_SHARED, $R4F_MAX_NODES]}" | tee -a "$LT/admission.jsonl"
  cp "$LT/squeue.txt" "$LT/squeue_$1_$(date +%H%M%S).txt"
}
ssh -T expanse "lfs quota -u zzheng8 /expanse/lustre/scratch" | tail -3
if ssh -T expanse "test -e $X"; then
  case " $JOBS " in *" def "*) echo "$X exists; remove it to rebuild, or leave def out of JOBS" >&2; exit 64;; esac
else
  case " $JOBS " in *" def "*|" control ") ;; *) echo "$X does not exist: a fresh export needs def (control alone builds its own)" >&2; exit 64;; esac
  git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
  ssh -T expanse "python3 - $X" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/c8d2_tree_$T.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
fi
P=$X/benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts
# Job ids in plain variables (the Mac's bash 3.2 has no associative arrays): ID_<job>.
dep() { local d="" j v; for j in "$@"; do eval "v=\${ID_$j:-}"; [ -n "$v" ] && d="$d:$v"; done; [ -n "$d" ] && echo "--dependency=afterok$d" || true; }
for j in $JOBS; do
  case "$j" in
    def) n=c8d2-r4f-defbuild; admit $n shared
      id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/r4f_default_build.slurm"); r=r4fdef;;
    gmpfat|gmphost) v=${j#gmp}; n=c8d2-r4f-gmp; admit $n shared
      id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X R4F_VARIANT=$v sbatch --parsable --export=ALL $P/r4f_gmp_build.slurm"); r=r4fgmp-$v;;
    valfat|valhost) v=${j#val}; n=c8d2-r4f-val; admit $n shared
      id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X R4F_VARIANT=$v sbatch --parsable --export=ALL $(dep def gmp$v) $P/r4f_validate.slurm"); r=r4fval-$v;;
    control) n=c8d2-r4f-ctrl; admit $n shared
      id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/r4f_control.slurm"); r=r4fctrl;;
    speed) n=c8d2-r4f-speed; admit $n compute
      id=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL $(dep def gmpfat gmphost) $P/r4f_speed.slurm"); r=r4fspeed;;
    *) echo "unknown job '$j' in JOBS (def gmpfat gmphost valfat valhost speed control)" >&2; exit 64;;
  esac
  [[ "$id" =~ ^[0-9]+$ ]] || { echo "sbatch of $j returned '$id'; stopping" >&2; exit 69; }
  eval "ID_$j=$id"
  echo "$j $id: log $D/logs/${n}_${id}.out; evidence $D/evidence/$T/$r.$id.0"
done
echo "admission records: $LT/admission.jsonl"
ssh -T expanse "squeue -u zzheng8 -h -o '%i %j %T %P %q %M %l %r'"
