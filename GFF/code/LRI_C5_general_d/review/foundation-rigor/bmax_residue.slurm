#!/bin/bash
#SBATCH -J fr_bmax
#SBATCH -p sharedq
#SBATCH -c 2
#SBATCH --mem=4000M
#SBATCH -t 04:00:00
#SBATCH -o results/bmax_residue_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/review/foundation-rigor
python3 bmax_residue.py
