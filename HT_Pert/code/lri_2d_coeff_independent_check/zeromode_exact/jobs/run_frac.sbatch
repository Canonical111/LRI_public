#!/bin/bash
# usage: sbatch [slurm opts] jobs/run_frac.sbatch "L-list"   (Fraction reference, one process per L in parallel)
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/zeromode
PY=~/indep2d_rs/venv/bin/python
echo "host $(hostname)  start $(date)  job ${SLURM_JOB_ID:-none}"
for L in $1; do
  ( /usr/bin/time -v $PY code/zeromode_fraction.py --L $L --out out/frac_L${L}.json > logs/frac_L${L}.log 2> logs/time_frac_L${L}.txt ; echo "L=$L done $(date) exit $?" ) &
done
wait
echo "end $(date)"
