#!/bin/bash
#SBATCH --job-name=lri-c8-d2-merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=lri-c8-d2-merge-%j.log
# Checks completeness, merges every group (groups already merged and valid are skipped) and assembles C8_result.json
# (C8_test_result.json for --test-graphs plans; an existing identical result is kept). Safe to resubmit. Same
# environment variables as slurm/run_array.sh; C8_BOOTSTRAP sets the bootstrap replicate count (default 4096).
# C8_MERGE_WORKERS opts into independent concurrent group merges (default 1).
# slurm_submit.py requests the same number of CPUs for the merge allocation.
# Site options (-A/-p) as for run_array.sh; slurm/submit.sh sets --time (02:00:00, or --time=0 under C8_TIME_POLICY=unlimited).
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
scratch="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
if ! report=$("$PY" -B "$C8_PACKAGE/tools/production.py" status "$C8_RUN" 2>&1); then
  echo "$report" >&2
  echo "C8: campaign incomplete. Run slurm/resubmit.sh (resubmits the listed indices and a dependent merge)." >&2; exit 65
fi
merge_workers="${C8_MERGE_WORKERS:-1}"
[[ "$merge_workers" =~ ^[1-9][0-9]*$ ]] || { echo "C8: C8_MERGE_WORKERS must be positive" >&2; exit 64; }
if (( merge_workers > ${SLURM_CPUS_PER_TASK:-1} )); then echo "C8: C8_MERGE_WORKERS exceeds allocated CPUs" >&2; exit 64; fi
"$PY" -B "$C8_PACKAGE/tools/production.py" merge "$C8_RUN" --scratch "$scratch" --workers "$merge_workers"
"$PY" -B "$C8_PACKAGE/tools/assemble.py" "$C8_RUN" --bootstrap "${C8_BOOTSTRAP:-4096}"
