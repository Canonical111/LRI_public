#!/bin/bash
#SBATCH --job-name=lri-eh-validate
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/validate-%j.out
set -euo pipefail
: "${EH_ROOT:?Set EH_ROOT}"
cd "$EH_ROOT"
export PYTHONPATH="$EH_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=4
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-/tmp}/lri-eh-validation-${SLURM_JOB_ID}"
srun --ntasks=1 --cpu-bind=cores python scripts/validate_release.py \
    --threads 4 --output "validation/${SLURM_JOB_ID}.json"
