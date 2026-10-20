#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check part B (2026-10-07): register the fresh base seed in symmetry's seed log (tools/seeds.py check, then add
# with a label), then write the nested run's setup (graph members checked by sha256, the two campaigns' scrambled nets
# per sector) with tc_nested.py --setup-only. Usage: sbatch -J c8d2-tcnsetup --export=ALL,TC_SEED=<seed>,TC_RUN=<dir> tc_nested_setup.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); seed $TC_SEED; run $TC_RUN"
cd "$PKG"
python3 -B tools/seeds.py check "$TC_SEED" --log "$C8_SEEDS" && echo "seed free in $C8_SEEDS"
python3 -B tools/seeds.py add --seed "$TC_SEED" --label "$TC_RUN (C8(2) tail check part B: fresh nested-N runs of selected L8 graphs, test only, never in an estimate)" --log "$C8_SEEDS"
python3 -B tools/seeds.py list --log "$C8_SEEDS" | tail -3
sha256sum "$C8_SEEDS"
sha256sum "$WK/tc_nested.py" "$WK/tc_nested_graphs.txt" "$WK/tc_nested.slurm" "$WK/tc_nested_setup.slurm"
python3 -B "$WK/tc_nested.py" --pkg "$PKG" --rundir "$TC_RUN" --graphs "$WK/tc_nested_graphs.txt" --seed "$TC_SEED" --reps "${TC_REPS:-32}" --setup-only
ls -la "$TC_RUN"
