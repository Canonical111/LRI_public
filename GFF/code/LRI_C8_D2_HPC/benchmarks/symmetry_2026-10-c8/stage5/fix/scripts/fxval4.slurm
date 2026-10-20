#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-VAL-4 rerun on symmetry after the F4 fix (A-KER-4): `python3 -B tests/sanitize.py --selftest` (the plan's command;
# the self-test probes now run on a pseudo-terminal, so GCC <= 12's _GLIBCXX_ASSERTIONS report on stdout is captured),
# plus `tests/sanitize.py --capture-check`, with the sanitizer executables built by fxbuild.slurm (make -q must find
# them current; nothing is rebuilt here). sharedq (8 CPUs of an Intel node; the sanitizer builds carry no -march
# flag), outside the H7 AMD cap.
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<fxbuild> -J c8d2-fxval4 fxval4.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=fxval4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"; g++ --version | head -1 | tee "$E/gcc.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
make -q bin/c8d2_decimal_san bin/c8d2_gmp_san; q=$?; echo "make -q bin/c8d2_{decimal,gmp}_san exit $q (0 = current)" | tee "$E/make_q_sanitize.txt"; [ $q -eq 0 ] || { echo "sanitizer builds not current; refusing to rebuild here" >&2; exit 3; }
sha256sum bin/c8d2_decimal_san bin/c8d2_gmp_san | tee "$E/binaries.sha256"
status=0; t=$(date +%s)
python3 -B tests/sanitize.py --selftest --output "$E/sanitize.json" > "$E/sanitize.stdout" 2>&1 || { echo "sanitize --selftest FAILED"; tail -40 "$E/sanitize.stdout"; status=1; }
echo "sanitize.py --selftest after $(( $(date +%s) - t )) s"; tail -4 "$E/sanitize.stdout" | cut -c1-600
python3 -B tests/sanitize.py --capture-check --output "$E/sanitize_capture.json" > "$E/sanitize_capture.stdout" 2>&1 || { echo "capture check FAILED"; cat "$E/sanitize_capture.stdout"; status=1; }
tail -2 "$E/sanitize_capture.stdout" | cut -c1-400
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
