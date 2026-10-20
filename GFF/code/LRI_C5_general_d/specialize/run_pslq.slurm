#!/bin/bash
#SBATCH -J c5pslqL
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -o results/run_pslq_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/specialize/spec
~/c5d2/venv/bin/python pslq_L.py 110 > results/pslq_L_dps110_v2.log 2>&1
