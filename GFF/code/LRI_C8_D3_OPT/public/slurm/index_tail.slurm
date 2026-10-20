#!/usr/bin/env bash
# Optional: a smaller lane index over an EXISTING campaign, to finish a few deferred jobs on fewer nodes (prod1: job
# 54838167 built a 16-lane index over runs/prod1 with the same bundling; lanes.slurm on 1 node then ran the 5 jobs in
# 11 min). Receipted jobs are skipped; no sample, sum or seed changes.
#SBATCH --job-name=c8opt-index
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output=c8opt-index-%j.out
set -euo pipefail
source "${C8_ENV:?set C8_ENV to your filled env.sh}"; [[ "${C8_ENV_OK:-}" == 1 ]] || exit 65
NAME="<NAME>"
for v in "$NAME" ${SEED:+"$SEED"} ${LANES:+"$LANES"}; do [[ "$v" != *"<"* ]] || { echo "fill the placeholders first" >&2; exit 64; }; done
cd "$C8_PACKAGE"
export OPENBLAS_NUM_THREADS=1
"$C8_PYTHON" -B tools/hpc_dispatch.py index "$C8_ROOT/runs/$NAME" "$C8_ROOT/dispatch/${NAME}_tail" --bundle-jobs 4 \
    --statistics results/pilot_20261008/graph_statistics.json --target-core-seconds 1800 --lanes 16
