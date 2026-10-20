#!/bin/bash
#SBATCH --job-name=c7-merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=c7-merge-%j.log
# Optional: C7_ENV_SETUP (sourced with errexit, before nounset; e.g. modules + venv), C7_PYTHON (default python3, >=3.8).
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts the job
if [[ -n "${C7_ENV_SETUP:-}" ]]; then [[ -r "$C7_ENV_SETUP" ]] || { echo "C7: cannot read C7_ENV_SETUP=$C7_ENV_SETUP" >&2; exit 64; }; echo "C7: sourcing $C7_ENV_SETUP" >&2; source "$C7_ENV_SETUP"; fi
set -u # nounset only after site setup (module/bashrc scripts often reference unset variables)
PY="${C7_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)' || { echo "C7: $PY is missing or older than Python 3.8; set C7_PYTHON or C7_ENV_SETUP" >&2; exit 64; }
: "${C7_ROOT:?Export the absolute extracted package directory}"
: "${C7_PRODUCTION:?Export the absolute full production-plan directory}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
"$PY" "$C7_ROOT/tools/production.py" merge "$C7_PRODUCTION" ${scratch_args[@]+"${scratch_args[@]}"}
