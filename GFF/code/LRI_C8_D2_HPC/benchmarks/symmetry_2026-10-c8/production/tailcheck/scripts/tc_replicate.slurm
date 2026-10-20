#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=8G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check (2026-10-07): replicate-level shape of the final graph sum (tc_replicate_c8.py). Reads the production
# batch; writes only this job's evidence folder. Usage: sbatch -J c8d2-tcrep --export=ALL tc_replicate.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tcrep.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"
sha256sum "$WK/tc_replicate_c8.py" "$WK/tc_replicate.slurm" "$WK/prod_tails.csv.gz" "$RUN/manifest.json" "$RUN/C8_result.json" | tee "$E/inputs.sha256"
cd "$PKG" || exit 64
t=$(date +%s); /usr/bin/time -v -o "$E/time.txt" python3 -B "$WK/tc_replicate_c8.py" --package "$PKG" --run "$RUN" --classes "$WK/prod_tails.csv.gz" --out "$E/replicate_c8.json" > "$E/stdout.txt" 2>&1
echo "exit $? after $(( $(date +%s) - t )) s" | tee "$E/exit.txt"; cat "$E/stdout.txt"
