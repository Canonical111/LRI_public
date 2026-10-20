#!/bin/bash
# usage: sbatch [slurm opts] run_fast.sbatch "L-list" "K-list" NPRIMES NCHECK [PROCS]
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/rs_exact
PY=~/indep2d_rs/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PROCS=${5:-${SLURM_CPUS_ON_NODE:-64}}
echo "host $(hostname)  start $(date)  procs $PROCS"
for K in $2; do for L in $1; do
  echo "=== L=$L K=$K  $(date)"
  /usr/bin/time -v $PY code/fast_modular.py --L $L --K $K --nprimes $3 --ncheck $4 --procs $PROCS \
     --out out/fast_L${L}_K${K}.json 2> logs/time_fast_L${L}_K${K}.txt | grep -vE "^#   (raw|consistent|literal) C_[0-7] "
  grep -E "Maximum resident|Elapsed|Exit status" logs/time_fast_L${L}_K${K}.txt
done; done
echo "end $(date)"
