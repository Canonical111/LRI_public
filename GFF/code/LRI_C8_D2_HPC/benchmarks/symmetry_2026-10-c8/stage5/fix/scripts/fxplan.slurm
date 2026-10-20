#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Plan job of the post-merge re-validation on symmetry (never on the login node): `production.py plan RUN ARGS`, then
# `ledger.py register RUN --role plan` (R10, as slurm/plan.sh does), then, with SEEDADD=1, `seeds.py add RUN` into
# symmetry's $C8_SEEDS (two-log rule: the Mac driver then merges it into Expanse's log and the package mirror). The
# restart twin (J-DRL-1) reuses the smoke's seed by design and runs with SEEDADD=0 (that seed is logged since J-SMK-1).
# Usage: C8_PACKAGE=... C8_RUN=... ARGS="..." SEEDADD=0|1 sbatch --export=ALL -J c8d2-fxplan-<name> fxplan.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${ARGS:?}" "${SEEDADD:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; run $C8_RUN; seeds log $C8_SEEDS"
echo "ARGS: $ARGS"
t0=$(date +%s)
python3 -B $C8_PACKAGE/tools/production.py plan $C8_RUN $ARGS
python3 -B $C8_PACKAGE/tools/ledger.py register $C8_RUN --role plan
if [ "$SEEDADD" = 1 ]; then python3 -B $C8_PACKAGE/tools/seeds.py add $C8_RUN; fi
echo "finished $(date -Is) after $(( $(date +%s) - t0 )) s"
