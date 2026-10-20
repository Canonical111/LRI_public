#!/bin/bash
#SBATCH --job-name=indep2d-rl-brute
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# exact Fraction end-to-end checks of the complete window scheme, L = 6 and 8 (two background processes)
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/code
export RS_EXACT_DIR=$W/code/rs_exact_copy
echo "host $(hostname) start $(date)"
sha1sum brute_full.py brute_nm.py rs_exact_copy/ref_fraction.py
for L in ${BRUTE_LS:-6 8}; do
  ( /usr/bin/time -v ~/indep2d_c4/venv/bin/python brute_full.py --L $L --out $W/results/brute_full_L$L.json > $W/logs/brute_full_L${L}_${SLURM_JOB_ID}.log 2>&1 ) &
done
wait
tail -n 3 $W/logs/brute_full_L*_${SLURM_JOB_ID}.log
grep -h "Elapsed\|Maximum resident" $W/logs/brute_full_L*_${SLURM_JOB_ID}.log
echo "end $(date)"
