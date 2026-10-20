#!/bin/bash
#SBATCH -A <ACCOUNT>
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --mem=16G
#SBATCH -t 00:30:00
#SBATCH -J ht3d-indep-spin
#SBATCH -o <SCRATCH>/temp_project/ht3d/indep/logs/%x_%j.out
source ~/ht3d/code/33ef4f35ff4b/cluster/expanse/env.sh >/dev/null 2>&1 || true
export OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 OMP_NUM_THREADS=8
cd <SCRATCH>/temp_project/ht3d/indep
echo "start $(date -Is) $(hostname)"
python -u t_spin.py 8 0.6,0.518149,0.7
echo "end $(date -Is)"
