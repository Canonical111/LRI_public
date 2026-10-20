#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=8G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r4a-trace
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, R4a development: the mpf call-sequence evidence again with the corrected tracer classes (get_prec, the
# precision query of Boost's copy constructor and copy assignment, counted with the copies), on the executables built by
# expanse_r4a_build.slurm in another export (C8_BINS: its bin/ with bin/baseline/). The tracer and r4a_trace.py come from
# this job's own export (C8_PACKAGE); the two L8 packs are hard-linked into it for staging (each member is checked
# against its inventory sha256). The executables' sha256 must be the build job's: R4a gmp 2fab1328..., ratiohist
# 6edf48d5...; baseline gmp 5c5328af..., ratiohist c307f2a3....
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_BINS=$C8_DATA/pkg/<built sha12>/bin C8_L8_PACKS=<dir> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_BINS:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4atrace.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; executables $C8_BINS; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
cd "$C8_PACKAGE"
test ! -e bin
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
sha256sum "$C8_BINS/c8d2_gmp" "$C8_BINS/c8d2_gmp_ratiohist" "$C8_BINS/baseline/c8d2_gmp" "$C8_BINS/baseline/c8d2_gmp_ratiohist" | tee "$E/binaries.sha256"
python3 - "$E/binaries.sha256" <<'PY'
import sys
want = {'2fab13288efb3ad9a0ee781ccd43cd014de0b16b702e26345d8a34479f08600c', '6edf48d580f846fc71e9e7e21e5aec2564cf5a3bf236dcfb27ef924b98f724ef',
        '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3', 'c307f2a314a67fea489d85073325edf12e4521ac08772789ecf7626f37326ecf'}
got = {l.split()[0] for l in open(sys.argv[1])}
sys.exit(0 if got == want else 3)
PY
mkdir -p bin/dev
D=benchmarks/expanse_2026-10-c8/stage4b/dev_r4a
gcc -O2 -fPIC -shared "$D/mpf_trace.c" -o bin/dev/mpf_trace.so -I"$C8_GMP/include" -ldl -lpthread
sha256sum bin/dev/mpf_trace.so | tee "$E/dev_binaries.sha256"
status=0
python3 -B "$D/r4a_trace.py" --base "$C8_BINS/baseline" --new "$C8_BINS" --shim bin/dev/mpf_trace.so --output "$E/trace" --scratch "$TMPDIR" > "$E/trace.stdout" 2>&1 || status=$?
echo "r4a_trace exit $status"; grep -E '^(PASS|FAIL)' "$E/trace.stdout" || tail -20 "$E/trace.stdout"
rm -f inputs/packs/free_L8.pack inputs/packs/power_L8.pack
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
