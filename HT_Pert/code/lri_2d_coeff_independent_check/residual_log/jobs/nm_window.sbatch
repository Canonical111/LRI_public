#!/bin/bash
#SBATCH --job-name=indep2d-rl-nm
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# usage: sbatch -p amddebugq jobs/nm_window.sbatch LMAX
set -euo pipefail
LMAX=${1:-2000}
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code
export OMP_NUM_THREADS=${SLURM_CPUS_ON_NODE:-32} OPENBLAS_NUM_THREADS=${SLURM_CPUS_ON_NODE:-32} MKL_NUM_THREADS=${SLURM_CPUS_ON_NODE:-32}
export NUMBA_CACHE_DIR=$W/code/numba_cache
echo "host $(hostname) start $(date) LMAX=$LMAX cpus=${SLURM_CPUS_ON_NODE:-?}"
sha1sum c4lib.py nm_window.py offdiag_window.py
/usr/bin/time -v ~/indep2d_c4/venv/bin/python nm_window.py --Lmax $LMAX --out $W/results/nm_L${LMAX}.npz 2>&1
echo "end $(date)"
