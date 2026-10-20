#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=8G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check (2026-10-07): pilot-to-production tail growth of the L7/L8 graphs from the merged per-replicate tail
# tables (tc_merged_tails.py). Reads the pilot and production campaigns; writes only this job's evidence folder.
# Usage (login node): sbatch -J c8d2-tcmerged --export=ALL tc_merged.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
PILOT=/mnt/beegfs/zzheng1/c8-d2/pilot1-20261006-ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tcmerged.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"
sha256sum "$WK/tc_merged_tails.py" "$WK/tc_merged.slurm" "$WK/prod_tails.csv.gz" "$PILOT/manifest.json" "$RUN/manifest.json" | tee "$E/inputs.sha256"
t=$(date +%s); /usr/bin/time -v -o "$E/time.txt" python3 -B "$WK/tc_merged_tails.py" --pilot "$PILOT" --prod "$RUN" --classes "$WK/prod_tails.csv.gz" --out "$E/merged_tails.json" > "$E/stdout.txt" 2>&1
echo "exit $? after $(( $(date +%s) - t )) s" | tee "$E/exit.txt"; cat "$E/stdout.txt"
