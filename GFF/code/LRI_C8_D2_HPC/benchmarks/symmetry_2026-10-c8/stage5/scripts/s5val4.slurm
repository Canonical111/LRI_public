#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Final J-VAL-4 on symmetry (A-KER-4): `make sanitize && python3 -B tests/sanitize.py --selftest` with the sanitizer
# executables built by s5build (make -q sanitize must find them current; nothing is rebuilt here). sharedq (8 CPUs of an
# Intel node; the sanitizer builds carry no -march flag), outside the H7 AMD cap.
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s5build> -J c8d2-s5val4 s5val4.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
make -q bin/c8d2_decimal_san bin/c8d2_gmp_san; q=$?; echo "make -q bin/c8d2_{decimal,gmp}_san exit $q (0 = current)" | tee "$E/make_q_sanitize.txt"; [ $q -eq 0 ] || { echo "sanitizer builds not current; refusing to rebuild here" >&2; exit 3; }
sha256sum bin/c8d2_decimal_san bin/c8d2_gmp_san | tee "$E/binaries.sha256"
status=0
python3 -B tests/sanitize.py --selftest --output "$E/sanitize.json" > "$E/sanitize.stdout" 2>&1 || { echo "sanitize FAILED"; tail -40 "$E/sanitize.stdout"; status=1; }
tail -3 "$E/sanitize.stdout" | cut -c1-400
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
