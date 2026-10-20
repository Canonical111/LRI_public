#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Final J-VAL-4 on symmetry, second attempt (the first, 570030, stopped in tests/sanitize.py --selftest: the
# _GLIBCXX_ASSERTIONS probe aborted with SIGABRT but GCC 11.4's libstdc++ prints its report on stdout, which the piped
# run loses; see s5val4_selftest.py). Here: (1) tests/sanitize.py WITHOUT --selftest (A-KER-4: the 144 worker runs and
# the point checks with the sanitizer builds of s5build, must all be clean); (2) s5val4_selftest.py, the same three
# probes built with sanitize.py's own command, each run piped and under a pty. make -q finds the sanitizer builds current.
# Usage: C8_PACKAGE=... SELFTEST=<s5val4_selftest.py> sbatch --export=ALL -J c8d2-s5val4b s5val4b.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SELFTEST:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val4b.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" "$SELFTEST" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
make -q bin/c8d2_decimal_san bin/c8d2_gmp_san; q=$?; echo "make -q bin/c8d2_{decimal,gmp}_san exit $q (0 = current)" | tee "$E/make_q_sanitize.txt"; [ $q -eq 0 ] || { echo "sanitizer builds not current" >&2; exit 3; }
sha256sum bin/c8d2_decimal_san bin/c8d2_gmp_san | tee "$E/binaries.sha256"
status=0; t=$(date +%s)
python3 -B tests/sanitize.py --output "$E/sanitize.json" > "$E/sanitize.stdout" 2>&1 || { echo "sanitize FAILED"; tail -40 "$E/sanitize.stdout"; status=1; }
echo "sanitize.py (no --selftest) after $(( $(date +%s) - t )) s"; tail -2 "$E/sanitize.stdout" | cut -c1-600
python3 -B "$SELFTEST" "$C8_PACKAGE" "$E/selftest_gcc11.json" > "$E/selftest.stdout" 2>&1 || { echo "self-test helper FAILED"; status=1; }
cat "$E/selftest.stdout" | cut -c1-400
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
