#!/bin/bash
#SBATCH --job-name=lri-c6-d3-merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=lri-c6-d3-merge-%j.log
# Checks completeness, merges every group (groups already merged and valid are skipped) and assembles C6_result.json
# (an existing identical result is kept). Safe to resubmit. Same environment variables as slurm/run_array.sh;
# C6_BOOTSTRAP sets the bootstrap replicate count (default 4096).
set -eo pipefail
if [[ -n "${C6_ENV_SETUP:-}" ]]; then [[ -r "$C6_ENV_SETUP" ]] || { echo "C6: cannot read C6_ENV_SETUP=$C6_ENV_SETUP" >&2; exit 64; }; source "$C6_ENV_SETUP"; fi
set -u
PY="${C6_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C6: $PY is missing or older than Python 3.10; set C6_PYTHON or C6_ENV_SETUP" >&2; exit 64; }
: "${C6_PACKAGE:?Set C6_PACKAGE to the package directory}"
: "${C6_RUN:?Set C6_RUN to the planned campaign directory on a shared filesystem}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
if ! report=$("$PY" -B "$C6_PACKAGE/tools/production.py" status "$C6_RUN" 2>&1); then
  echo "$report" >&2
  echo "C6: campaign incomplete. Run slurm/resubmit.sh (resubmits the listed indices and a dependent merge)." >&2; exit 65
fi
"$PY" -B "$C6_PACKAGE/tools/production.py" merge "$C6_RUN" ${scratch_args[@]+"${scratch_args[@]}"}
"$PY" -B "$C6_PACKAGE/tools/assemble.py" "$C6_RUN" --bootstrap "${C6_BOOTSTRAP:-4096}"
