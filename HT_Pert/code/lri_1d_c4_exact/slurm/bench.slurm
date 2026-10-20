#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Single-task benchmark (PLAN sec. 3.6: worker sizing from measured peak RSS): the most expensive task(s) at
# Lmax = C4_LMAX, one process bound to socket 0, for each thread count in C4_THREADS (space separated).
set -euo pipefail
: "${C4_ROOT:?}" "${C4_DATA:?}" "${C4_LMAX:?}" "${C4_THREADS:?}" "${C4_EXPECT_SHA:?}"
source "$C4_ROOT/slurm/env.sh"
cd "$C4_ROOT"
got=$(python c4_run1d.py sha --kind snapshot)
[[ $got == "$C4_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C4_EXPECT_SHA" >&2; exit 64; }
numa=$(lscpu -p=NODE,SOCKET | grep -v '^#' | awk -F, '$2==0{print $1}' | sort -un | paste -sd,)
echo "[bench] job $SLURM_JOB_ID host $(hostname) partition $SLURM_JOB_PARTITION socket0 numa=$numa Lmax=$C4_LMAX"
for T in $C4_THREADS; do
  for task in ${C4_TASKS:-0}; do
    numactl --cpunodebind="$numa" --membind="$numa" env OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T NUMBA_NUM_THREADS=$T \
      NUMBA_CACHE_DIR="$C4_DATA/numba_cache/$(hostname)_bench" \
      python c4_run1d.py bench --Lmax "$C4_LMAX" --task "$task" --block "${C4_BLOCK:-32}"
  done
done
