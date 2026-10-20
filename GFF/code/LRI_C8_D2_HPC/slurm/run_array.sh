#!/bin/bash
#SBATCH --job-name=c8d2-array
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=c8d2-array-%A_%a.log
# One array element = one job index of a planned C8(2) campaign. Submit with slurm/submit.sh, which sets the plan's
# threads (--cpus-per-task), the plan's memory suggestion (--mem; a smaller user value is refused), the suggested time,
# the index offset, the job name and the campaign tag. Site options go in C8_SBATCH_ARGS, e.g.
#   symmetry: C8_SBATCH_ARGS="-p amdq --exclude=cn112"     Expanse: C8_SBATCH_ARGS="-A yun124 -p shared"
# Environment: C8_PACKAGE and C8_RUN (a campaign directory on a SHARED filesystem) are required. Optional:
#   C8_ENV_SETUP     script sourced with errexit on and before nounset (modules + venv; slurm/env.sh.example)
#   C8_PYTHON        interpreter (default python3; >= 3.10)
#   C8_INDEX_OFFSET  added to SLURM_ARRAY_TASK_ID, so plans may exceed MaxArraySize (slurm/submit.sh sets it)
#   C8_STAGE=1       run from a verified node-local copy of the runtime and of the index's pack members (tools/stage_runtime.py)
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts the job
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u # nounset only after site setup (module and bashrc scripts often reference unset variables)
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
: "${SLURM_ARRAY_TASK_ID:?Submit as a job array (slurm/submit.sh)}"
[[ "${C8_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C8: C8_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C8_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
# Y2: no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*, KMP_* from a module or the submitting
# shell) reaches the claim; production.py run gives its native worker the same controlled environment
# (common.omp_child_env) and watches the worker's team in any case.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
scratch="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
echo "C8: index $index (offset ${C8_INDEX_OFFSET:-0} + array ${SLURM_ARRAY_TASK_ID}) on $(hostname), $OMP_NUM_THREADS threads" >&2
# Cleanup on scancel/timeout: TERM (also INT, HUP) is forwarded to production.py, which stops the native worker and
# removes its job-private runtime; the optional staging directory is removed here; exit 128+signal. SIGKILL, a node
# failure or an expired Slurm KillWait cannot be cleaned up: such leftovers are named c8d2_runtime_* / c8d2_stage_*.
package="$C8_PACKAGE"; stage=""; child=""
cleanup() { if [[ -n "$stage" ]]; then rm -rf "$stage"; fi; }
on_signal() {
  # Every background job of this script, also one launched just before `child=$!` ran (the launch boundary). It gets
  # TERM and up to 30 s to stop its native worker and remove its runtime, then KILL: the wait is never unbounded.
  # TERM is sent again every 0.5 s while the job runs: a TERM that reaches the job between its fork and the exec of
  # Python, while it is still a copy of this shell, can be lost (seen with bash 3.2 under load, where it left the job
  # running until the KILL and its runtime behind). production.py ignores a repeated TERM once it is stopping.
  trap - TERM INT HUP
  local pids x n live=""; pids="$(jobs -p) $child"
  if [[ -n "${pids// /}" ]]; then
    kill -TERM $pids 2>/dev/null || true
    for n in $(seq 1 60); do
      live=""; for x in $pids; do if kill -0 "$x" 2>/dev/null; then live="$live $x"; fi; done
      [[ -z "$live" ]] && break; sleep 0.5
      kill -TERM $live 2>/dev/null || true
    done
    if [[ -n "$live" ]]; then echo "C8: still running after 30 s, killed:$live" >&2; kill -KILL $live 2>/dev/null || true; fi
    wait $pids 2>/dev/null || true
  fi
  cleanup; exit "$1"
}
trap cleanup EXIT
trap 'on_signal 143' TERM; trap 'on_signal 130' INT; trap 'on_signal 129' HUP
if [[ "${C8_STAGE:-0}" == "1" ]]; then
  stage="$(mktemp -d "${scratch}/c8d2_stage_XXXXXX")"
  "$PY" -B "$C8_PACKAGE/tools/stage_runtime.py" "$C8_RUN" "$stage" --index "$index"
  package="$stage"
fi
# Python runs in the batch step (no srun), which holds the whole allocation: OpenMP sees every allocated core. It runs
# in the background so that a trapped signal is handled at once (bash defers traps while a foreground child runs).
"$PY" -B "$package/tools/production.py" run "$C8_RUN" --index "$index" --threads "$OMP_NUM_THREADS" --scratch "$scratch" &
child=$!
set +e; wait "$child"; status=$?; set -e
child=""
exit "$status"
