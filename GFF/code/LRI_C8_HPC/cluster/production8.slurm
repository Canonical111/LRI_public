#!/bin/bash
#SBATCH --job-name=c8
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%A_%a.out
# Runs one work element (production8.py run --index C8_INDEX_OFFSET+SLURM_ARRAY_TASK_ID) of a planned C8 batch.
# Required: C8_ENV_SETUP (sourced with errexit, before nounset), C8_ROOT (frozen code copy), C8_PRODUCTION (batch dir).
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
: "${C8_ROOT:?}" "${C8_PRODUCTION:?}" "${SLURM_ARRAY_TASK_ID:?Submit as a job array}"
[[ "${C8_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C8: C8_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C8_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}" OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
echo "C8: element $index of $C8_PRODUCTION on $(hostname) at $(date -Is)"
srun --ntasks=1 --cpus-per-task="${SLURM_CPUS_PER_TASK:-16}" --cpu-bind=cores "$PY" "$C8_ROOT/tools/production8.py" run "$C8_PRODUCTION" --index "$index" --threads "$OMP_NUM_THREADS" ${scratch_args[@]+"${scratch_args[@]}"}
echo "C8: element $index done at $(date -Is)"
