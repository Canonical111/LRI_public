#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 64
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH -t 06:00:00
#SBATCH -J c7d2-thru
#SBATCH -o <SCRATCH>/c7d2_fix/logs/%x_%j.out
# Drill 6 (A-M4): block throughput of large L7 shards at 64 threads, checkpoint_tasks 1024 (>=16 x threads).
set -eo pipefail; source $HOME/c7d2_prod/env.sh; set -u
W=<SCRATCH>/c7d2_fix; P=$W/final; RT=$W/thru
export OMP_NUM_THREADS=64 OMP_PLACES=cores OMP_PROC_BIND=close OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
echo "host $(hostname) job $SLURM_JOB_ID $(date -Is) $(lscpu | grep 'Model name')"
for i in $IDX; do t0=$(date +%s.%N); python3 -B $P/tools/production.py run $RT --index $i --threads 64 --scratch /tmp > $W/logs/thru_idx$i.log 2>&1; t1=$(date +%s.%N); echo "index $i wall $(python3 -c "print(round($t1-$t0,2))")"; done
echo "done $(date -Is)"
