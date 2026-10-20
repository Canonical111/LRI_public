#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 04:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Final J-VAL-2 on symmetry (PLAN template, -t 04:00:00): `make test-full OUTPUT=<evidence>/val2` = tests/validate.py
# --full (A-RPL-1/2/3 exact on the L=2 graph and all 3,773 L3-L7 kernels, both backends, against make c7ref),
# tests/check_points.py (450-digit point checks L3-L8 < 1e-280), check_inputs, workflow, staging. The executables come
# from s5build in the same export (built once there; make c7ref is NOT rerun here because it deletes bin/ref while other
# jobs read it); the template's `sha256sum bin/ref/c7d2_decimal bin/ref/c7d2_gmp # expect e696d7f3... and 7e3c8c92...`
# is checked here. Their sha256 are recorded before and after (make must not rebuild them).
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s5build> -J c8d2-s5val2 s5val2.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
c=0
d=$(sha256sum bin/ref/c7d2_decimal | cut -c1-64); g=$(sha256sum bin/ref/c7d2_gmp | cut -c1-64)
if [ "$d" = e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5 ] && [ "$g" = 7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3 ]; then
  echo "c7ref: e696d7f3... and 7e3c8c92... as the plan expects on symmetry" | tee "$E/c7ref_hashes.txt"
else echo "c7ref hashes differ from the plan's: decimal $d gmp $g" | tee "$E/c7ref_hashes.txt"; c=3; fi
t=$(date +%s); echo "== make test-full $(date -Is)"
make test-full OUTPUT="$E/val2" > "$E/make_test_full.log" 2>&1; m=$?
echo "== make test-full exit $m after $(( $(date +%s) - t )) s"; [ $m -eq 0 ] || c=1
grep -E 'passed in|passed|FAILED|Error|error' "$E/make_test_full.log" | cut -c1-300 | head -60
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged by make test-full"; else echo "executables CHANGED during make test-full" >&2; c=3; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $c"
exit $c
