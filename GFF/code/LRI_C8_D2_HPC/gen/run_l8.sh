#!/bin/bash
# gen/run_l8.sh: the J-GEN-2 pipeline (PLAN.md component A): build L7 and L8 in both sectors, run every A-INV-3
# gate, and publish the frozen tree inventory8_d2/ only after the gates have exited 0.
#
# Failure propagation (C8(1) R10/R11/R15): set -euo pipefail; no "|| echo"; every step runs in the foreground, so
# a failing builder, gate or publication stops the script with its status; no process substitution.
#
# Required environment:
#   C8_PACKAGE     git archive export of the generating commit
#   C8_GEN_COMMIT  full commit id of that export (recorded in MANIFEST.json)
#   C8_GEN_BIN     directory holding build_free, build_power, check_edge_forests (make -C gen BIN=...)
#   C8_GEN_STAGE   fresh staging directory (must not exist)
#   C8_GEN_TARGET  publication target .../inventory8_d2 (must not exist; published trees are frozen)
#   C8_GEN_THREADS OpenMP threads of the builders
# Optional: C8_GEN_JOBS (process pool of the gates; default C8_GEN_THREADS), C8_PYTHON (default python3).
# Test hooks, honoured only with C8_GEN_TEST_HOOKS=1 (gen/test_run_l8.py): C8_GEN_BUILD_CMD, C8_GEN_GATES_CMD and
# C8_GEN_PUBLISH_CMD replace the three steps; the x86-64 check is skipped.
set -euo pipefail
: "${C8_PACKAGE:?}" "${C8_GEN_COMMIT:?}" "${C8_GEN_BIN:?}" "${C8_GEN_STAGE:?}" "${C8_GEN_TARGET:?}" "${C8_GEN_THREADS:?}"
# Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*,
# KMP_* from a module or the submitting shell) reaches the generator programs; each gets OMP_NUM_THREADS explicitly.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_DYNAMIC=FALSE
JOBS=${C8_GEN_JOBS:-$C8_GEN_THREADS}
PY=${C8_PYTHON:-python3}
CLASSES="$C8_PACKAGE/reference/c8d1_inputs8"
HOOKS=${C8_GEN_TEST_HOOKS:-0}

stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }

if [ "$HOOKS" != 1 ] && [ "$(uname -m)" != x86_64 ]; then
  echo "refusing: generation runs on x86-64 only (long double printing differs on $(uname -m))" >&2
  exit 64
fi
if [ -e "$C8_GEN_STAGE" ]; then echo "refusing: $C8_GEN_STAGE exists (use a fresh stage)" >&2; exit 64; fi
if [ -e "$C8_GEN_TARGET" ]; then echo "refusing: $C8_GEN_TARGET exists (published trees are frozen)" >&2; exit 64; fi
mkdir "$C8_GEN_STAGE"

step_build() {
  local L sector t0
  for L in 7 8; do
    for sector in free power; do
      t0=$(date +%s)
      OMP_NUM_THREADS=$C8_GEN_THREADS "$C8_GEN_BIN/build_$sector" "$CLASSES/classes$L.txt" \
        "$C8_GEN_STAGE/L${L}_$sector" "$C8_GEN_STAGE/L${L}_$sector.subgraphs.txt"
      stamp "built L$L $sector in $(( $(date +%s) - t0 )) s"
    done
  done
}
step_gates() {
  "$PY" -B "$C8_PACKAGE/gen/gates.py" --stage "$C8_GEN_STAGE" --bin "$C8_GEN_BIN" --jobs "$JOBS"
}
step_publish() {
  "$PY" -B "$C8_PACKAGE/gen/publish_inventory.py" build --stage "$C8_GEN_STAGE" --target "$C8_GEN_TARGET" \
    --package "$C8_PACKAGE" --bin "$C8_GEN_BIN" --commit "$C8_GEN_COMMIT"
}
run_step() {  # run_step NAME FUNCTION HOOKVAR
  local cmd=""
  if [ "$HOOKS" = 1 ]; then cmd=${!3:-}; fi
  stamp "step $1: start"
  if [ -n "$cmd" ]; then bash -c "$cmd"; else "$2"; fi
  stamp "step $1: exit 0"
}

run_step build step_build C8_GEN_BUILD_CMD
run_step gates step_gates C8_GEN_GATES_CMD
run_step publish step_publish C8_GEN_PUBLISH_CMD
stamp "published $C8_GEN_TARGET"
