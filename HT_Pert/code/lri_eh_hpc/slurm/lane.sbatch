#!/bin/bash
#SBATCH --job-name=lri-eh-delta
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=USR1@180
#SBATCH --requeue
#SBATCH --output=logs/eh-%A_%a.out
#SBATCH --error=logs/eh-%A_%a.err
# Supply account, partition, time, memory, CPUs and --array on the sbatch command.
# A homogeneous array must have the same threads/memory settings in every lane.
# No account expiry date or machine-specific quota is embedded here.
set -euo pipefail
: "${EH_ROOT:?Set EH_ROOT to the extracted/installable package root}"
: "${EH_MANIFEST:?Set EH_MANIFEST to an absolute manifest JSON path}"
: "${SLURM_ARRAY_TASK_ID:?Submit as an array, including a single-lane 0-0 array}"
: "${SLURM_CPUS_PER_TASK:?Supply --cpus-per-task}"
cd "$EH_ROOT"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$EH_ROOT${PYTHONPATH:+:$PYTHONPATH}"
SRC=$(python -m lri_eh source)
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/lri-eh-${USER}/${SRC}"
mkdir -p "$NUMBA_CACHE_DIR"
# Check allocation against manifest before doing numerical work.
python - "$EH_MANIFEST" "$SLURM_ARRAY_TASK_ID" <<'PY'
import json,os,sys
x=json.load(open(sys.argv[1]));lane=x['lanes'][int(sys.argv[2])]
if lane['threads']!=int(os.environ['SLURM_CPUS_PER_TASK']):raise SystemExit('Manifest/allocation CPU mismatch')
m=os.environ.get('SLURM_MEM_PER_NODE')
if m and float(m)<lane['memory_limit_gib']*1024:raise SystemExit('Allocation below manifest memory budget')
PY
# The numerical process holds the claim. SIGUSR1 reaches the Slurm job step;
# its lane supervisor forwards it to the current solver, which exits at a safe
# scalar-checkpoint boundary. Exit 75 requires resubmission with the same manifest.
exec srun --ntasks=1 --cpu-bind=cores python -m lri_eh lane \
    --manifest "$EH_MANIFEST" --lane "$SLURM_ARRAY_TASK_ID"
