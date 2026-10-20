#!/bin/bash
#SBATCH --job-name=c8d2-merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=c8d2-merge-%j.log
# Checks completeness (exit 65 if incomplete; the documented recovery is slurm/resubmit.sh in array mode or
# slurm/submit.sh --lanes N in lane mode, whose queue rebuild also drops stale done markers), merges every group
# (phase 1 parallel over shards, phase 2 an external merge of bounded fan-in parallel over groups; groups already merged
# and valid are skipped, and an interrupted merge resumes from the complete intermediate runs in $C8_RUN/merge_work;
# byte-identical to the serial merge) with C8_MERGE_JOBS processes (default 24), and assembles
# C8_result.json (C8_test_result.json for test-only plans; an existing identical result is kept, one that differs only
# in merged_sha256 after a recovered group was re-merged is superseded and kept as *.superseded.<sha>.json; F8). Safe to resubmit and to
# run concurrently. slurm/submit.sh sets --mem (C8_MERGE_MEM), --time (C8_MERGE_TIME) and -c (C8_MERGE_JOBS).
# C8_BOOTSTRAP sets the bootstrap replicate count (default 4096).
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
[[ "${C8_MERGE_JOBS:-24}" =~ ^[1-9][0-9]*$ ]] || { echo "C8: C8_MERGE_JOBS must be a positive integer" >&2; exit 64; }
[[ "${C8_BOOTSTRAP:-4096}" =~ ^[0-9]+$ ]] || { echo "C8: C8_BOOTSTRAP must be a non-negative integer" >&2; exit 64; }
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
scratch="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
if ! report=$("$PY" -B "$C8_PACKAGE/tools/production.py" status "$C8_RUN" --fast 2>&1); then
  echo "$report" >&2
  echo "C8: campaign incomplete. Run slurm/resubmit.sh (array mode) or slurm/submit.sh --lanes N (lane mode)." >&2; exit 65
fi
"$PY" -B "$C8_PACKAGE/tools/production.py" merge "$C8_RUN" --scratch "$scratch" --jobs "${C8_MERGE_JOBS:-24}"
"$PY" -B "$C8_PACKAGE/tools/assemble.py" "$C8_RUN" --bootstrap "${C8_BOOTSTRAP:-4096}"
