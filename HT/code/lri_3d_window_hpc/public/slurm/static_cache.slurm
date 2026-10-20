#!/bin/bash
# Build the N = 20 static cache (bath graph, spin-0 SO(3) projector, spin-0 vertices at one Ds) for a rerun.
# Measured: 9.0 h, 92 GiB peak on one large-memory node (Expanse job 54748336, 4 cores). The projector is
# single-threaded LAPACK; more cores do not help. Use --spins 0 1 only if J = 1 diagnostics are wanted (more than
# 224 GB for the spin-1 vertices; see REPRODUCE.md).
#SBATCH -A <ACCOUNT>
#SBATCH -p <LARGE_MEMORY_PARTITION>
#SBATCH -N 1 -n 1 -c 4
#SBATCH --mem=192G
#SBATCH -t 16:00:00
#SBATCH -J ht3d-cache-L20
#SBATCH -o ht3d-cache-L20_%j.out
set -euo pipefail
cd <HT>/code/lri_3d_window_hpc
source <VENV>/bin/activate
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -B scripts/probe_large_setup.py --L 20 --x 0.6 --spins 0 --execute --stop-after vertices \
  --max-bath-states 200000000 --memory-limit-gib 180 --threads ${SLURM_CPUS_PER_TASK} \
  --cache-dir <SCRATCH>/ht3d/static_cache --output <SCRATCH>/ht3d/static_cache_setup.json
