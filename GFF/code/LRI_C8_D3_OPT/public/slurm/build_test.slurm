#!/usr/bin/env bash
# Build the native workers IN PLACE (bin/; a campaign pins bin/c8d3_optimized by path and SHA-256) and run the
# package's tests in a copy (make -f public.mk test). Production: 32 cores / 64 GB of an AMD EPYC 7742 node, about
# 2-3 min in total. Build on the CPU model the lanes will run on: one CPU model per campaign.
#SBATCH --job-name=c8opt-build
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=32 --mem=64G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=c8opt-build-%j.out
set -euo pipefail
source "${C8_ENV:?set C8_ENV to your filled env.sh}"; [[ "${C8_ENV_OK:-}" == 1 ]] || exit 65
cd "$C8_PACKAGE"
lscpu | grep -E 'Model name' || true
make -j"$SLURM_CPUS_PER_TASK" PYTHON="$C8_PYTHON" gmp optimized baseline points reference bin/test_positive_quad
bin/c8d3_optimized --describe
sha256sum bin/c8d3_optimized
make -f public.mk PYTHON="$C8_PYTHON" test
