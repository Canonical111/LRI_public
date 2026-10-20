#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SMK-1 (PLAN "L8 smoke (exact job specs; Stage 5)"): plan the smoke and its twin (same arguments and seed) inside one
# sharedq job, register the plan job in both campaigns' ledgers with role plan (R10), then register the seed. The
# plan's command, word for word, with ARGS from the environment (the plan's ARGS line; the cost model is the J-SWEEP-2
# model with J-SWEEP-3's Intel class factors, cost_models/gmp_symmetry_amd_c8.json in the export).
# Usage: C8_ENV_SETUP=... C8_PACKAGE=... C8_RUN=... C8_RUN_TWIN=... ARGS="..." sbatch --export=ALL -J c8d2-plan-smoke s5smk1.slurm
set -euo pipefail
source "$C8_ENV_SETUP"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${C8_RUN_TWIN:?}" "${ARGS:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; run $C8_RUN; twin $C8_RUN_TWIN"
echo "ARGS: $ARGS"
t0=$(date +%s)
python3 -B $C8_PACKAGE/tools/production.py plan $C8_RUN $ARGS
python3 -B $C8_PACKAGE/tools/ledger.py register $C8_RUN --role plan
python3 -B $C8_PACKAGE/tools/production.py plan $C8_RUN_TWIN $ARGS
python3 -B $C8_PACKAGE/tools/ledger.py register $C8_RUN_TWIN --role plan
python3 -B $C8_PACKAGE/tools/seeds.py add $C8_RUN
echo "finished $(date -Is) after $(( $(date +%s) - t0 )) s"
