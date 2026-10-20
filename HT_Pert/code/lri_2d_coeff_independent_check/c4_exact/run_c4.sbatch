#!/bin/bash
# usage: sbatch [-p ...] run_c4.sbatch <Lmax> <GB_per_worker> [extra]
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/c4_exact/logs/%x_%j.out
set -euo pipefail
LMAX=${1:?Lmax}; GBPW=${2:?GB per worker}; EXTRA=${3:-}
WD=/mnt/beegfs/zzheng1/indep2d/c4_exact
cd "$WD"
if [[ -f "results/c4_L$LMAX.npz" ]]; then echo "# results/c4_L$LMAX.npz already exists: nothing to do"; exit 0; fi
phys_alloc() {
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}; BUDGET=$(( PA < CAP ? PA : CAP ))
MEMGB=$(( ${SLURM_MEM_PER_NODE:-100000} / 1024 ))
WC=$(( BUDGET / 2 )); WM=$(( (MEMGB - 12) / GBPW ))
W=$(( WC < WM ? WC : WM ))
if [[ "$EXTRA" == brute ]]; then W=$(( W - 1 )); fi
(( W >= 1 )) || { echo "refusing: no worker fits"; exit 64; }
THR=$(( BUDGET / W ))
export OMP_NUM_THREADS=$THR OPENBLAS_NUM_THREADS=$THR MKL_NUM_THREADS=$THR NUMBA_NUM_THREADS=$THR
echo "# host $(hostname) job ${SLURM_JOB_ID} partition ${SLURM_JOB_PARTITION} phys=$PA cpus=$CAP mem=${MEMGB}G workers=$W threads=$THR Lmax=$LMAX $(date)"
PY=~/indep2d_c4/venv/bin/python
mkdir -p results brute
if [[ "$EXTRA" == brute ]]; then
  ( for L in 10 12; do RS_EXACT_DIR=$WD/vendor OMP_NUM_THREADS=1 $PY brute_corrected.py --L $L --out brute/brute_L$L.json \
      > logs/brute_L${L}_${SLURM_JOB_ID}.log 2>&1; done ) &
  BPID=$!
fi
/usr/bin/time -v $PY c4_run.py --Lmax "$LMAX" --workers "$W" --cache "cache_L$LMAX" --out "results/c4_L$LMAX.npz" 2>&1
if [[ "$EXTRA" == brute ]]; then wait $BPID || true; for f in logs/brute_L*_${SLURM_JOB_ID}.log; do tail -n 2 "$f"; done; fi
echo "# finished $(date)"
