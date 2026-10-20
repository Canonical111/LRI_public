#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Final J-VAL-1 on symmetry (PLAN job table: template, -t 02:00:00) in the export of the final commit: the commands of
# `make test` one by one, each to the end with its own record and exit code: make all gmp (input verification; the
# executables of s5build must be current: their sha256 are recorded before and after), tests/validate.py (replay
# subset, native refusals, invariance, inspector, class B, diagnostics), the `make test-python` list (unit_orchestration
# with the A-ORC-13 claim on the real bin/c8d2_gmp on the Linux fingerprint path and the R18 bootstrap regeneration in
# a copy of this export; test_pipeline, ast_scan, test_regress, merge_scale --rows 20000, check_vendored
# --no-review-record, vendored_isolated --in-place (A-ASM-1 cluster part), the delivery-verifier test, check_inputs,
# test_profiling, test_gmp_prefix, test_numerics_flags, test_dd_profile), then the real-worker workflow.py and staging.py.
# Temporary package copies and campaigns on the node-local /tmp (TMPDIR). C8_SEEDS/C8_SITE/C8_INPUTS unset (the tests
# make their own).
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s5build> -J c8d2-s5val1 s5val1.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64; R=$E/records; mkdir "$R"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"; python3 --version
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
status=0
run() {
  local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -2 "$E/$name.log" | cut -c1-300
  if [ $c -ne 0 ]; then status=1; grep -E '^FAIL|Error|Traceback' "$E/$name.log" | head -20 | cut -c1-300; fi
}
run make_prerequisites make all gmp
run validate python3 -B tests/validate.py --output "$R/validate.json"
run unit_orchestration python3 -B tests/unit_orchestration.py --output "$R/unit_orchestration.json"
run test_pipeline python3 -B tests/test_pipeline.py --output "$R/test_pipeline.json"
run ast_scan python3 -B tests/ast_scan.py --output "$R/ast_scan.json"
run test_regress python3 -B gen/test_regress.py --output "$R/test_regress.json"
run merge_scale python3 -B tests/merge_scale.py --rows 20000 --output "$R/merge_scale.json"
run check_vendored python3 -B tests/check_vendored.py --no-review-record --output "$R/check_vendored.json"
run vendored_isolated python3 -B tests/vendored_isolated.py --in-place --output "$R/vendored_isolated.json"
run delivery_verifier python3 -B tests/test_delivery_verifier.py
run check_inputs python3 -B tests/check_inputs.py --output "$R/check_inputs.json"
run test_profiling python3 -B tests/test_profiling.py --output "$R/test_profiling.json"
run test_gmp_prefix python3 -B tests/test_gmp_prefix.py --output "$R/test_gmp_prefix.json"
run test_numerics_flags python3 -B tests/test_numerics_flags.py --output "$R/test_numerics_flags.json"
run test_dd_profile python3 -B tests/test_dd_profile.py --output "$R/test_dd_profile.json"
run workflow python3 -B tests/workflow.py --output "$R/workflow.json"
run staging python3 -B tests/staging.py --output "$R/staging.json"
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=1; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
