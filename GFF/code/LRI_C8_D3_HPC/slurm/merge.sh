#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
# The merge of a campaign (PLAN D.13), submitted by `tools/slurm_submit.py lanes N|submit|resubmit` with
# C8_MERGE_SBATCH_ARGS (default on Expanse: shared, -c 24, --mem=48G). It checks completeness (exit 65 if incomplete),
# merges every group (valid merged groups are skipped; C8_MERGE_JOBS phase-2 and C8_PARSE_JOBS phase-1 processes,
# default the job's CPUs), then dispatches by campaign role (D.3a, R01; `production.py role`):
#   pilot_subset             -> tools/pilot_report.py subset-check (no coefficient assembly; subset_summary.json)
#   test, pilot_full, production -> tools/assemble.py --bootstrap $C8_BOOTSTRAP (default 4096)
#   anything else            -> exit 64
# Safe to resubmit and to run concurrently (no-clobber, idempotent publication). After a recovered index (a checkpoint
# and its group's merged.json deleted, the index recomputed) the group is re-merged: merged.json is its commit point, so
# its uncommitted tables are replaced and reported (graph_costs.csv: timing only), and a result whose only change is
# merged_sha256 is superseded, the old one kept as *.superseded.<sha12>.json (F8-d3).
set -eo pipefail
source "${C8_PACKAGE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/slurm/common.sh"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory}"
cpus="${SLURM_CPUS_PER_TASK:-4}"
[[ "${C8_MERGE_JOBS:-$cpus}" =~ ^[1-9][0-9]*$ && "${C8_PARSE_JOBS:-$cpus}" =~ ^[1-9][0-9]*$ ]] || { echo "C8: C8_MERGE_JOBS and C8_PARSE_JOBS must be positive integers" >&2; exit 64; }
[[ "${C8_BOOTSTRAP:-4096}" =~ ^[0-9]+$ ]] || { echo "C8: C8_BOOTSTRAP must be a non-negative integer" >&2; exit 64; }
if ! report=$("$PY" -B "$C8_PACKAGE/tools/production.py" status "$C8_RUN" --fast 2>&1); then
  echo "$report" >&2
  echo "C8: campaign incomplete. Run slurm_submit.py resubmit (array mode) or slurm_submit.py lanes N (lane mode)." >&2; exit 65
fi
"$PY" -B "$C8_PACKAGE/tools/production.py" merge "$C8_RUN" --scratch "$C8_SCRATCH" --jobs "${C8_MERGE_JOBS:-$cpus}" --parse-jobs "${C8_PARSE_JOBS:-$cpus}"
role=$("$PY" -B "$C8_PACKAGE/tools/production.py" role "$C8_RUN")
case "$role" in
  pilot_subset) exec "$PY" -B "$C8_PACKAGE/tools/pilot_report.py" subset-check "$C8_RUN" ;;
  test|pilot_full|production) exec "$PY" -B "$C8_PACKAGE/tools/assemble.py" "$C8_RUN" --bootstrap "${C8_BOOTSTRAP:-4096}" ;;
  *) echo "C8: unknown campaign role '$role' of $C8_RUN; nothing assembled" >&2; exit 64 ;;
esac
