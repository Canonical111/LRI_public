#!/bin/bash
# usage: campaign.sh "<L list>" "<scheme list>" "<variant list>"
# runs every (L, scheme, variant) with 64 worker processes, skipping finished outputs.
set -u
CODE=/mnt/beegfs/zzheng1/indep2d/cauchy/code
RUNS=/mnt/beegfs/zzheng1/indep2d/cauchy/runs
PY=$HOME/indep2d_cauchy/venv/bin/python
NPROC=${NPROC:-64}
export OMP_NUM_THREADS=1
mkdir -p $RUNS
cd $CODE
for L in $1; do
  for scheme in $2; do
    for var in $3; do
      out=$RUNS/${scheme}_L${L}_${var}.json
      [ -s "$out" ] && { echo "skip $out"; continue; }
      case $var in
        base)  a="--rho 1/64 --K 128 --prec 256 --cap 19" ;;
        rhoK)  a="--rho 1/40 --K 96 --prec 256 --cap 19" ;;
        prec)  a="--rho 1/64 --K 128 --prec 352 --cap 19" ;;
        path)  a="--rho 1/64 --K 128 --prec 256 --cap 19 --tsteps 0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1" ;;
        cap17) a="--rho 1/64 --K 128 --prec 256 --cap 17" ;;
        cap18) a="--rho 1/64 --K 128 --prec 256 --cap 18" ;;
        cap21) a="--rho 1/64 --K 128 --prec 256 --cap 21" ;;
        cap23) a="--rho 1/64 --K 128 --prec 256 --cap 23" ;;
        fast)  a="--rho 1/64 --K 64 --prec 256 --cap 19 --half" ;;
        *) echo "unknown variant $var"; exit 1 ;;
      esac
      echo "=== $(date) L=$L scheme=$scheme variant=$var : $a"
      $PY run_points.py --scheme $scheme --L $L $a --procs $NPROC --out $out.tmp > $RUNS/${scheme}_L${L}_${var}.log 2>&1 \
        && mv $out.tmp $out && echo "done $out" || { echo "FAILED $out"; tail -5 $RUNS/${scheme}_L${L}_${var}.log; }
    done
  done
done
echo "=== campaign finished $(date)"
