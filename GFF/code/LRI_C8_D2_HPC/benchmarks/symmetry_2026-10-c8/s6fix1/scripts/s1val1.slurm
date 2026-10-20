#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-VAL-1 on symmetry after Stage-6 fix round 1 (PLAN job table: template, -t 02:00:00; a whole amdq node), in the
# export of the merged head built by s1build.slurm (template: stage5/fix/scripts/fxval1.slurm, unchanged steps):
#   1. tests/check_venv.py --strict;
#   2. `make test OUTPUT=<evidence>/test`, literally, as ONE command (validate subset, test-python: check_venv,
#      unit_orchestration (X8 runtime_identity with the real ldd and library hashes on Linux; X9, X10, X11, X12, X13,
#      X21 and every earlier group), test_pipeline (X1, X10, X14, X15), ast_scan (tools/*.py, then gen/*.py and tests/*.py),
#      test_regress and test_handoff_inventory (X5), merge_scale, check_vendored (X7), vendored_isolated --in-place,
#      the delivery-verifier test (X20, the symlinked-directory case), check_inputs (X4), test_profiling,
#      test_gmp_prefix, test_numerics_flags (X1, X2, X3 with fakes), test_dd_profile, sanitize --capture-check; then
#      workflow and staging); it must exit 0;
#   3. tests/assembly_checks.py --exact, tests/verify_result_tamper.py (X16) and tests/compat_2026.py;
#   4. the executables are unchanged by make (sha256 before and after).
# Temporary package copies and campaigns on the node-local /tmp (TMPDIR). C8_SEEDS/C8_SITE/C8_INPUTS unset (the tests
# make their own).
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s1build> -J c8d2-s1val1 s1val1.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s1val1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"; python3 --version; python3 -c 'import numpy;print("numpy",numpy.__version__)'
python3 -m pip freeze > "$E/pip_freeze.txt" 2>&1
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
status=0
run() {
  local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "== $name exit $c after $(( $(date +%s) - t )) s"; echo "$name $c $(( $(date +%s) - t ))" >> "$E/exits.txt"; tail -3 "$E/$name.log" | cut -c1-300
  if [ $c -ne 0 ]; then status=1; grep -E '^FAIL|Error|Traceback|failed' "$E/$name.log" | head -30 | cut -c1-300; fi
}
run check_venv_strict python3 -B tests/check_venv.py --strict --output "$E/check_venv_strict.json"
run make_test make test OUTPUT="$E/test"
grep -E '^(PASS|FAIL)|"status"|passed|FAILED' "$E/make_test.log" | grep -v '^PASS' | cut -c1-200 | tail -40
run assembly_checks python3 -B tests/assembly_checks.py --exact --output "$E/assembly_checks.json"
run verify_result_tamper python3 -B tests/verify_result_tamper.py --output "$E/verify_result_tamper.json"
run compat_2026 python3 -B tests/compat_2026.py --output "$E/compat_2026.json"
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=1; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
