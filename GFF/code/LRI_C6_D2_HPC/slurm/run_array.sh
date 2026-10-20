#!/bin/bash
#SBATCH --job-name=lri-c6-d2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=lri-c6-d2-%A_%a.log
# Site options go on the sbatch command line (or in C6_SBATCH_ARGS for slurm/submit.sh), e.g. for SDSC Expanse:
#   -A <ACCOUNT> -p shared
# Use the wall time printed by `production.py plan` (suggested_sbatch_time) instead of the default above.
# Environment: C6_PACKAGE and C6_RUN (a campaign directory on a SHARED filesystem) are required. Optional:
#   C6_ENV_SETUP     script sourced with errexit on and before nounset (modules + venv; slurm/expanse_env.sh.example)
#   C6_PYTHON        interpreter (default python3; >= 3.10)
#   C6_INDEX_OFFSET  added to SLURM_ARRAY_TASK_ID, so plans may exceed MaxArraySize (slurm/submit.sh sets it)
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts the job
if [[ -n "${C6_ENV_SETUP:-}" ]]; then [[ -r "$C6_ENV_SETUP" ]] || { echo "C6: cannot read C6_ENV_SETUP=$C6_ENV_SETUP" >&2; exit 64; }; source "$C6_ENV_SETUP"; fi
set -u # nounset only after site setup (module and bashrc scripts often reference unset variables)
PY="${C6_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C6: $PY is missing or older than Python 3.10; set C6_PYTHON or C6_ENV_SETUP" >&2; exit 64; }
: "${C6_PACKAGE:?Set C6_PACKAGE to the package directory}"
: "${C6_RUN:?Set C6_RUN to the planned campaign directory on a shared filesystem}"
: "${SLURM_ARRAY_TASK_ID:?Submit as a job array}"
[[ "${C6_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C6: C6_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C6_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
export OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
echo "C6: index $index (offset ${C6_INDEX_OFFSET:-0} + array ${SLURM_ARRAY_TASK_ID}) on $(hostname), $OMP_NUM_THREADS threads" >&2
# Python runs in the batch step (no srun), which holds the whole allocation: OpenMP sees every allocated core.
"$PY" -B "$C6_PACKAGE/tools/production.py" run "$C6_RUN" --index "$index" --threads "$OMP_NUM_THREADS" \
  ${scratch_args[@]+"${scratch_args[@]}"}
