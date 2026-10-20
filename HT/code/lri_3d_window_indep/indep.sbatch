#!/bin/bash
#SBATCH -A <ACCOUNT>
#SBATCH -p shared
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 4
#SBATCH --mem=24G
#SBATCH -t 12:00:00
#SBATCH -J ht3d-indep
#SBATCH -o <SCRATCH>/temp_project/ht3d/indep/logs/%x_%A_%a.out
set -euo pipefail
source ~/ht3d/code/33ef4f35ff4b/cluster/expanse/env.sh >/dev/null 2>&1 || true
export OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 OMP_NUM_THREADS=4
cd <SCRATCH>/temp_project/ht3d/indep
read L MODE X < <(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" tasks.txt)
echo "task $SLURM_ARRAY_TASK_ID L=$L mode=$MODE x=$X host=$(hostname) python=$(which python) start $(date -Is)"
python -c "import numpy,scipy;print(numpy.__version__,scipy.__version__)"
python -u run_compare.py --L $L --x $X --mode $MODE --K 16 --K2 24 --out results/cmp_L${L}_${MODE}_x${X}.json
echo "end $(date -Is)"
