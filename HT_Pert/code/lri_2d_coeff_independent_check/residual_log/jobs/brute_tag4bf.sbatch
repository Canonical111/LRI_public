#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=10:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# Phase 5: budget-free tagged chi_aa through eps^4 (scheme Wcs windows), brute_desc_tag4.py --nu 0,0; RUNS="L:a ..."
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code2
export RS_EXACT_DIR=$W/code2/rs_exact_copy
echo "host $(hostname) start $(date)"
sha1sum brute_desc_tag.py brute_desc_tag4.py brute_legw.py brute_W5.py
for run in $RUNS; do
  IFS=: read L A <<< "$run"
  tag="L${L}_a${A}"
  ( /usr/bin/time -v ~/indep2d_c4/venv/bin/python brute_desc_tag4.py --L $L --a $A --nu 0,0 --out $W/results/tag4bf_${tag}.json > $W/logs/tag4bf_${tag}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
grep -h "R_4" $W/logs/tag4bf_*_${SLURM_JOB_ID}.log
echo "end $(date)"
