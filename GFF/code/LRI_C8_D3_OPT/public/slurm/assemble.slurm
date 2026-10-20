#!/usr/bin/env bash
# Streaming assembly of a completed campaign into NEW files (prod1: job 54838171, 16 cores / 64 GB, 46 s):
# C8_result_<job>.json and graph_statistics_<job>.json. It refuses missing, duplicated or overlapping work.
#SBATCH --job-name=c8opt-assemble
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=c8opt-assemble-%j.out
set -euo pipefail
source "${C8_ENV:?set C8_ENV to your filled env.sh}"; [[ "${C8_ENV_OK:-}" == 1 ]] || exit 65
NAME="<NAME>"
for v in "$NAME" ${SEED:+"$SEED"} ${LANES:+"$LANES"}; do [[ "$v" != *"<"* ]] || { echo "fill the placeholders first" >&2; exit 64; }; done
cd "$C8_PACKAGE"
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
RUN="$C8_ROOT/runs/$NAME"
"$C8_PYTHON" -B tools/campaign.py status "$RUN"
"$C8_PYTHON" -B tools/assemble_streaming.py "$RUN" --bootstrap 4096 \
    --output "$RUN/C8_result_$SLURM_JOB_ID.json" --graph-statistics "$RUN/graph_statistics_$SLURM_JOB_ID.json"
