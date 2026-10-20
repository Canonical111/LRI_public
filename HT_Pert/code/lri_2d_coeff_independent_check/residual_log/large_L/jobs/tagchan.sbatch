#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L/logs/%x_%j.out
# usage: sbatch -p amddebugq --job-name=indep2d-ll-<tag> --mem=200G --time=00:59:00 tagchan.sbatch "<python args run in large_L/>"
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log/large_L
cd $W
export NUMBA_CACHE_DIR=$W/numba_cache
NT=${NT:-${SLURM_CPUS_ON_NODE:-1}}; export OMP_NUM_THREADS=$NT NUMBA_NUM_THREADS=$NT OPENBLAS_NUM_THREADS=$NT MKL_NUM_THREADS=$NT ENGINE_THREADS=${ET:-1}
echo "threads: $NT, engine threads: ${ET:-1}"
echo "host $(hostname) start $(date) cpus=${SLURM_CPUS_ON_NODE:-?} job=${SLURM_JOB_ID:-?}"
echo "args: $1"
sha1sum *.py lib/*.py | sed 's/^/# /'
/usr/bin/time -v ~/indep2d_c4/venv/bin/python $1 2>&1 | grep --line-buffered -v "OMP: Info"
echo "end $(date)"
