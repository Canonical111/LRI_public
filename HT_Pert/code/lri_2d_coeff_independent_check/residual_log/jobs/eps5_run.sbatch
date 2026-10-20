#!/bin/bash
#SBATCH --job-name=indep2d-rl-e5
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# usage: sbatch -p amddebugq [--job-name=indep2d-rl-e5-xxx] eps5_run.sbatch "<python args run in eps5/>"
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code/eps5
export RS_EXACT_DIR=$W/code/rs_exact_copy
export NUMBA_CACHE_DIR=$W/code/eps5/numba_cache
echo "host $(hostname) start $(date) cpus=${SLURM_CPUS_ON_NODE:-?}"
echo "args: $1"
sha1sum *.py | sed 's/^/# /'
/usr/bin/time -v ~/indep2d_c4/venv/bin/python $1 2>&1 | grep --line-buffered -v "OMP: Info"
echo "end $(date)"
