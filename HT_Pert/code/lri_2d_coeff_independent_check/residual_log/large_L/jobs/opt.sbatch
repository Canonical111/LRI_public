#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L/logs/%x_%j.out
# lib_opt runs (regression, timing, production).  usage: NT=<threads> sbatch -p <part> --job-name=indep2d-ll-<x> --mem=.. --time=.. opt.sbatch "<args in lib_opt/>"
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L
cd $W/lib_opt
export RS_EXACT_DIR=/mnt/beegfs/zzheng1/indep2d/residual_log/code2/rs_exact_copy
export NUMBA_CACHE_DIR=$W/numba_cache_opt
NT=${NT:-${SLURM_CPUS_ON_NODE:-1}}; export OMP_NUM_THREADS=$NT NUMBA_NUM_THREADS=$NT OPENBLAS_NUM_THREADS=$NT MKL_NUM_THREADS=$NT ENGINE_THREADS=1
echo "threads per process: $NT"
echo "host $(hostname) start $(date) cpus=${SLURM_CPUS_ON_NODE:-?} job=${SLURM_JOB_ID:-?}"
echo "args: $1"
sha1sum *.py | sed 's/^/# /'
/usr/bin/time -v ~/indep2d_c4/venv/bin/python $1 2>&1 | grep --line-buffered -v "OMP: Info"
echo "end $(date)"
