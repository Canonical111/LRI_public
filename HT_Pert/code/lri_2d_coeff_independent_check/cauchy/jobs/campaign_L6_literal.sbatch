#!/bin/bash
#SBATCH --job-name=indep2d-cauchy-L6-literal
#SBATCH --partition=amddebugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/cauchy/logs/campaign_L6_literal_%j.log
lscpu | grep -E "Model name"
bash /mnt/beegfs/zzheng1/indep2d/cauchy/code/jobs/campaign.sh "6" "literal" "base rhoK prec path cap21 cap23 cap17 cap18"
