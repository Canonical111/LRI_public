#!/bin/bash
#SBATCH --job-name=lri-c8-d2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=lri-c8-d2-%A_%a.log
# Site options go on the sbatch command line (or in C8_SBATCH_ARGS for slurm/submit.sh), for example:
#   -A <account> -p <partition>          (symmetry: -p amdq or -p defq; Expanse-type: -A <project> -p shared)
# slurm/submit.sh sets --cpus-per-task to the plan's --threads and --time to the plan's suggestion (C8_TIME_POLICY).
# Environment: C8_PACKAGE and C8_RUN (a campaign directory on a SHARED filesystem) are required. Optional:
#   C8_ENV_SETUP     script sourced with errexit on and before nounset (modules + venv; slurm/env.sh.example)
#   C8_PYTHON        interpreter (default python3; >= 3.10)
#   C8_INDEX_OFFSET  added to SLURM_ARRAY_TASK_ID, so plans may exceed MaxArraySize (slurm/submit.sh sets it)
#   C8_STAGE=1       run from a verified node-local copy of the runtime and the group's pack (tools/stage_runtime.py)
#   C8_PACK_CACHE    with C8_STAGE=1, reuse a user-owned node-local pack cache across array elements
#   C8_REVERIFY_PACK_CACHE=1   force a full hash of cache hits (graph members are always hashed before use)
set -eo pipefail # errexit before the setup script: a failing module load or venv activation aborts the job
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u # nounset only after site setup (module and bashrc scripts often reference unset variables)
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
: "${SLURM_ARRAY_TASK_ID:?Submit as a job array}"
[[ "${C8_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C8: C8_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C8_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export OMP_DYNAMIC=FALSE OMP_PLACES="${OMP_PLACES:-cores}" OMP_PROC_BIND="${OMP_PROC_BIND:-close}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
scratch="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
echo "C8: index $index (offset ${C8_INDEX_OFFSET:-0} + array ${SLURM_ARRAY_TASK_ID}) on $(hostname), $OMP_NUM_THREADS threads" >&2
# Cleanup on scancel/timeout: TERM (also INT, HUP) is forwarded to production.py, which stops the native worker and
# removes its job-private runtime, and the optional staging directory is removed here; exit 128+signal. SIGKILL, a node
# failure or an expired Slurm KillWait cannot be cleaned up: such leftovers are named c8d2_runtime_* / c8d2_stage_*.
package="$C8_PACKAGE"; stage=""; child=""
cleanup() { if [[ -n "$stage" ]]; then rm -rf "$stage"; fi; }
on_signal() {
  # Every background job of this script, also one launched just before `child=$!` ran (the launch boundary).
  trap - TERM INT HUP
  local pids; pids="$(jobs -p) $child"
  if [[ -n "${pids// /}" ]]; then kill -TERM $pids 2>/dev/null || true; wait $pids 2>/dev/null || true; fi
  cleanup; exit "$1"
}
trap cleanup EXIT
trap 'on_signal 143' TERM; trap 'on_signal 130' INT; trap 'on_signal 129' HUP
if [[ "${C8_STAGE:-0}" == "1" ]]; then
  stage="$(mktemp -d "${scratch}/c8d2_stage_XXXXXX")"
  stage_args=()
  if [[ -n "${C8_PACK_CACHE:-}" ]]; then stage_args+=(--pack-cache "$C8_PACK_CACHE"); fi
  if [[ "${C8_REVERIFY_PACK_CACHE:-0}" == "1" ]]; then stage_args+=(--reverify-cache); fi
  "$PY" -B "$C8_PACKAGE/tools/stage_runtime.py" "$C8_RUN" "$stage" --index "$index" "${stage_args[@]}" &
  child=$!
  set +e; wait "$child"; status=$?; set -e
  child=""
  if (( status != 0 )); then exit "$status"; fi
  package="$stage"
fi
# Python runs in the batch step (no srun), which holds the whole allocation: OpenMP sees every allocated core. It runs
# in the background so that a trapped signal is handled at once (bash defers traps while a foreground child runs).
"$PY" -B "$package/tools/production.py" run "$C8_RUN" --index "$index" --threads "$OMP_NUM_THREADS" --scratch "$scratch" &
child=$!
set +e; wait "$child"; status=$?; set -e
child=""
exit "$status"
