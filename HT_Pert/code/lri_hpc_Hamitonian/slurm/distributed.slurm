#!/bin/bash
#SBATCH --job-name=lri-distributed
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=lri-mpi-%j.log
set -euo pipefail
# EXPERIMENTAL until tests/mpi_smoke.py passes on this cluster.
# Adapt site MPI modules / srun --mpi=... to the site's supported launcher.
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/lri-numba-${USER}"
mkdir -p "$NUMBA_CACHE_DIR"
srun --cpu-bind=cores python -m lri_hpc --mpi --task thermal --degree 7 \
  --cutoffs 64 --threads "$SLURM_CPUS_PER_TASK" --memory-limit-gib 48 \
  --output-dir results/thermal-mpi --resume
