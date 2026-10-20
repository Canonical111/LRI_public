#!/bin/bash
#SBATCH --job-name=indep2d-cauchy-L6
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=12:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/cauchy/logs/campaign_L6_%j.log
lscpu | grep -E "Model name"
bash /mnt/beegfs/zzheng1/indep2d/cauchy/code/jobs/campaign.sh "6" "raw consistent literal" "base rhoK prec path cap21 cap23 cap17 cap18"
