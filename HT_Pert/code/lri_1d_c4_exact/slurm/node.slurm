#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# One node of a production run (array index = node index). Two socket-bound driver instances (numactl
# --cpunodebind/--membind on the NUMA domains of each package: one BLAS process never spans both sockets), each with
# C4_WPS worker processes of (cores per package / C4_WPS) threads; static task partition part = node*2 + socket over
# nparts = C4_NNODES*2. Checkpoints go to cache_L<Lmax>_<numerics sha12> (they are keyed by the numerics sha).
# Submit with slurm/submit.sh prod.
set -euo pipefail
: "${C4_ROOT:?}" "${C4_DATA:?}" "${C4_LMAX:?}" "${C4_NNODES:?}" "${C4_WPS:?}" "${C4_BLOCK:?}" "${C4_EXPECT_SHA:?}"
source "$C4_ROOT/slurm/env.sh"
[[ $- == *e* ]] || { echo "errexit lost" >&2; exit 70; }
cd "$C4_ROOT"
got=$(python c4_run1d.py sha --kind snapshot)
[[ $got == "$C4_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C4_EXPECT_SHA" >&2; exit 64; }
NUM=$(python c4_run1d.py sha --kind numerics)
NODE=${SLURM_ARRAY_TASK_ID:-0}
nsock=$(lscpu -p=SOCKET | grep -v '^#' | sort -u | wc -l)
(( nsock == 2 )) || { echo "expected 2 sockets, found $nsock" >&2; exit 64; }
CACHE=$C4_DATA/cache_L${C4_LMAX}_${NUM:0:12}; LOGD=$C4_DATA/logs/run_L${C4_LMAX}_${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}; mkdir -p "$CACHE" "$LOGD"
echo "[node] job ${SLURM_JOB_ID} array ${SLURM_ARRAY_JOB_ID:-}_${NODE} host $(hostname) partition ${SLURM_JOB_PARTITION} $(date '+%Y-%m-%dT%H:%M:%S%z') Lmax=$C4_LMAX nnodes=$C4_NNODES wps=$C4_WPS block=$C4_BLOCK"
pids=()
for s in 0 1; do
  numa=$(lscpu -p=NODE,SOCKET | grep -v '^#' | awk -F, -v s=$s '$2==s{print $1}' | sort -un | paste -sd,)
  cores=$(lscpu -p=CORE,SOCKET | grep -v '^#' | awk -F, -v s=$s '$2==s{print $1}' | sort -u | wc -l)
  T=$(( cores / C4_WPS )); (( T >= 1 )) || { echo "C4_WPS=$C4_WPS > $cores cores on socket $s" >&2; exit 64; }
  part=$(( NODE * 2 + s )); nparts=$(( C4_NNODES * 2 ))
  echo "[node] socket $s numa=$numa cores=$cores workers=$C4_WPS threads=$T part=$part/$nparts log $LOGD/part${part}.log"
  numactl --cpunodebind="$numa" --membind="$numa" env OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T NUMBA_NUM_THREADS=$T \
    NUMBA_CACHE_DIR="$C4_DATA/numba_cache/$(hostname)_s$s" \
    /usr/bin/time -v python c4_run1d.py run --Lmax "$C4_LMAX" --cache "$CACHE" --workers "$C4_WPS" \
      --part "$part" --nparts "$nparts" --block "$C4_BLOCK" > "$LOGD/part${part}.log" 2>&1 &
  pids+=($!)
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
for s in 0 1; do tail -n 3 "$LOGD/part$(( NODE * 2 + s )).log"; grep -E 'Maximum resident|Elapsed' "$LOGD/part$(( NODE * 2 + s )).log" || true; done
echo "[node] done rc=$rc $(date '+%Y-%m-%dT%H:%M:%S%z')"
exit $rc
