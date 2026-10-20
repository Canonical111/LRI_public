#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L/logs/%x_%j.out
# raw C_5 at larger L with the unmodified copy lib/prod5.py (README Sec. 9.8 machinery).
# usage: NT=<threads/worker> ET=<engine threads> sbatch -p amdq --job-name=indep2d-ll-p300<x> --mem=240G --time=..:..:.. prod5.sbatch "<args>"
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L
cd $W/lib
export RS_EXACT_DIR=/mnt/beegfs/zzheng1/indep2d/residual_log/code2/rs_exact_copy
export NUMBA_CACHE_DIR=$W/numba_cache_p5
NT=${NT:-1}; export OMP_NUM_THREADS=$NT NUMBA_NUM_THREADS=$NT OPENBLAS_NUM_THREADS=$NT MKL_NUM_THREADS=$NT ENGINE_THREADS=${ET:-1}
echo "threads per worker: $NT, engine threads: ${ET:-1}"
echo "host $(hostname) start $(date) cpus=${SLURM_CPUS_ON_NODE:-?} job=${SLURM_JOB_ID:-?}"
echo "args: $1"
sha1sum *.py | sed 's/^/# /'
/usr/bin/time -v ~/indep2d_c4/venv/bin/python $1 2>&1 | grep --line-buffered -v "OMP: Info"
echo "end $(date)"
