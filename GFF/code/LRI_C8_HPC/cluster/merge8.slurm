#!/bin/bash
#SBATCH --job-name=c8-merge
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out
# Merge and verify every campaign of one planned C8 batch (production8.py merge). Required: C8_ENV_SETUP, C8_ROOT, C8_PRODUCTION.
set -eo pipefail
source "${C8_ENV_SETUP:?}"
set -u
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
"${C8_PYTHON:-python3}" "${C8_ROOT:?}/tools/production8.py" merge "${C8_PRODUCTION:?}" ${scratch_args[@]+"${scratch_args[@]}"}
