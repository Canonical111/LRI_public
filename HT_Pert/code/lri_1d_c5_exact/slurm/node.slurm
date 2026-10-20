#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# One node of a C5 run (array index = node index; validate.slurm also calls it with SLURM_ARRAY_TASK_ID=0 and
# C5_NNODES=1). Two socket-bound driver instances (numactl --cpunodebind/--membind on the NUMA domains of each package:
# one BLAS process never spans both sockets), each with C5_WPS worker processes of (physical cores per package / C5_WPS)
# threads; static task partition part = node*2 + socket over nparts = C5_NNODES*2 (run5.py run --part/--nparts).
# Checkpoints go to $C5_DATA/cache_L<Lmax>_<numerics sha12> (keyed by the numerics sha; run5.py validates and reuses
# existing ones, so a rerun after a TIMEOUT resumes). Per-part logs: $C5_DATA/logs/run_L<Lmax>_<array job id>/part<k>.log
# (with /usr/bin/time -v). Submit with slurm/submit.sh prod.
set -euo pipefail
: "${C5_ROOT:?}" "${C5_DATA:?}" "${C5_LMAX:?}" "${C5_NNODES:?}" "${C5_WPS:?}" "${C5_BLOCK:?}" "${C5_EXPECT_SHA:?}"
source "$C5_ROOT/slurm/env.sh"
[[ $- == *e* ]] || { echo "errexit lost" >&2; exit 70; }
for v in C5_LMAX C5_NNODES C5_WPS C5_BLOCK; do
  [[ ${!v} =~ ^[1-9][0-9]*$ ]] || { echo "$v='${!v}' is not a positive integer" >&2; exit 64; }
done
cd "$C5_ROOT"
got=$(python run5.py sha --kind snapshot)
[[ $got == "$C5_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C5_EXPECT_SHA" >&2; exit 64; }
NUM=$(python run5.py sha --kind numerics)
[[ $NUM =~ ^[0-9a-f]{64}$ ]] || { echo "numerics sha '$NUM' is not a sha256" >&2; exit 64; }
NODE=${SLURM_ARRAY_TASK_ID:-0}
(( NODE < C5_NNODES )) || { echo "array index $NODE >= C5_NNODES=$C5_NNODES" >&2; exit 64; }
nsock=$(lscpu -p=SOCKET | grep -v '^#' | sort -u | wc -l)
(( nsock == 2 )) || { echo "expected 2 sockets, found $nsock" >&2; exit 64; }
JOBID=${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-nojob}}
CACHE=$C5_DATA/cache_L${C5_LMAX}_${NUM:0:12}; LOGD=$C5_DATA/logs/run_L${C5_LMAX}_$JOBID
echo "[node] job ${SLURM_JOB_ID:-} array ${SLURM_ARRAY_JOB_ID:-}_${NODE} host $(hostname) partition ${SLURM_JOB_PARTITION:-}" \
  "$(date '+%Y-%m-%dT%H:%M:%S%z') Lmax=$C5_LMAX nnodes=$C5_NNODES wps=$C5_WPS block=$C5_BLOCK snapshot ${C5_EXPECT_SHA:0:12} numerics ${NUM:0:12}"
numa=(); thr=()
for s in 0 1; do                    # size both sockets before launching anything
  numa[s]=$(c5_numa $s); cores=$(c5_cores $s)
  [[ -n ${numa[s]} ]] || { echo "no NUMA domain found for socket $s" >&2; exit 64; }
  thr[s]=$(( cores / C5_WPS )); (( thr[s] >= 1 )) || { echo "C5_WPS=$C5_WPS > $cores cores on socket $s" >&2; exit 64; }
  echo "[node] socket $s numa=${numa[s]} cores=$cores workers=$C5_WPS threads=${thr[s]} part=$(( NODE * 2 + s ))/$(( C5_NNODES * 2 ))"
done
mkdir -p "$CACHE" "$LOGD"
pids=()
for s in 0 1; do
  part=$(( NODE * 2 + s )); nparts=$(( C5_NNODES * 2 )); T=${thr[s]}
  echo "[node] socket $s -> log $LOGD/part${part}.log"
  numactl --cpunodebind="${numa[s]}" --membind="${numa[s]}" env OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T NUMBA_NUM_THREADS=$T \
    NUMBA_CACHE_DIR="$C5_DATA/numba_cache/$(hostname)_s$s" \
    /usr/bin/time -v python run5.py run --Lmax "$C5_LMAX" --cache "$CACHE" --workers "$C5_WPS" \
      --part "$part" --nparts "$nparts" --block "$C5_BLOCK" > "$LOGD/part${part}.log" 2>&1 &
  pids+=($!)
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
for s in 0 1; do
  f=$LOGD/part$(( NODE * 2 + s )).log; echo "[node] tail of $f"; tail -n 3 "$f"; grep -E 'Maximum resident|Elapsed' "$f" || true
done
echo "[node] done rc=$rc $(date '+%Y-%m-%dT%H:%M:%S%z')"
exit $rc
