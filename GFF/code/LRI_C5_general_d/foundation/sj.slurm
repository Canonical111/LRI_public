#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH -t 02:00:00
#SBATCH -J fd_sjets
#SBATCH -o <SCRATCH>/c5_gend/foundation/fd_sjets_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/foundation
export SLURM_CPUS_PER_TASK=$(lscpu -p=CORE | grep -v '^#' | sort -u | wc -l)
echo "host $(hostname) workers $SLURM_CPUS_PER_TASK start $(date)"
~/c5d2/venv/bin/python sample_jets.py sample_jets.json 30 1,1.5,2,2.5,3
echo "end $(date)"
