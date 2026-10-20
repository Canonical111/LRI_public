#!/bin/bash
#SBATCH -J tm-conv
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -o conv_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/review/topmode-numeric
~/c5d2/venv/bin/python conv_test.py
