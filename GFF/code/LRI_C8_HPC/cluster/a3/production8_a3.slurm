#!/bin/bash
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G
#SBATCH --time=04:00:00
# Amendment A3 (docs/EXTENSION_A3.md), Expanse: one work element (production8.py run --index SLURM_ARRAY_TASK_ID) of a
# planned A3 batch (b12-b14). Identical to cluster/production8.slurm (the b1-b4 launcher, 16 EPYC cores, 24G) except
# that the executable is given explicitly: the batch was planned on symmetry, so its manifests name the symmetry path
# of the same binary; campaign.py checks the given file against the planned sha256 before every invocation.
# Required: C8_ENV_SETUP, C8_ROOT (frozen code copy c0ffa63), C8_PRODUCTION (batch dir), C8_EXECUTABLE, C8_A3_STOP (the stop
# barrier: an element that starts after it exists exits without work).
set -eo pipefail
[[ -r "${C8_ENV_SETUP:?}" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }
source "$C8_ENV_SETUP"
set -u
PY="${C8_PYTHON:-python3}"
: "${C8_ROOT:?}" "${C8_PRODUCTION:?}" "${C8_EXECUTABLE:?}" "${SLURM_ARRAY_TASK_ID:?Submit as a job array}"
index=$SLURM_ARRAY_TASK_ID
if [[ -e "${C8_A3_STOP:?}" ]]; then echo "C8: A3 stop barrier $C8_A3_STOP present: element $index not started"; exit 0; fi
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}" OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
echo "C8: element $index of $C8_PRODUCTION on $(hostname) at $(date -Is)"
srun --ntasks=1 --cpus-per-task="${SLURM_CPUS_PER_TASK:-16}" --cpu-bind=cores "$PY" "$C8_ROOT/tools/production8.py" run "$C8_PRODUCTION" --index "$index" --threads "$OMP_NUM_THREADS" --executable "$C8_EXECUTABLE" ${scratch_args[@]+"${scratch_args[@]}"}
echo "C8: element $index done at $(date -Is)"
