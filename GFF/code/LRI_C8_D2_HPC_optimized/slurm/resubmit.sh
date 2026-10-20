#!/bin/bash
# Recovery: resubmit every incomplete job index of a campaign that is not still live, and a merge that waits for all
# resubmitted arrays and for every still-live element (afterok). If nothing needs resubmission, only the merge is
# submitted. The decision is `production.py recover` logic on a complete squeue snapshot taken under the campaign
# lock; submission goes through tools/slurm_submit.py (same inputs and guarantees as slurm/submit.sh). Refusals
# (nothing submitted): a merge of the campaign is live (exit 65; scancel it first); a tagged job is completing,
# preempted or in an unrecognised state, or squeue fails (exit 69; rerun later); invalid input (exit 64); another
# submission holds the lock (exit 75).
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
# Managed sites (C8_SITE set, e.g. by slurm/env_<site>.sh) run campaigns through tools/site_submit.py runners, whose
# admission counts every job against the site budget; arrays there need an explicit C8_ALLOW_ARRAYS=1.
if [[ -n "${C8_SITE:-}" && "${C8_ALLOW_ARRAYS:-0}" != 1 ]]; then echo "C8: C8_SITE=$C8_SITE is a managed site: submit with tools/site_submit.py runners (docs/SITES.md); array submission refused (set C8_ALLOW_ARRAYS=1 to override)" >&2; exit 64; fi
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE}"; : "${C8_RUN:?Set C8_RUN}"
exec "$PY" -B "$C8_PACKAGE/tools/slurm_submit.py" resubmit "$@"
