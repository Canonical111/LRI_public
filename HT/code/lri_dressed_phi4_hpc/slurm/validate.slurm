#!/bin/bash
#SBATCH --job-name=lri-dressed-validation
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=logs/validation-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
# --baseline: a frozen tree of release e637dfd (its numerical source fingerprint is pinned and checked).
python scripts/validate_release.py --threads "$SLURM_CPUS_PER_TASK" --output validation/cluster-receipt.json \
    --baseline "${LRI_BASELINE:?set LRI_BASELINE to a frozen e637dfd source tree}"
