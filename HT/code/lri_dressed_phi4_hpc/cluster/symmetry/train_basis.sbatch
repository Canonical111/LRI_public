#!/bin/bash
#SBATCH -p amdq
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@600
#SBATCH --requeue
#SBATCH --job-name=lri-basis-train
# Supply the job array and a log path explicitly to sbatch, after creating its directory.
# Required exports: LRI_CODE_DIR, LRI_BASIS_MANIFEST, LRI_RECEIPT.
# Resource requests are starting allocations, not a measured performance guarantee.
set -euo pipefail
source "${LRI_CODE_DIR:?}/cluster/symmetry/env.sh"
cd "$LRI_CODE"
exec python scripts/run_basis_training.py --manifest "${LRI_BASIS_MANIFEST:?}" \
     --index "${SLURM_ARRAY_TASK_ID:?}" --receipt "${LRI_RECEIPT:?}"
