#!/bin/bash
# usage: sbatch [slurm opts] run_diag.sbatch "L-list" KDIAG [TAG]
# non-perturbative mpmath check of results/<scheme>_L<L>.json for all schemes, in parallel
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/rs_exact
PY=~/indep2d_rs/venv/bin/python
TAG=${3:-}
echo "host $(hostname)  start $(date)"
for L in $1; do for s in raw consistent literal; do
  ( /usr/bin/time -f "%e s %M KB" $PY code/diag_check.py --json results/${s}_L${L}.json --eps 1e-3,1e-5,1e-8 \
        --Kdiag $2 --dps 110 > logs/diag${TAG}_${s}_L${L}.log 2>&1; echo "done diag $s L=$L" ) &
done; done
wait
echo "end $(date)"
