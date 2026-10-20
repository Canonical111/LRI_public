#!/bin/bash
# Mac-side driver for the checkpoint-fix validation on Expanse (needs an open ControlMaster socket: log in to expanse
# interactively once). Exports HEAD, checks the export against git archive, uploads 601b102's production.py, then
# submits build -> (val1, mscale) with afterok dependencies, and the J-GEN-1 rerun (CK-K02) beside them. All four are
# shared-partition jobs (no compute node), named c8d2-*, with --mem and -t. Expected cost: about 15-25 SU.
# Usage (in the checkout): bash benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/submit_ckpt_expanse.sh
#
# Adapted 2026-10-04 for the run on d98e3a1 (the version first committed with 9f2c7e1 checked the queue once, only for
# the account's running normal-QOS jobs and this session's shared jobs):
#  1. admit() applies the full H7E-R rule before EVERY sbatch: this session's c8d2-* normal-QOS jobs at most 11 running
#     and 27 submitted, the whole <ACCOUNT> account at most 32 running normal-QOS jobs, c8d2-* shared jobs at most 32 live
#     after this submission, c8d2-* compute nodes at most 4; a failed or unparsable squeue refuses (fail closed).
#  2. The export listing goes to a private mktemp directory (C8_LOCAL_TMP, else $TMPDIR), not /tmp.
#  3. J-GEN-1 (slurm/gen/expanse_regress.slurm of the export, as c8d2-ckfix-gen1) is submitted too; it builds the
#     generator into its own directory and does not need the build job.
#  4. Tighter wall limits on the command line (val1 1:30, mscale 2:00) and mscale at --mem=32G instead of 48G (Stage
#     3b's merge-scale job 54643361 peaked at 0.9 GB), so the worst case of the four jobs stays far below 100 SU.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../.."
H=$(git rev-parse HEAD); T=${H:0:12}; D=<SCRATCH>/temp_project/c8d2; X=$D/pkg/$T
LT=$(mktemp -d "${C8_LOCAL_TMP:-${TMPDIR:-/tmp}}/c8d2_ckfix.XXXXXX")
echo "commit under test $H; export $X; local listing in $LT"
ssh -T -o BatchMode=yes expanse true
admit() {  # admit <job>: H7E-R snapshot of the <ACCOUNT> queue; exit 65 when a cap would be exceeded, 69 when squeue fails
  local snap
  snap=$(ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'") || { echo "squeue failed; nothing submitted" >&2; exit 69; }
  printf '%s\n' "$snap" | awk -F'|' -v me=<USER> -v job="$1" -v when="$(date '+%Y-%m-%dT%H:%M:%S%z')" '
    NF == 0 || $0 == "" {next}
    NF < 7 {bad = 1; next}
    { live = ($2 ~ /^(PENDING|RUNNING|CONFIGURING|COMPLETING|SUSPENDED|REQUEUED|REQUEUE_HOLD|REQUEUE_FED|RESIZING|SIGNALING|STAGE_OUT|STOPPED)$/)
      run  = ($2 ~ /^(RUNNING|CONFIGURING|COMPLETING|RESIZING|SIGNALING|STAGE_OUT)$/)
      all[$4 " " $2]++ }
    $4 == "normal" && run {acc_run++}
    $6 == me && $7 ~ /^c8d2-/ && live {
      if ($4 == "normal") {my_sub++; if (run) my_run++}
      if ($3 ~ /(^|,)shared(,|$)/) my_sh++
      if ($3 ~ /(^|,)compute(,|$)/) my_nodes += $5 }
    END {
      printf "%s H7E-R before %s: <ACCOUNT> running normal-QOS %d (<= 32); c8d2 normal-QOS running %d (<= 11), submitted %d (<= 27); c8d2 shared live %d (+1 <= 32); c8d2 compute nodes %d (<= 4)\n", when, job, acc_run, my_run, my_sub, my_sh, my_nodes
      for (k in all) printf "   account %s: %d\n", k, all[k]
      if (bad || acc_run > 32 || my_run > 11 || my_sub > 27 || my_sh + 1 > 32 || my_nodes > 4) {print "admission refused" > "/dev/stderr"; exit 65} }'
}
ssh -T expanse "test ! -e $X" || { echo "$X exists; remove it or reuse it by hand"; exit 64; }
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch"
git archive --format=tar "$H" | ssh -T expanse "mkdir -p $X && tar -x -C $X"
ssh -T expanse "python3 - $X" < "$S/tree_manifest.py" > "$LT/c8d2_tree_$T.txt"
python3 "$S/export_check.py" "$H" "$LT/c8d2_tree_$T.txt" expanse "$X" "benchmarks/expanse_2026-10-c8/setup/export_check_$T.json"
git show 601b102:tools/production.py | ssh -T expanse "cat > $D/ckpt_production_601b102.py"
L8=$D/pkg/7aac898add43/inputs/packs
P=$X/benchmarks/expanse_2026-10-c8/ckpt_fix/scripts
admit build
b=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_L8_PACKS=$L8 sbatch --parsable --export=ALL $P/expanse_ckpt_build.slurm")
admit val1
v=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL -t 01:30:00 --dependency=afterok:$b $P/expanse_ckpt_val1.slurm")
admit mscale
m=$(ssh -T expanse "cd $D && C8_PACKAGE=$X C8_OLD_PRODUCTION=$D/ckpt_production_601b102.py sbatch --parsable --export=ALL --mem=32G -t 02:00:00 --dependency=afterok:$b $P/expanse_ckpt_mscale.slurm")
admit gen1
g=$(ssh -T expanse "cd $D && C8_PACKAGE=$X sbatch --parsable --export=ALL -J c8d2-ckfix-gen1 $X/slurm/gen/expanse_regress.slurm")
echo "build $b, val1 $v, mscale $m, gen1 $g; logs $D/logs/c8d2-ckfix-{build,val1,mscale,gen1}_<id>.out; evidence $D/evidence/$T/"
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %q %r'"
