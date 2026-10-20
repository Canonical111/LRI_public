#!/bin/bash
#SBATCH -p amdq -N 1 --exclusive --mem=200G
#SBATCH --exclude=cn112,cn083,cn084,cn085,cn086,cn087,cn088,cn089,cn090,cn091,cn092,cn095,cn096,cn097,cn105,cn106,cn107
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check, Codex follow-up (2026-10-08): the double-lift targeted nested-N native calls (tc_nested.py with
# tc_dl_graphs.txt: the 16 double-lift power L8 graphs with the largest production variance shares, 32 scrambles,
# prefixes 2^12..2^17, the 3 largest to 2^19) on one whole AMD node (64 threads), the production's gated dd+mp256
# executable a46f3060 of export ba68f401e46e. TC_ONLY is a "+"-separated list of <campaign>_<sector>.
# Requeue-safe: finished calls are skipped. The setup (seed registration, nets) is job c8d2-tc2setup.
# Usage: sbatch -J c8d2-tc2dl-<x> -t HH:MM:SS --export=ALL,TC_SEED=<seed>,TC_RUN=<dir>,TC_ONLY=<list> tc_dl.slurm
set -euo pipefail
TC_ONLY="${TC_ONLY//+/,}"
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck2-ba68f401e46e
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); cpu $(grep -m1 'model name' /proc/cpuinfo); seed $TC_SEED; run $TC_RUN; only $TC_ONLY"
python3 -B "$WK/tc_nested.py" --pkg "$PKG" --rundir "$TC_RUN" --graphs "$WK/tc_dl_graphs.txt" --seed "$TC_SEED" --reps 32 --threads 64 --only "$TC_ONLY"
echo "done at $(date -Is)"
