#!/bin/bash
#SBATCH -J fft-pole
#SBATCH -p sharedq
#SBATCH -c 4
#SBATCH --mem=12000M
#SBATCH -t 04:00:00
#SBATCH -o <SCRATCH>/c5_gend/review/formula-from-text/results/slurm_pole_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/review/formula-from-text
PY=~/c5d2/venv/bin/python
for d in 1.5 2.5 1.25 2.75; do
  $PY pole_check.py $d 30000 12 > results/log_pole_$d.txt 2>&1 &
done
wait
echo ALLDONE
