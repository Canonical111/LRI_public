#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH -t 03:00:00
#SBATCH -J fd_valx
#SBATCH -o <SCRATCH>/c5_gend/foundation/fd_valx_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/foundation
export SLURM_CPUS_PER_TASK=$(lscpu -p=CORE | grep -v '^#' | sort -u | wc -l)
echo "host $(hostname) workers $SLURM_CPUS_PER_TASK start $(date)"
~/c5d2/venv/bin/python run_validation.py valx.json 50 extra
echo "end $(date)"
