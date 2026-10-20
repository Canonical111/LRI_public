#!/bin/bash
#SBATCH --job-name=kRpart
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=25
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=%x-%j.out
# args: d r N K M dps tag
source ~/c7d3_prod/env.sh
cd ~/kgen_R_part
python3 kjet_prod.py $1 $2 $3 $4 $5 $6 prod_${7}_d$1.json
