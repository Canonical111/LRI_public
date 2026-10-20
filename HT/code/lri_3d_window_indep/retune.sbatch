#!/bin/bash
#SBATCH -A <ACCOUNT>
#SBATCH -p debug
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --mem=16G
#SBATCH -t 00:30:00
#SBATCH -J ht3d-indep-retune
#SBATCH -o <SCRATCH>/temp_project/ht3d/indep/logs/%x_%j.out
source ~/ht3d/code/33ef4f35ff4b/cluster/expanse/env.sh >/dev/null 2>&1 || true
export OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 OMP_NUM_THREADS=4
cd <SCRATCH>/temp_project/ht3d/indep
echo "start $(date -Is) $(hostname)"
python -u run_compare.py --L 10 --x 0.55 --mode window --out results/cmp_L10_window_x0.55.json &
python -u run_compare.py --L 10 --x 0.518149 --mode window --out results/cmp_L10_window_x0.518149.json &
wait
echo "end $(date -Is)"
