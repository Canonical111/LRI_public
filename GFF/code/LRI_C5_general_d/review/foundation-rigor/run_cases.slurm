#!/bin/bash
#SBATCH -J fr_cases
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -o results/run_cases_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <SCRATCH>/c5_gend/review/foundation-rigor
python3 run_cases.py 8
