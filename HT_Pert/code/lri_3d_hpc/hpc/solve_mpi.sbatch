#!/usr/bin/env bash
# Generic example. On Expanse and symmetry use cluster/submit.py (cluster/RUNBOOK.md).
#SBATCH --job-name=ht3d-mpi
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=ht3d-mpi-%j.log
# Load the site's matching Python, compiler and MPI modules before submission.
# Use the site's supported srun MPI configuration; do not mix MPI installations.
set -euo pipefail
: "${HT3D_ROOT:?Set HT3D_ROOT to the unpacked package}"
: "${HT3D_STORE:?Set HT3D_STORE to a shared verified vertex directory}"
: "${HT3D_OUTPUT:?Set HT3D_OUTPUT to a new result JSON path}"
: "${HT3D_CUTOFF:?Set HT3D_CUTOFF to an even bath cutoff}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OMP_PROC_BIND=close OMP_PLACES=cores
export OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0
export HT3D_NATIVE_CACHE="${HT3D_NATIVE_CACHE:-${SLURM_TMPDIR:-$HT3D_ROOT/work}/ht3d-native}"
srun --cpu-bind=cores python -m mpi4py "$HT3D_ROOT/code/ht3d_coefficients.py" solve \
  --mpi --store "$HT3D_STORE" --output "$HT3D_OUTPUT" --cutoff "$HT3D_CUTOFF" \
  --order "${HT3D_ORDER:-8}" --scheme "${HT3D_SCHEME:-consistent}" \
  --backend native --threads "$OMP_NUM_THREADS" --progress --resume
