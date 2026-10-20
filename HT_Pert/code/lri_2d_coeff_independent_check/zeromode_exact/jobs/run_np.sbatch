#!/bin/bash
# usage: sbatch [slurm opts] jobs/run_np.sbatch "L-list" "variant-list" PROCS
# non-perturbative zeromode hierarchy on the circle (code/np_check/run_zm_points.py); runs/zm_L<L>_<variant>.json
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/zeromode
PY=~/indep2d_rs/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "host $(hostname)  start $(date)  job ${SLURM_JOB_ID:-none}  args: $*"
for L in $1; do for V in $2; do
  case $V in
    base)  OPT="--Zh 18 --rho 1/256 --K 128 --prec 320 --cap 19" ;;
    zh14)  OPT="--Zh 14 --rho 1/256 --K 128 --prec 320 --cap 19" ;;
    rhoK)  OPT="--Zh 18 --rho 1/400 --K 96 --prec 320 --cap 19" ;;
    prec)  OPT="--Zh 18 --rho 1/256 --K 128 --prec 384 --cap 19" ;;
    path)  OPT="--Zh 18 --rho 1/256 --K 128 --prec 320 --cap 19 --tsteps 0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1" ;;
    cap21) OPT="--Zh 20 --rho 1/256 --K 128 --prec 320 --cap 21" ;;
    *) echo "unknown variant $V"; continue ;;
  esac
  echo "=== L=$L variant=$V ($OPT)  $(date)"
  P=$3; [ "$P" = auto ] && P=$(lscpu -p=CORE,SOCKET | grep -v "^#" | sort -u | wc -l)
  $PY code/np_check/run_zm_points.py --L $L $OPT --half --procs $P --cache code/np_check/cache \
      --out runs/zm_L${L}_${V}.json > runs/zm_L${L}_${V}.log 2>&1
  echo "exit $?  $(date)"; tail -2 runs/zm_L${L}_${V}.log
done; done
echo "end $(date)"
