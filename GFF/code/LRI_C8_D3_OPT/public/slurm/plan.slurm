#!/usr/bin/env bash
# Freeze a new campaign and its lane index (production plan job 54822480: 4 cores, 16 GB, 1 h 41 min, most of it
# hashing the 9 GB of graph payloads on Lustre). Needs `make -f public.mk fetch-data` (payloads) and the build above.
#   <FRESH_SEED>  a new integer in [0, 2^63): never 1546835505427890396 (prod1), 7736323638330945148 (the delivered
#                 pilot) or 6129871430538291 (the README example); a reused seed repeats the same random streams.
#   <LANES>       nodes x 16 for 128-core nodes (prod1: 96 = 6 x 16).
#SBATCH --job-name=c8opt-plan
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=c8opt-plan-%j.out
set -euo pipefail
source "${C8_ENV:?set C8_ENV to your filled env.sh}"; [[ "${C8_ENV_OK:-}" == 1 ]] || exit 65
NAME="<NAME>"
SEED="<FRESH_SEED>"
LANES="<LANES>"
for v in "$NAME" ${SEED:+"$SEED"} ${LANES:+"$LANES"}; do [[ "$v" != *"<"* ]] || { echo "fill the placeholders first" >&2; exit 64; }; done
cd "$C8_PACKAGE"
export OPENBLAS_NUM_THREADS=1
RUN="$C8_ROOT/runs/$NAME"; DISPATCH="$C8_ROOT/dispatch/$NAME"
# The production options (tools/campaign.py plan), with the frozen allocation of prod1:
"$C8_PYTHON" -B tools/campaign.py plan "$RUN" --purpose production --points 4096 --replicates 16 --threads 8 \
    --graph-block 32 --chunk-points 262144 --allocation ../../results/C8_3_check/allocations/prod1_2000.json \
    --seed "$SEED" --executable "$C8_PACKAGE/bin/c8d3_optimized"
# The lane index (tools/hpc_dispatch.py index). prod1 used the delivered pilot's graph statistics (sha256 41e3a0d7...,
# unpacked by fetch-data); they only shape the bundles and the deadline estimates, never the science.
"$C8_PYTHON" -B tools/hpc_dispatch.py index "$RUN" "$DISPATCH" --bundle-jobs 4 \
    --statistics results/pilot_20261008/graph_statistics.json --target-core-seconds 1800 --lanes "$LANES"
