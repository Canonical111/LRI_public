#!/bin/bash
#SBATCH -p amdq -N 1 --exclusive --mem=200G
#SBATCH --exclude=cn112,cn083,cn084,cn085,cn086,cn087,cn088,cn089,cn090,cn091,cn092,cn095,cn096,cn097,cn105,cn106,cn107
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check part B (2026-10-07): the fresh nested-N native calls of tc_nested.py on one whole AMD node (64 threads),
# restricted to TC_ONLY (a "+"-separated list of <campaign>_<sector>; sbatch --export splits on commas, so jobs 571362/571363,
# submitted with "a_free,a_power", ran a_free and b_free only). Requeue-safe: finished calls are skipped.
# Usage: sbatch -J c8d2-tcnest-<x> -t HH:MM:SS --export=ALL,TC_SEED=<seed>,TC_RUN=<dir>,TC_ONLY=<list> tc_nested.slurm
set -euo pipefail
TC_ONLY="${TC_ONLY//+/,}"
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); cpu $(grep -m1 'model name' /proc/cpuinfo); seed $TC_SEED; run $TC_RUN; only $TC_ONLY"
python3 -B "$WK/tc_nested.py" --pkg "$PKG" --rundir "$TC_RUN" --graphs "$WK/tc_nested_graphs.txt" --seed "$TC_SEED" --reps "${TC_REPS:-32}" --threads 64 --only "$TC_ONLY"
echo "done at $(date -Is)"
