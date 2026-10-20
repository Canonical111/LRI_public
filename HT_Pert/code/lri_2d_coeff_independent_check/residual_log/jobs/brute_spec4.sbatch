#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=06:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# Phase 5: spectator response of the budget-free chi line at every spectator charge 2..L (brute_desc_chi4.py --spec); RUNS="L:a ..."
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code2
export RS_EXACT_DIR=$W/code2/rs_exact_copy
echo "host $(hostname) start $(date)"
sha1sum brute_desc_tag.py brute_desc_chi4.py brute_legw.py brute_W5.py
for run in $RUNS; do
  IFS=: read L A <<< "$run"
  tag="L${L}_a${A}"
  SPECN=$(seq -s, 2 2 $L)
  ( /usr/bin/time -v ~/indep2d_c4/venv/bin/python brute_desc_chi4.py --L $L --a $A --nu 0,0 --spec --specN $SPECN --out $W/results/spec4_${tag}.json > $W/logs/spec4_${tag}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
grep -h "spectator\|R_4" $W/logs/spec4_*_${SLURM_JOB_ID}.log
echo "end $(date)"
