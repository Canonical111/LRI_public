#!/usr/bin/env bash
# Optional Slurm entry point. No CPU, memory, time, partition, account, node or
# array-size requests are fixed here; supply them when submitting the job.
# Run one Python driver per array task, not one duplicate process per CPU.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${SLURM_ARRAY_TASK_ID:?Submit as an array, or use run_task.py directly.}"
: "${LRI_WORK_ROOT:?Set a persistent scratch root visible to this job.}"
: "${LRI_OUTPUT_ROOT:?Set an output root visible from the submitting host.}"
PYTHON="${LRI_PYTHON:-python3}"
PLAN="${LRI_PLAN:-$ROOT/cluster/extension_plan.json}"
WORKERS="${LRI_WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"
args=(run --plan "$PLAN" --task-index "$SLURM_ARRAY_TASK_ID"
      --work-root "$LRI_WORK_ROOT" --output-root "$LRI_OUTPUT_ROOT"
      --workers "$WORKERS" --skip-completed)
if [[ -n "${LRI_COEFFICIENT_CACHE:-}" ]]; then
    args+=(--coefficient-cache "$LRI_COEFFICIENT_CACHE")
fi
if [[ -n "${LRI_FFT_WORKERS:-}" ]]; then
    args+=(--fft-workers "$LRI_FFT_WORKERS")
fi
exec "$PYTHON" "$ROOT/cluster/run_task.py" "${args[@]}"
