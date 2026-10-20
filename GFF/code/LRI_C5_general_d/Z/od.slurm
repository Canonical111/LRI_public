#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive --mem=200G
#SBATCH -t 02:00:00
#SBATCH -J z_offdiag
#SBATCH -o <SCRATCH>/c5_gend/Z/od_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/Z
export SLURM_CPUS_PER_TASK=$(lscpu -p=CORE | grep -v '^#' | sort -u | wc -l)
echo "host $(hostname) start $(date)"
~/c5d2/venv/bin/python offdiag_check.py offdiag60.json 60
echo "end $(date)"
