#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive --mem=200G
#SBATCH -t 04:00:00
#SBATCH -J zj_jets
#SBATCH -o <SCRATCH>/c5_gend/Z/zj_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/Z
export SLURM_CPUS_PER_TASK=$(lscpu -p=CORE | grep -v '^#' | sort -u | wc -l)
echo "host $(hostname) workers $SLURM_CPUS_PER_TASK start $(date)"
~/c5d2/venv/bin/python z_jets.py ${OUT:-zj60.json} ${DPS:-60} ${DS:-1,1.5,2,2.5,3,0.8,1.25,2.75} ${DEG:-2}
echo "end $(date)"
