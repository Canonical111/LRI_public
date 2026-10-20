#!/bin/bash
# Submit a planned campaign: work arrays of at most C8_MAX_ARRAY elements (default 1000), each with its own
# C8_INDEX_OFFSET and at most C8_THROTTLE running elements (default 64), then slurm/merge.sh with an afterok
# dependency on every array. `submit.sh --window OFFSET:ARRAY` submits one window only (the form printed by
# `production.py status`). All submissions go through tools/slurm_submit.py, which validates every input, takes the
# campaign lock and a squeue snapshot first (see its docstring), and tags each job with the Slurm comment
# <campaign tag>:off=<offset> or <tag>:merge.
#
#   export C8_PACKAGE=/path/to/LRI_C8_D2_HPC C8_RUN=/shared/fs/c8-d2/run1
#   export C8_ENV_SETUP=/path/to/env.sh C8_SBATCH_ARGS="-p amdq"     # site options, allowlisted
#   export C8_TIME_POLICY=unlimited                                    # only where the site requires --time=0
#   slurm/submit.sh                    # extra arguments: allowlisted sbatch options for the work arrays
#
# CPUs per element default to the plan's --threads and the wall time to the plan's suggestion; extra arguments may
# override those two, never the array, tag, offset, output or export. Logs: $C8_RUN/slurm_logs/. If a work element
# fails, the merge never starts (afterok): `scancel` the pending merge, then run slurm/resubmit.sh.
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
# Managed sites (C8_SITE set, e.g. by slurm/env_<site>.sh) run campaigns through tools/site_submit.py runners, whose
# admission counts every job against the site budget; arrays there need an explicit C8_ALLOW_ARRAYS=1.
if [[ -n "${C8_SITE:-}" && "${C8_ALLOW_ARRAYS:-0}" != 1 ]]; then echo "C8: C8_SITE=$C8_SITE is a managed site: submit with tools/site_submit.py runners (docs/SITES.md); array submission refused (set C8_ALLOW_ARRAYS=1 to override)" >&2; exit 64; fi
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE}"; : "${C8_RUN:?Set C8_RUN}"
if [[ "${1:-}" == --window ]]; then shift; exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" window "$@"; fi
exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" submit "$@"
