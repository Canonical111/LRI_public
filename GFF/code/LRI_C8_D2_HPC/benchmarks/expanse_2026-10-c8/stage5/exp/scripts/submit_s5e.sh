#!/bin/bash
# Mac driver of the Stage-5 Expanse jobs (site deviation U1; PLAN "Expanse (J-EXP-1..4)", J-SWEEP-2, J-PIL-1 planned for
# the H11 window). Run from the repository root of the main checkout, one step at a time:
#   submit_s5e.sh export                       git archive HEAD -> $C8_DATA/pkg/<sha12> (an existing export is refused),
#                                              checked file by file (setup/export_check_<sha12>.json)
#   submit_s5e.sh exp1   X                     J-EXP-1 on debug (s5e_exp1.slurm): build + make test of export X
#   submit_s5e.sh zen2   X [DEP]               the GMP_PREFIX=zen2 gates (s5e_zen2.slurm), compute, afterok DEP
#   submit_s5e.sh sweep2 X SEED [DEP]          J-SWEEP-2E (s5e_sweep2.slurm), compute, afterok DEP
#   submit_s5e.sh prep   X S2 S3 S4 [DEP]      the J-EXP-2..4 test campaigns (s5e_prep.slurm), shared, afterok DEP
#   submit_s5e.sh exp2|exp3|exp4 X             J-EXP-2/3/4: slurm/submit.sh on the Expanse login node with the plan's
#                                              variables; its output (snapshot numbers, admission decision, job ids) is
#                                              kept in admission/<step>_submit_<time>.txt
#   submit_s5e.sh pilotplan X SEED SYMLOG CM   J-PIL-1E (CM: the J-SWEEP-2E cost model): slurm/plan.sh on shared (-c 8 --mem=15G -t 01:00:00 --no-requeue),
#                                              --forbid-seeds-from the Expanse log AND SYMLOG (a read-only copy of the
#                                              symmetry log on Expanse); nothing else is submitted
# Rules: the existing ControlMaster only (`ssh -O check expanse` must say "Master running"); before EVERY sbatch a fresh
# `squeue -A <ACCOUNT>` and the H7E-R admission (stage4a/scripts/h7_admit.py: c8d2 normal-QOS <= 11 running / 27
# submitted, account <= 32 running, c8d2 shared <= 32 live, c8d2 compute+debug nodes <= 4); slurm/submit.sh does its own
# H7E-R admission (k = every new job, merges included) under the site lock. Records go to admission/.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster for expanse; nothing done" >&2; exit 69; }
D=<SCRATCH>/temp_project/c8d2; R=benchmarks/expanse_2026-10-c8/stage5/exp; A=$R/admission; P=$R/scripts; mkdir -p "$A"
LT=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_s5e.XXXXXX"); trap 'rm -rf "$LT"' EXIT
stamp() { date +%Y%m%dT%H%M%S; }
admit() {  # admit <job name> <partition> <nodes>: H7E-R on a fresh snapshot; exits 65 when refused
  ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt" || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  cp "$LT/squeue.txt" "$A/squeue_before_$1_$(stamp).txt"
  python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$1" --partition "$2" --nodes "$3" < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
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
  dirty=$(git status --porcelain -- tools src tests Makefile inputs gen slurm vendor benchmarks/fixtures8 "$P")
  [ -z "$dirty" ] || { echo "uncommitted changes in exported paths; commit first:"; echo "$dirty"; exit 64; } >&2
  h=$(git rev-parse HEAD); t=${h:0:12}; x=$D/pkg/$t
  ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -2 | tee -a "$A/lfs_quota.txt"
  if ssh -T expanse "test -e $x"; then echo "$x exists; refusing" >&2; exit 64; fi
  git archive --format=tar "$h" | ssh -T expanse "mkdir -p $x && tar -x -C $x"
  ssh -T expanse "python3 - $x" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/tree.txt"
  python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/tree.txt" expanse "$x" "benchmarks/expanse_2026-10-c8/setup/export_check_$t.json" >&2
  echo "$x";;
exp1)
  X=$1; id=$(sub c8d2-s5e-exp1 debug 1 "C8_PACKAGE=$X" "$X/$P/s5e_exp1.slurm")
  echo "J-EXP-1 job $id; log $D/logs/c8d2-s5e-exp1_$id.out; evidence $D/evidence/$(basename "$X")/s5eexp1.$id.0";;
exp1b)  # written after the export (J-EXP-1 follow-up): uploaded to $D/work/s5e-<sha12>-scripts/ with its sha256 recorded
  X=$1; W=$D/work/s5e-$(basename "$X")-scripts; ssh -T expanse "mkdir -p $W"
  ssh -T expanse "cat > $W/s5e_exp1b.slurm" < "$P/s5e_exp1b.slurm"
  echo "$(date -u +%FT%TZ) uploaded $P/s5e_exp1b.slurm sha256 $(shasum -a 256 "$P/s5e_exp1b.slurm" | cut -c1-64) remote $(ssh -T expanse "sha256sum $W/s5e_exp1b.slurm" | cut -c1-64)" >> "$A/submitted.txt"
  id=$(sub c8d2-s5e-exp1b debug 1 "C8_PACKAGE=$X" "$W/s5e_exp1b.slurm")
  echo "J-EXP-1b job $id; log $D/logs/c8d2-s5e-exp1b_$id.out; evidence $D/evidence/$(basename "$X")/s5eexp1b.$id.0";;
local)  # local X NAME PARTITION SCRIPT: a script written after the export (diagnostics), uploaded with its sha256 recorded
  X=$1; name=$2; part=$3; f=$4; W=$D/work/s5e-$(basename "$X")-scripts; ssh -T expanse "mkdir -p $W"
  ssh -T expanse "cat > $W/$(basename "$f")" < "$f"
  echo "$(date -u +%FT%TZ) uploaded $f sha256 $(shasum -a 256 "$f" | cut -c1-64) remote $(ssh -T expanse "sha256sum $W/$(basename "$f")" | cut -c1-64)" >> "$A/submitted.txt"
  id=$(sub "$name" "$part" 1 "C8_PACKAGE=$X" "$W/$(basename "$f")")
  echo "$name job $id; log $D/logs/${name}_$id.out";;
zen2)
  X=$1; dep=${2:+--dependency=afterok:$2}; id=$(sub c8d2-s5e-zen2 compute 1 "C8_PACKAGE=$X" $dep "$X/$P/s5e_zen2.slurm")
  echo "zen2 gates job $id; log $D/logs/c8d2-s5e-zen2_$id.out; evidence $D/evidence/$(basename "$X")/s5ezen2.$id.0";;
sweep2)
  X=$1; s=$2; dep=${3:+--dependency=afterok:$3}; id=$(sub c8d2-s5e-sweep2 compute 1 "C8_PACKAGE=$X SWEEP_SEED=$s" $dep "$X/$P/s5e_sweep2.slurm")
  echo "J-SWEEP-2E job $id; log $D/logs/c8d2-s5e-sweep2_$id.out; evidence $D/evidence/$(basename "$X")/s5esweep2.$id.0; campaign $D/sweep2e-$(basename "$X")";;
sweep2x)  # the rerun on another node (the first ran on <NODE>): uploaded script copy, its own campaign directory
  X=$1; s=$2; ex=$3; W=$D/work/s5e-$(basename "$X")-scripts; ssh -T expanse "mkdir -p $W"
  ssh -T expanse "cat > $W/s5e_sweep2.slurm" < "$P/s5e_sweep2.slurm"
  echo "$(date -u +%FT%TZ) uploaded $P/s5e_sweep2.slurm sha256 $(shasum -a 256 "$P/s5e_sweep2.slurm" | cut -c1-64) remote $(ssh -T expanse "sha256sum $W/s5e_sweep2.slurm" | cut -c1-64)" >> "$A/submitted.txt"
  id=$(sub c8d2-s5e-sweep2 compute 1 "C8_PACKAGE=$X SWEEP_SEED=$s C8_SWEEP_RUN=$D/sweep2e-$(basename "$X")-r2" --exclude=$ex "$W/s5e_sweep2.slurm")
  echo "J-SWEEP-2E rerun job $id; log $D/logs/c8d2-s5e-sweep2_$id.out; evidence $D/evidence/$(basename "$X")/s5esweep2.$id.0; campaign $D/sweep2e-$(basename "$X")-r2";;
prep)
  X=$1; dep=${5:+--dependency=afterok:$5}
  id=$(sub c8d2-s5e-prep shared 1 "C8_PACKAGE=$X C8_S5E=$D/s5e-$(basename "$X") S2=$2 S3=$3 S4=$4" $dep "$X/$P/s5e_prep.slurm")
  echo "prep job $id; log $D/logs/c8d2-s5e-prep_$id.out; campaigns $D/s5e-$(basename "$X")/t2,t3,t4";;
exp2|exp3|exp4)
  X=$1; C=$D/s5e-$(basename "$X")
  case $step in
    exp2) RUNV=$C/t2; VARS="C8_SBATCH_ARGS='-A <ACCOUNT> -p shared --mem=62G'"; ARGS=""; part=shared; k=3;;
    exp3) RUNV=$C/t3; VARS="C8_SBATCH_ARGS='-A <ACCOUNT> -p debug' C8_LANE_MEM=240G C8_LANE_TIME=00:25:00 C8_LANES=numa C8_MERGE_TIME=00:30:00"; ARGS="--lanes 1"; part=debug; k=2;;
    exp4) RUNV=$C/t4; VARS="C8_SBATCH_ARGS='-A <ACCOUNT> -p compute' C8_LANE_MEM=240G C8_LANE_TIME=00:30:00"; ARGS="--lanes 1"; part=compute; k=2;;
  esac
  # the record of this driver's H7E-R check (with all k new jobs as nodes for node partitions); slurm/submit.sh decides
  admit "c8d2-s5e-$step" "$part" "$([ $part = shared ] && echo 1 || echo $k)" >&2
  f=$A/${step}_submit_$(stamp).txt
  ssh -T expanse "source \$HOME/c8d2/env_expanse.sh && export C8_ENV_SETUP=\$HOME/c8d2/env_expanse.sh C8_SITE=expanse C8_PACKAGE=$X C8_RUN=$RUNV && export $VARS && \
    echo \"== \$(date -Is) on \$(hostname): C8_RUN=\$C8_RUN C8_SBATCH_ARGS=\$C8_SBATCH_ARGS C8_LANE_MEM=\${C8_LANE_MEM:-} C8_LANE_TIME=\${C8_LANE_TIME:-} C8_LANES=\${C8_LANES:-} C8_MERGE_TIME=\${C8_MERGE_TIME:-}\" && \
    echo \"== expanse-client project <ACCOUNT> -p\" && (expanse-client project <ACCOUNT> -p 2>&1 | head -8) && echo \"== squeue -A <ACCOUNT> before\" && squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j' && \
    echo \"== \$C8_PACKAGE/slurm/submit.sh $ARGS\" && \$C8_PACKAGE/slurm/submit.sh $ARGS; c=\$?; echo \"== submit.sh exit \$c\"; squeue -u <USER> -h -o '%i %j %T %P %M %l %r'; exit \$c" > "$f" 2>&1 && rc=0 || rc=$?
  cat "$f"; echo "$(date -u +%FT%TZ) $step submit.sh $ARGS exit $rc (C8_RUN=$RUNV); output $f" >> "$A/submitted.txt"; exit $rc;;
pilotplan)
  X=$1; s=$2; sym=$3; CM=$4; RUNP=$D/pilot1e-$(date +%Y%m%d)-$(basename "$X")
  id=$(sub c8d2-s5e-pilotplan shared 1 "C8_PACKAGE=$X C8_ENV_SETUP=\$HOME/c8d2/env_expanse.sh" -A <ACCOUNT> -p shared -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue \
       -J c8d2-s5e-pilotplan -o "$D/logs/%x_%j.out" "$X/slurm/plan.sh" "$RUNP" --pilot --points 4096 --replicates 8 --threads 8 --checkpoint-tasks 256 \
       --index-hours 1.5 --backend gmp --cost-model "$CM" --forbid-seeds-from "$D/forbidden_seeds.json" --forbid-seeds-from "$sym" --seed "$s")
  echo "pilot plan job $id; log $D/logs/c8d2-s5e-pilotplan_$id.out; campaign $RUNP; cost model $CM";;
*) echo "unknown step $step" >&2; exit 64;;
esac
