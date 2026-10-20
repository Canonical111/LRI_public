#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=170G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# budget-free external-line descendant diagnostic; RUNS="L:a:bf ..." (bf = 0/1), one process each
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code2
export RS_EXACT_DIR=$W/code2/rs_exact_copy
echo "host $(hostname) start $(date)"
for run in $RUNS; do
  IFS=: read L A BF <<< "$run"
  opt=""; [ "$BF" = "1" ] && opt="--bf"
  ( ~/indep2d_c4/venv/bin/python brute_desc_bf.py --L $L --a $A $opt --out $W/results/bf_L${L}_a${A}_bf${BF}.json > $W/logs/bf_L${L}_a${A}_bf${BF}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
grep -h "R_2" $W/logs/bf_*_${SLURM_JOB_ID}.log
echo "end $(date)"
