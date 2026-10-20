#!/bin/bash
#SBATCH --job-name=c8d2-ind-run
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=c8d2-ind-run-%j.log
# One whole-node runner of a site campaign (docs/SITES.md). Submitted only by tools/site_submit.py, which sets every
# option (account, partition, -c = the plan's --threads, --mem, --time, name, comment, append-mode log) and the
# environment: C8_PACKAGE, C8_RUN, C8_SITE and C8_ENV_SETUP (slurm/env_<site>.sh). It runs tools/node_runner.py run,
# which claims indices heaviest first and runs the unchanged `production.py run RUN --index I --threads T --scratch
# $TMPDIR/idx<I> [--max-blocks k]` on each, until no eligible index (or, for cost-model plans, no block) fits.
# Signals: TERM (scancel, wall time; also INT and HUP) is forwarded to the runner, which forwards it to production.py;
# the attempt is recorded `term`, its claim removed, and the job exits 128+signal.
set -euo pipefail # the env file suspends nounset around its module and venv code
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
: "${SLURM_JOB_ID:?Submit with tools/site_submit.py runners}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OMP_DYNAMIC=FALSE OMP_PLACES="${OMP_PLACES:-cores}" OMP_PROC_BIND="${OMP_PROC_BIND:-close}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
scratch="${TMPDIR:-/tmp}"
echo "C8: runner job $SLURM_JOB_ID (restart ${SLURM_RESTART_COUNT:-0}) on $(hostname): $OMP_NUM_THREADS threads, scratch $scratch, campaign $C8_RUN" >&2
child=""
cleanup() { if declare -F c8_site_cleanup >/dev/null; then c8_site_cleanup; fi; }
on_signal() {
  trap - TERM INT HUP
  echo "C8: runner job $SLURM_JOB_ID: signal $(( $1 - 128 )) received; forwarding TERM to the runner" >&2
  local pids p; pids="$(jobs -p)"  # every background job, and the runner if it started just before `child=$!` ran
  for p in $child; do case " $pids " in *" $p "*) ;; *) pids="$pids $p" ;; esac; done
  if [[ -n "${pids// /}" ]]; then kill -TERM $pids 2>/dev/null || true; wait $pids 2>/dev/null || true; fi
  cleanup; trap - EXIT; exit "$1"
}
trap cleanup EXIT
trap 'on_signal 143' TERM; trap 'on_signal 130' INT; trap 'on_signal 129' HUP
# The runner runs in the background so that a trapped signal is handled at once (bash defers traps while a
# foreground child runs); it holds the whole allocation (no srun).
"$PY" -B "$C8_PACKAGE/tools/node_runner.py" run "$C8_RUN" --threads "$OMP_NUM_THREADS" --scratch "$scratch" &
child=$!
set +e; wait "$child"; status=$?; set -e
child=""
exit "$status"
