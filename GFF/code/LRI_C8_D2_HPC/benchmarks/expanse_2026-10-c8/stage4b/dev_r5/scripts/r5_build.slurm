#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-r5-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R5a/R5b development (branch opt-r5; Expanse, site deviation U1): the native executables built in the export
# of the commit under test (make, make gmp inspect, make profile ratiohist, make c7ref), the two L8 packs hard-linked
# from an earlier export (make re-hashes every pack against inputs/manifest.json). R5a changes src/c8d2_integrate.cpp, so
# bin/c8d2_{decimal,gmp} are expected to DIFFER from the Stage-3 builds (3dbd51bb..., 5c5328af...): their hashes are
# recorded, and exactness is shown by the gates, not by the hashes. Then, on this job's 16 CPUs:
#   - tests/validate.py default parts (describe, bad_inputs, the replay subset of A-RPL-1/2/3, invariance, inspector with
#     the order-trace build, class_b, diagnostics);
#   - r5a_first_error.py against the Stage-3 baseline binaries in C8_BASELINE_BIN (hashes checked): the parallel
#     loading reports the serial loading's first error at 1-16 threads, and loads valid blocks identically.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir with the pinned L8 packs> [C8_BASELINE_BIN=<dir>] sbatch --export=ALL ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
BASE=${C8_BASELINE_BIN:-$C8_DATA/pkg/c17688158e2b/bin}
TAG=$(basename "$C8_PACKAGE"); RUN=r5build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; baseline $BASE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
{ make -j16 && make -j16 gmp inspect && make -j16 profile ratiohist && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"; grep -E 'Error|error:' "$E/make.log" | head
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp | tee "$E/binaries.sha256"
sha256sum "$BASE/c8d2_decimal" "$BASE/c8d2_gmp" | tee "$E/baseline.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
python3 - "$E" "$BASE" <<'PY'
import hashlib, json, sys
from pathlib import Path
E, B = Path(sys.argv[1]), Path(sys.argv[2])
stage3 = {'c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3'}
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rec = {'stage3': stage3, 'baseline_dir': str(B), 'baseline_now': {k: h(B / k) for k in stage3},
       'candidate': {k: h(Path('bin') / k) for k in stage3}}
rec['baseline_is_stage3'] = rec['baseline_now'] == stage3
rec['candidate_equals_stage3'] = {k: rec['candidate'][k] == v for k, v in stage3.items()}
rec['note'] = ('R5a changes src/c8d2_integrate.cpp (parallel graph loading), so the candidate hashes are expected to differ '
               'from Stage 3; exactness comes from the row comparisons (G-L8SELF, thread identity, the P4 rows digest).')
(E / 'binaries_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1))
sys.exit(0 if rec['baseline_is_stage3'] else 3)
PY
[ $? -eq 0 ] || { echo "the baseline directory does not hold the Stage-3 binaries"; exit 3; }
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.log" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/$name.log" | cut -c1-300; [ $c -eq 0 ] || status=1; }
run validate python3 -B tests/validate.py --jobs 4 --threads 4 --output "$E/validate.json"
run first_error python3 -B benchmarks/expanse_2026-10-c8/stage4b/dev_r5/scripts/r5a_first_error.py --baseline "$BASE" --output "$E/first_error.json"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
