#!/bin/bash
#SBATCH -J fr_bmaxc
#SBATCH -p sharedq
#SBATCH -c 2
#SBATCH --mem=4000M
#SBATCH -t 04:00:00
#SBATCH -o results/bmax_compare_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/review/foundation-rigor
python3 bmax_compare.py 2.5 4 &
python3 bmax_compare.py 2.75 3 &
wait
