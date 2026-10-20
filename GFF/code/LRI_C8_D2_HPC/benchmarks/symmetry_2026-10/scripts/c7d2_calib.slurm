#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 64
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH -t 06:00:00
#SBATCH -J c7d2-calib-dec
#SBATCH -o <SCRATCH>/c7d2_fix/logs/%x_%j.out
# Drill 5: decimal-backend calibration (seconds per proxy unit per sector/L) on one AMD node, 64 threads.
set -eo pipefail; source $HOME/c7d2_prod/env.sh; set -u
W=<SCRATCH>/c7d2_fix; P=$W/final; RC=$W/calib_decimal
export OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
echo "host $(hostname) job $SLURM_JOB_ID $(date -Is) $(lscpu | grep 'Model name')"
n=$(python3 -c "import json;print(len(json.load(open('$RC/manifest.json'))['jobs']))")
for i in $(seq 0 $((n-1))); do s=$(date +%s); python3 -B $P/tools/production.py run $RC --index $i --threads 64 --scratch /tmp > $W/logs/calib_idx$i.log 2>&1; echo "index $i done $(( $(date +%s)-s )) s"; done
echo "done $(date -Is)"
