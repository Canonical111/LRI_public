#!/bin/bash
#SBATCH --job-name=c7-kernels
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=4G
#SBATCH --time=04:00:00
#SBATCH --output=c7-%A_%a.log
# Supply --array at submission; partition/account/time/memory are site-dependent.
# Optional: C7_ENV_SETUP (sourced with errexit, before nounset; e.g. modules + venv), C7_PYTHON (default python3, >=3.8),
# C7_INDEX_OFFSET (default 0; the work index is C7_INDEX_OFFSET+SLURM_ARRAY_TASK_ID, so plans may exceed MaxArraySize).
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts the job
if [[ -n "${C7_ENV_SETUP:-}" ]]; then [[ -r "$C7_ENV_SETUP" ]] || { echo "C7: cannot read C7_ENV_SETUP=$C7_ENV_SETUP" >&2; exit 64; }; echo "C7: sourcing $C7_ENV_SETUP" >&2; source "$C7_ENV_SETUP"; fi
set -u # nounset only after site setup (module/bashrc scripts often reference unset variables)
PY="${C7_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)' || { echo "C7: $PY is missing or older than Python 3.8; set C7_PYTHON or C7_ENV_SETUP" >&2; exit 64; }
: "${C7_ROOT:?Export the absolute extracted package directory}"
: "${C7_CAMPAIGN:?Export the absolute directory containing manifest.json}"
: "${SLURM_ARRAY_TASK_ID:?Submit as a job array}"
[[ "${C7_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C7: C7_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C7_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export OMP_DYNAMIC=FALSE
export OMP_PLACES=cores
export OMP_PROC_BIND=close
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
# The executable is built and input indices are generated BEFORE submission.
# Each array element is one shared-memory process; elements may run on many nodes.
# --cpus-per-task on srun is required: Slurm 22.05-23.02 steps do not inherit it and would get one CPU.
srun --ntasks=1 --cpus-per-task="${SLURM_CPUS_PER_TASK:-8}" --cpu-bind=cores "$PY" "$C7_ROOT/tools/campaign.py" run \
  "$C7_CAMPAIGN" --index "$index" --threads "$OMP_NUM_THREADS" \
  ${scratch_args[@]+"${scratch_args[@]}"}
