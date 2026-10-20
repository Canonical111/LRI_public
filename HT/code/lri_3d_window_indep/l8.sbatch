#!/bin/bash
#SBATCH -A <ACCOUNT>
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --mem=16G
#SBATCH -t 00:30:00
#SBATCH -J ht3d-indep-L8
#SBATCH -o <SCRATCH>/temp_project/ht3d/indep/logs/%x_%j.out
source ~/ht3d/code/33ef4f35ff4b/cluster/expanse/env.sh >/dev/null 2>&1 || true
export OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 OMP_NUM_THREADS=8
cd <SCRATCH>/temp_project/ht3d/indep
echo "start $(date -Is) $(hostname)"
for i in 0 1 2 3 4 5 6; do read L MODE X < <(sed -n "$((i+1))p" tasks.txt); python -u run_compare.py --L $L --x $X --mode $MODE --K 16 --K2 24 --out results/cmp_L${L}_${MODE}_x${X}.json; done
echo "end $(date -Is)"
