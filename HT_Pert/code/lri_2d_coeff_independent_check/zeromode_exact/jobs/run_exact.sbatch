#!/bin/bash
# usage: sbatch [slurm opts] jobs/run_exact.sbatch "L-list" VARIANTS NPRIMES NCHECK PROCS CAPEXTRA TIERS TAG
# exact multi-modular zeromode runs (code/zeromode_modular.py); one output JSON per L in out/<TAG>_L<L>.json
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/zeromode
PY=~/indep2d_rs/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "host $(hostname)  start $(date)  job ${SLURM_JOB_ID:-none}  args: $*"
for L in $1; do
  echo "=== L=$L  $(date)"
  /usr/bin/time -v $PY code/zeromode_modular.py --L $L --variants $2 --nprimes $3 --ncheck $4 --procs $5 \
      --capextra $6 --tiers $7 --out out/${8}_L${L}.json 2> logs/time_${8}_L${L}.txt | grep -vE "C_[0-3] "
  grep -E "Maximum resident|Elapsed|Exit status" logs/time_${8}_L${L}.txt
done
echo "end $(date)"
