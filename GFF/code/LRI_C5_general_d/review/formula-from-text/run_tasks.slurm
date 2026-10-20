#!/bin/bash
#SBATCH -J fft-review
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -o <SCRATCH>/c5_gend/review/formula-from-text/results/slurm_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/review/formula-from-text
PY=~/c5d2/venv/bin/python
export OMP_NUM_THREADS=1
cat tasks.txt | xargs -P 8 -L 1 sh -c 'exec '"$PY"' circle_driver.py "$0" "$1" "$2" "$3" "$4" "$5" "$6" "$7" > results/log_$0_$1_$7.txt 2>&1'
echo ALLDONE
