#!/bin/bash
# Old-code versus new-code regression (science unchanged); runs on any machine.
#
#   cluster/sitekit/regression.sh OLD_ROOT NEW_ROOT OUT_DIR [PYTHON]
#
# OLD_ROOT and NEW_ROOT are two extracted package trees (for example the pristine
# commit 474487c and the current one). Both run the same small workflows with the
# same interpreter: validate, analyze, analyze-recorded, demo and the N=12 cluster
# smoke task (prepare-grid + run with the shared-cache path). The outputs are then
# compared old-vs-new (must be identical apart from timing/timestamp keys) and
# new-vs-shipped results/ (reported; bit identity across machines is not assumed).
# Small and serial: about two minutes on one core. No environment variables needed.
set -o pipefail
if [[ $# -lt 3 ]]; then
    echo "usage: $0 OLD_ROOT NEW_ROOT OUT_DIR [PYTHON]" >&2
    exit 64
fi
OLD=$(cd "$1" && pwd) || exit 64
NEW=$(cd "$2" && pwd) || exit 64
# A fresh report directory per invocation: stale reports must never satisfy the checks.
if [[ -e "$3" && -n "$(ls -A "$3" 2>/dev/null)" ]]; then
    echo "OUT_DIR $3 exists and is not empty; use a new directory" >&2
    exit 64
fi
mkdir -p "$3" || exit 73
OUT=$(cd "$3" && pwd)
PY=${4:-python3}
COMPARE="$NEW/cluster/sitekit/compare.py"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset LRI_TAIL_CUTOFF LRI_WORKERS LRI_FFT_WORKERS

status=0
run_side() {   # run_side LABEL ROOT
    local label=$1 root=$2 cmd
    for cmd in validate analyze analyze-recorded demo; do
        echo "== $label: run.py $cmd"
        (cd "$root" && "$PY" scripts/run.py "$cmd" --output "$OUT/$label/$cmd") \
            > "$OUT/$label/$cmd.log" 2>&1 || { echo "FAILED $label $cmd (see $OUT/$label/$cmd.log)"; status=1; }
    done
    echo "== $label: cluster smoke (N=12 prepare-grid + run, shared-cache path)"
    (cd "$root" && "$PY" cluster/run_task.py prepare-grid --cutoff 12 --oversample 3 --radius-cost 4 \
            --cache-root "$OUT/$label/smoke_cache" --workers 1 &&
     "$PY" cluster/run_task.py run --plan cluster/smoke_plan.json --task-index 0 \
            --work-root "$OUT/$label/smoke_work" --output-root "$OUT/$label/smoke_out" \
            --coefficient-cache "$OUT/$label/smoke_cache" --workers 1) \
        > "$OUT/$label/cluster_smoke.log" 2>&1 || { echo "FAILED $label cluster smoke"; status=1; }
    mkdir -p "$OUT/$label/cluster_smoke"
    cp "$OUT/$label"/smoke_out/smoke_*/cluster_k*_N12.json "$OUT/$label/cluster_smoke/" 2>/dev/null
}
mkdir -p "$OUT/old" "$OUT/new"
run_side old "$OLD"
run_side new "$NEW"

compare() {   # compare TAG A B; a failing comparison (e.g. unreadable output) fails the regression
    if ! "$PY" "$COMPARE" outputs "$2" "$3" --out "$OUT/compare_$1.json" > "$OUT/compare_$1.txt" 2>&1; then
        echo "FAILED comparison $1 (see $OUT/compare_$1.txt)"
        status=1
    fi
    sed "s/^/[$1] /" "$OUT/compare_$1.txt"
}
OLD_VS_NEW=(validate analyze analyze-recorded demo cluster_smoke)
for cmd in "${OLD_VS_NEW[@]}"; do
    compare "old_vs_new_$cmd" "$OUT/old/$cmd" "$OUT/new/$cmd"
done
# Shipped records (produced on another Linux machine; reported, not required to be identical).
compare shipped_validation "$NEW/results/validation" "$OUT/new/validate"
compare shipped_hamiltonian "$NEW/results/hamiltonian" "$OUT/new/analyze"
compare shipped_hamiltonian_recorded "$NEW/results/hamiltonian_recorded" "$OUT/new/analyze-recorded"
compare shipped_demo "$NEW/results/demo" "$OUT/new/demo"
compare shipped_cluster_smoke "$(ls -d "$NEW"/results/revision/cluster_smoke/smoke_* | head -1)" "$OUT/new/cluster_smoke"

# Summary: every expected report must exist; all old-vs-new reports must be identical;
# any failed run or comparison fails the regression.
"$PY" "$COMPARE" regression-summary "$OUT" --old "$OLD" --new "$NEW" --python "$PY" --runs-status "$status" \
    --expect-old-vs-new "${OLD_VS_NEW[@]}" \
    --expect-shipped validation hamiltonian hamiltonian_recorded demo cluster_smoke
