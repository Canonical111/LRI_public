#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -J lgself
#SBATCH -o <SCRATCH>/c5_gend/lemmaG/logs/%x_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/lemmaG/code
~/c5d2/venv/bin/python selftest.py 48 44 14 28 26 &
~/c5d2/venv/bin/python selftest.py 54 50 18 36 32 &
wait
