#!/bin/bash
# Mac driver of the post-merge re-validation on Expanse (G5 fixes F1-F9 merged into c8; evidence in
# benchmarks/expanse_2026-10-c8/stage5/fix/). Run from the repository root of the main checkout, one step at a time:
#   fxe.sh export            git archive HEAD -> $C8_DATA/pkg/<sha12> (the workflow's ONE new export; an existing one is
#                            refused), checked file by file (benchmarks/expanse_2026-10-c8/setup/export_check_<sha12>.json)
#   fxe.sh exp1 X            J-EXP-1 on debug (fxe_exp1.slurm): build + make test of export X
#   fxe.sh flag X [DEP]      the dd+mp256 J-FLAG gate (fxe_flag.slurm) on compute with --exclude=<NODE>, afterok DEP
# Rules: the existing ControlMaster only (`ssh -O check expanse` must say "Master running"; never opens a login); before
# EVERY sbatch a fresh `squeue -A <ACCOUNT>` and the H7E-R admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS <= 11
# running / 27 submitted, account <= 32 running, c8d2 shared <= 32 live, c8d2 compute+debug nodes <= 4). Records go to
# fix/admission/.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster for expanse; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2; R=benchmarks/expanse_2026-10-c8/stage5/fix; A=$R/admission; P=$R/scripts; mkdir -p "$A"
LT=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_fxe.XXXXXX"); trap 'rm -rf "$LT"' EXIT
stamp() { date +%Y%m%dT%H%M%S; }
admit() {  # admit <job name> <partition> <nodes>: H7E-R on a fresh snapshot; exits 65 when refused
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(stamp).txt"
  <HOME>/anaconda3/bin/python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
}
sub() {  # sub <name> <partition> <nodes> <env assignments> <sbatch args...>: admission, then sbatch; prints the job id
  local name=$1 part=$2 n=$3 envs=$4; shift 4
  admit "$name" "$part" "$n" >&2
  local id; id=$(ssh -T expanse "cd $D && $envs sbatch --parsable --export=ALL $*")
  echo "$(date -u +%FT%TZ) $name $id $part $envs $*" >> "$A/submitted.txt"; echo "$id"
}
step=${1:?step}; shift
case $step in
export)
  dirty=$(git status --porcelain -- tools src tests Makefile inputs gen slurm vendor cost_models benchmarks/fixtures8 "$P")
  [ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
  h=$(git rev-parse HEAD); t=${h:0:12}; x=$D/pkg/$t
  ssh -T expanse "timeout 120 lfs quota -u <USER> /expanse/lustre/scratch 2>&1" | tail -3 | tee -a "$A/lfs_quota.txt"
  if ssh -T expanse "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T expanse "mkdir -p $x && tar -x -C $x"
  ssh -T expanse "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/tree.txt"
  <HOME>/anaconda3/bin/python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/tree.txt" expanse "$x" "benchmarks/expanse_2026-10-c8/setup/export_check_$t.json" >&2
  echo "$x";;
exp1)
  X=$1; id=$(sub c8d2-fxe-exp1 debug 1 "C8_PACKAGE=$X" "$X/$P/fxe_exp1.slurm")
  echo "J-EXP-1 job $id; log $D/logs/c8d2-fxe-exp1_$id.out; evidence $D/evidence/$(basename "$X")/fxeexp1.$id.0";;
flag)
  X=$1; dep=${2:+--dependency=afterok:$2}
  id=$(sub c8d2-fxe-flag compute 1 "C8_PACKAGE=$X" --exclude=<NODE> $dep "$X/$P/fxe_flag.slurm")
  echo "J-FLAG dd+mp256 job $id; log $D/logs/c8d2-fxe-flag_$id.out; evidence $D/evidence/$(basename "$X")/fxeflag.$id.0";;
*) sed -n '2,/^set -euo/p' "$0" | sed '$d' >&2; exit 64;;
esac
