#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:20:00 --no-requeue
#SBATCH -J c8d2-s5e-exp1c
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5 on Expanse: check of the proposed one-line fix for J-EXP-1's second test failure (diagnosed by job 54676921).
# tests/test_numerics_flags.py, group f2_profile, passes C8_FAKE_PROFILE_DELTA=repr(delta) where delta is a numpy
# float64; under NumPy >= 2 (Expanse venv 2.3.5) repr gives 'np.float64(...)', which the fake profile executable cannot
# parse, so the 'dse' run writes no record. On the Mac (NumPy 1.23.5) repr gives the bare number. This job copies the
# export (no bin/, build/ or L8 packs; fakes only) to node-local scratch, applies repr(delta) -> repr(float(delta)) in
# the COPY only (nothing in the package changes), and runs the whole tests/test_numerics_flags.py there.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL s5e_exp1c.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s5eexp1c.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; nproc $(nproc)"
python3 -c "import numpy;print('numpy',numpy.__version__,repr(numpy.float64(0.5)))"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch" >&2; exit 69; }
export TMPDIR=$L/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
P=$L/pkg; mkdir "$P"
( cd "$C8_PACKAGE" && tar --exclude=./bin --exclude=./build --exclude=./inputs/packs/free_L8.pack --exclude=./inputs/packs/power_L8.pack -cf - . ) | tar -C "$P" -xf -
cd "$P" || exit 64
grep -c 'repr(delta)' tests/test_numerics_flags.py
sed -i 's/repr(delta)/repr(float(delta))/' tests/test_numerics_flags.py
diff <(cd "$C8_PACKAGE" && cat tests/test_numerics_flags.py) tests/test_numerics_flags.py > "$E/patch.diff"; cat "$E/patch.diff"
python3 -B tests/test_numerics_flags.py --output "$E/test_numerics_flags_patched.json" > "$E/test_numerics_flags_patched.log" 2>&1; c=$?
echo "patched test_numerics_flags exit $c"; grep -E '^PASS|^FAIL|"passed"' "$E/test_numerics_flags_patched.log" | cut -c1-200
cd /; rm -rf "$P" "$TMPDIR"; echo "finished $(date -Is), exit $c"; exit $c
