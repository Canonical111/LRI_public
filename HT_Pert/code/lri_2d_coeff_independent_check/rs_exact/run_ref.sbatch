#!/bin/bash
# usage: sbatch [slurm opts] run_ref.sbatch "L-list" "K-list"
# runs the exact Fraction reference for every (L, K, scheme) as parallel single-core processes
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/rs_exact
PY=~/indep2d_rs/venv/bin/python
echo "host $(hostname)  start $(date)"
for L in $1; do for K in $2; do for s in raw consistent literal; do
  ( /usr/bin/time -f "%e s %M KB" $PY code/ref_fraction.py --L $L --scheme $s --K $K \
        --out out/ref_${s}_L${L}_K${K}.json > logs/ref_${s}_L${L}_K${K}.log 2>&1; \
    echo "done ref $s L=$L K=$K: $(tail -1 logs/ref_${s}_L${L}_K${K}.log)" ) &
done; done; done
wait
echo "end $(date)"
