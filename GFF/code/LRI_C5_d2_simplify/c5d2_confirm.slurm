#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH -t 06:00:00
#SBATCH -J c5d2-confirm
#SBATCH -o <SCRATCH>/c5d2/confirm-%j.out
# High-precision confirmation of L2 = -2 log2 P4(2) and K2 = 32 G^2 - 28 zeta(3) log2 (d=2), all single sums in parallel.
set -eo pipefail
source /etc/profile.d/modules.sh; module load python/3.11
cd $HOME/c5d2
echo "host $(hostname) $(date) cpus $(nproc) dps $DPS"
export OMP_NUM_THREADS=1
venv/bin/python -u parallel_eval.py $DPS
mkdir -p <SCRATCH>/c5d2 && cp confirm_dps$DPS.json <SCRATCH>/c5d2/
echo "done $(date)"
