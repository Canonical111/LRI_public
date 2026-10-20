#!/bin/bash
# Submit a planned campaign: work arrays of at most C6_MAX_ARRAY elements (default 1000 = Expanse MaxArraySize), each
# with its own C6_INDEX_OFFSET and at most C6_THROTTLE running elements (default 64), then slurm/merge.sh with an
# afterok dependency on every array. `submit.sh --window OFFSET:ARRAY` submits one window only (the form printed by
# `production.py status`). All submissions go through tools/slurm_submit.py, which validates every input
# (see its docstring) and tags each job with the Slurm comment <campaign tag>:off=<offset> or <tag>:merge.
#
#   export C6_PACKAGE=/path/to/LRI_C6_D3_HPC C6_RUN=/expanse/lustre/scratch/$USER/temp_project/c6-d3/run1
#   export C6_ENV_SETUP=/path/to/expanse_env.sh C6_SBATCH_ARGS="-A yun124 -p shared"
#   slurm/submit.sh                          # extra arguments: allowlisted sbatch options for the work arrays
#
# CPUs per element default to the plan's --threads and the wall time to the plan's suggestion; extra arguments may
# override those two, never the array, tag, offset, output or export. Logs: $C6_RUN/slurm_logs/. If a work element
# fails, the merge never starts (afterok): `scancel` the pending merge, then run slurm/resubmit.sh.
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts
if [[ -n "${C6_ENV_SETUP:-}" ]]; then [[ -r "$C6_ENV_SETUP" ]] || { echo "C6: cannot read C6_ENV_SETUP=$C6_ENV_SETUP" >&2; exit 64; }; source "$C6_ENV_SETUP"; fi
PY="${C6_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C6: $PY is missing or older than Python 3.10; set C6_PYTHON or C6_ENV_SETUP" >&2; exit 64; }
: "${C6_PACKAGE:?Set C6_PACKAGE}"; : "${C6_RUN:?Set C6_RUN}"
if [[ "${1:-}" == --window ]]; then shift; exec "$PY" -B "$C6_PACKAGE/tools/slurm_submit.py" window "$@"; fi
exec "$PY" -B "$C6_PACKAGE/tools/slurm_submit.py" submit "$@"
