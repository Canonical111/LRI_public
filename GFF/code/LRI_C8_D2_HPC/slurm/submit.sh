#!/bin/bash
# Submit a planned C8(2) campaign. Lane mode (symmetry's default): `submit.sh --lanes N` submits N whole-node lane
# workers (slurm/lane_worker.sh) and one merge that waits (afterany) for them and for every live lane worker; a later
# `--lanes N` releases claims of finished workers, rebuilds the queue (dropping done markers of incomplete indices),
# adds workers, submits a new merge on all live workers and then cancels a superseded merge while the scheduler still
# holds it pending (scontrol hold, then scancel --state=PENDING; one that started is left alone). Array mode:
# `submit.sh` submits work arrays of at most C8_MAX_ARRAY elements (default 1000), each with its own C8_INDEX_OFFSET and
# at most C8_THROTTLE running elements (default 64), then slurm/merge.sh with an afterok dependency on every array;
# `submit.sh --window OFFSET:ARRAY` submits one window only (the form printed by `production.py status`). Every
# submission goes through tools/slurm_submit.py (allowlisted options, the campaign lock, a queue snapshot, admission:
# the Expanse H7E-R reservation under C8_SITE=expanse and the AMD-pool cap C8_AMDQ_CAP on symmetry, the allocation
# ledger $C8_RUN/submissions.jsonl), which names every job c8d2-* and tags it with the Slurm comment
# <campaign tag>:off=<offset>, <tag>:lane or <tag>:merge.
#
#   symmetry: export C8_PACKAGE=/mnt/beegfs/$USER/c8d2/pkg/<sha12> C8_RUN=/mnt/beegfs/$USER/c8-d2/run1 C8_ENV_SETUP=$HOME/c8d2/env.sh
#             C8_SITE=symmetry C8_AMDQ_CAP=4 C8_SBATCH_ARGS="-p amdq --exclude=cn112" C8_LANE_MEM=245G slurm/submit.sh --lanes 2
#   Expanse:  export C8_SITE=expanse C8_ENV_SETUP=$HOME/c8d2/env_expanse.sh C8_SBATCH_ARGS="-A yun124 -p compute" C8_LANE_MEM=240G
#             slurm/submit.sh --lanes 1        (shared arrays: C8_SBATCH_ARGS="-A yun124 -p shared" slurm/submit.sh)
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE}"; : "${C8_RUN:?Set C8_RUN}"
if [[ "${1:-}" == --window ]]; then shift; exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" window "$@"; fi
if [[ "${1:-}" == --lanes ]]; then shift; exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" lanes "$@"; fi
exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" submit "$@"
