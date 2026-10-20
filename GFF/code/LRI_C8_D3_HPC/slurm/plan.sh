#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
# A real plan runs in a shared job (PLAN D.4, HD15): submit it through
#   tools/slurm_submit.py raw --role plan --dir $C8_ROOT/runs/<name> -- -A yun124 -p shared --nodes=1 -c 4 --mem=16G \
#       -t 01:00:00 --wrap "$C8_PACKAGE/slurm/plan.sh $C8_ROOT/runs/<name> <plan arguments>"
# It plans on the job's node-local scratch (production.py plan --scratch $C8_SCRATCH; the SQLite files are never
# written on Lustre in place), reserves the campaign's base seed in $C8_SEEDS before anything is built or published
# (production.py plan --reserve-seed: rechecked under the session lock and keyed by the campaign directory, so a retry
# of this directory is idempotent, another directory with the same seed is refused when the plan checks seeds, and a
# killed plan keeps its reservation; HD6, S2-002), publishes with one rename that fails when the directory exists
# (S2-005) and registers the job in the ledger (ledger.py register --role plan), in that order.
set -eo pipefail
source "${C8_PACKAGE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/slurm/common.sh"
[[ $# -ge 1 ]] || { echo "usage: plan.sh CAMPAIGN_DIR <production.py plan arguments>" >&2; exit 64; }
run="$1"; shift
"$PY" -B "$C8_PACKAGE/tools/production.py" plan "$run" --scratch "$C8_SCRATCH" ${C8_SEEDS:+--reserve-seed "$C8_SEEDS"} "$@"
"$PY" -B "$C8_PACKAGE/tools/ledger.py" register "$run" --role plan
