#!/bin/bash
#SBATCH --job-name=indep2d-rl-desc3
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=170G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# exact Fraction descendant residuals for several L in parallel, given schemes (DESC_LS, DESC_SCHEMES, DESC_TAG)
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code2
export RS_EXACT_DIR=$W/code2/rs_exact_copy
echo "host $(hostname) start $(date)"
sha1sum brute_desc.py brute_W5.py rs_exact_copy/ref_fraction.py
for L in ${DESC_LS:-2 4 6 8 10 12}; do
  ( /usr/bin/time -v ~/indep2d_c4/venv/bin/python brute_desc.py --L $L --schemes $DESC_SCHEMES --out $W/results/brute_desc_L${L}_${DESC_TAG}.json > $W/logs/brute_desc_L${L}_${DESC_TAG}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
grep -h "^# \|Elapsed" $W/logs/brute_desc_L*_${DESC_TAG}_${SLURM_JOB_ID}.log
echo "end $(date)"
