#!/bin/bash
#SBATCH -J l2fourier60
#SBATCH -p sharedq
#SBATCH -c 2
#SBATCH --mem=4000M
#SBATCH -t 01:30:00
#SBATCH -o l2fourier60-%j.out
# 60-digit run of the L2-fourier reduction checks (elliptic forms of A,B,A',B'; (E1),(E2); strip contours;
# structural collapse vs the 70-digit single sums).
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5d2_proof/L2-fourier
export CONFIRM_JSON=<SCRATCH>/c5d2_proof/L2-fourier/confirm_dps70.json
date
~/c5d2/venv/bin/python check_reduction.py 60 > check_reduction_dps60.log 2>&1
~/c5d2/venv/bin/python check_strip.py 60 > check_strip_dps60.log 2>&1
date
