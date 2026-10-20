#!/bin/bash
# Array-mode recovery: resubmit every incomplete job index of a campaign that is not still live, and a merge that waits
# for all resubmitted arrays and for every still-live element (afterok). If nothing needs resubmission, only the merge
# is submitted. The decision is `production.py recover` on a complete squeue snapshot taken under the campaign lock;
# submission goes through tools/slurm_submit.py (same inputs, admission and guarantees as slurm/submit.sh). Refusals
# (nothing submitted): a merge or a lane worker of the campaign is live (exit 65; scancel a pending merge first; lane
# campaigns recover with slurm/submit.sh --lanes N); a tagged job is completing, preempted or in an unrecognised state,
# or squeue fails (exit 69); invalid input (exit 64); a full admission budget (exit 65); a held lock (exit 75).
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE}"; : "${C8_RUN:?Set C8_RUN}"
exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" resubmit "$@"
