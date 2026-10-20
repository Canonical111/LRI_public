#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH --mem=200G
#SBATCH -t 04:00:00
#SBATCH -J L_ref
#SBATCH -o <SCRATCH>/c5_gend/L/L_ref_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/L
export SLURM_CPUS_PER_TASK=$(lscpu -p=CORE | grep -v '^#' | sort -u | wc -l)
echo "host $(hostname) workers $SLURM_CPUS_PER_TASK start $(date) args: $@"
OPENBLAS_NUM_THREADS=1 ~/c5d2/venv/bin/python -u refcheck_r4.py "$@"
echo "end $(date)"
