#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -J lgconv
#SBATCH -o <SCRATCH>/c5_gend/lemmaG/logs/%x_%j.out
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/lemmaG/code
~/c5d2/venv/bin/python conv_h.py "$1" "$2" --np 8 $3
