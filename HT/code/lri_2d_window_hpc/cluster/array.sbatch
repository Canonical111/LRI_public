#!/bin/bash
#SBATCH --job-name=ht2d
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=logs/ht2d_%A_%a.out
set -euo pipefail
: "${HT2D_ROOT:?Set HT2D_ROOT to this immutable release}"
: "${HT2D_MANIFEST:?Set HT2D_MANIFEST to the generated manifest}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-/tmp}/ht2d-numba-${SLURM_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
mkdir -p "$NUMBA_CACHE_DIR"
child=''
forward_stop() { if [[ -n "$child" ]]; then kill -USR1 "$child" 2>/dev/null || true; fi; }
trap forward_stop USR1 TERM INT
python "$HT2D_ROOT/cluster/run_item.py" --manifest "$HT2D_MANIFEST" --index "$SLURM_ARRAY_TASK_ID" &
child=$!
# wait can be interrupted by the signal sent to the shell; keep waiting for
# Python to checkpoint/release ownership rather than launch a duplicate writer.
rc=0
while true; do
    wait "$child" && rc=0 || rc=$?
    if ! kill -0 "$child" 2>/dev/null; then break; fi
done
exit "$rc"
