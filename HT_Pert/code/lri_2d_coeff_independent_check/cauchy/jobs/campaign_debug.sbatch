#!/bin/bash
#SBATCH --job-name=indep2d-cauchy-L024
#SBATCH --partition=amddebugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/cauchy/logs/campaign_L024_%j.log
lscpu | grep -E "Model name"
bash /mnt/beegfs/zzheng1/indep2d/cauchy/code/jobs/campaign.sh "0 2 4" "raw consistent literal" "base rhoK prec path cap21 cap23 cap17 cap18"
