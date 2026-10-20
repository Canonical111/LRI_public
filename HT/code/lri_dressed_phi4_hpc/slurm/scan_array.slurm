#!/bin/bash
#SBATCH --job-name=lri-dressed
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=logs/dressed-%A_%a.out
#SBATCH --error=logs/dressed-%A_%a.err
set -euo pipefail
# Create logs/ before sbatch; set account/partition on the sbatch command line.
# Submit with e.g. --array=0-2%2. No obsolete allocation/account is hardcoded.
: "${LRI_MANIFEST:?Set to absolute campaign JSON}"
: "${LRI_RECEIPT:?Set to absolute target-cluster validation receipt}"
: "${LRI_OUTPUT:?Set to shared result directory}"
: "${LRI_MEMORY_GIB:?Set to the allocated per-task GiB, not node total}"
cd "${SLURM_SUBMIT_DIR}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-/tmp}/lri-numba-${SLURM_JOB_ID}"
# The allocation runs exactly one process. Signals go to the solver; it checkpoints at a
# safe Newton boundary. An interrupted eigensolve is not serialized.
child=''
forward_signal() { if [[ -n "$child" ]]; then kill -USR1 "$child" 2>/dev/null || true; fi; }
trap forward_signal USR1 TERM
args=(python scripts/run_lane.py --manifest "$LRI_MANIFEST" --index "$SLURM_ARRAY_TASK_ID" --receipt "$LRI_RECEIPT" --output "$LRI_OUTPUT" --threads "$SLURM_CPUS_PER_TASK" --memory-limit-gib "$LRI_MEMORY_GIB")
if [[ -n "${LRI_SEEDS:-}" ]]; then args+=(--seed-dir "$LRI_SEEDS"); fi
# exec path keeps the claim inside the Python solver; no background solver
# survives after this shell exits normally. Scheduler kill still invalidates no
# completed output because result writes are atomic.
"${args[@]}" & child=$!
set +e
wait "$child";rc=$?
# wait may return after the shell trap while Python is still checkpointing.
while kill -0 "$child" 2>/dev/null; do wait "$child";rc=$?;done
exit "$rc"
