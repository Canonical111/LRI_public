#!/bin/bash
#SBATCH --job-name=lri-array
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --array=0-12%4
#SBATCH --output=lri-%A_%a.log
set -euo pipefail
# Activate your cluster environment before submitting. Run from the project root.
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/lri-numba-${USER}"
mkdir -p "$NUMBA_CACHE_DIR"
CUTOFF=$((40+2*SLURM_ARRAY_TASK_ID))
srun --cpu-bind=cores python -m lri_hpc --task thermal --degree 7 \
  --cutoffs "$CUTOFF" --threads "$SLURM_CPUS_PER_TASK" \
  --memory-limit-gib 48 --output-dir results/thermal --resume
