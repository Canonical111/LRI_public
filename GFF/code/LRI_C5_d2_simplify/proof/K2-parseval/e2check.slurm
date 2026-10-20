#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 02:00:00
#SBATCH -J k2p-e2check
#SBATCH -o <SCRATCH>/c5d2_proof/K2-parseval/%x_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5d2_proof/K2-parseval
echo "host $(hostname)  start $(date)"
grep Cpus_allowed_list /proc/self/status
~/c5d2/venv/bin/python -u e2check.py 8
echo "end $(date)"
