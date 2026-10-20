#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=04:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# zero-mode-tagged phi channel c1tag(L; nu_in, nu_out) (brute_desc_tag.py --phinu); RUNS="L:a:nuin_nuout_conv ..."
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code2
export RS_EXACT_DIR=$W/code2/rs_exact_copy
echo "host $(hostname) start $(date)"
for run in $RUNS; do
  IFS=: read L A NU <<< "$run"
  tag="L${L}_a${A}_phi${NU}"
  ( /usr/bin/time -v ~/indep2d_c4/venv/bin/python brute_desc_tag_v2.py --L $L --a $A --nu none --phinu ${NU//_/,} --out $W/results/tag_${tag}.json > $W/logs/tag_${tag}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
grep -h "phi-tag" $W/logs/tag_*phi*_${SLURM_JOB_ID}.log
echo "end $(date)"
