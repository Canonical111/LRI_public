#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:40:00 --no-requeue
#SBATCH -J c8d2-r3a-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R3a, development (wf_f7916ef0-f06): the builds every R3a job reads, in the git-archive export of the commit
# under test. The two L8 packs are hard-linked from C8_L8_PACKS (make re-hashes every pack against inputs/manifest.json).
# Builds: make (decimal + inputs), make gmp, make profile (the tier-timer diagnostic, for the speed job's phase 3),
# make quaddiff (bin/c8d2_quad_differential, bin/c8d2_quad_ranges), make inspect, make c7ref (validate.py's replay).
# Then (1) the baseline: the Stage-3 binaries of the 4a export (decimal 3dbd51bb..., gmp 5c5328af...) are copied to
# $C8_PACKAGE/baseline/ and checked; (2) asm_compare.py: the worker's translation unit of both backends compiled to
# assembly from the 4a export's src/ and from this export's src/ with the Makefile's flags, function by function.
# Exit 3 when a build fails or the baseline hashes differ (the afterok jobs then never start).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir with the pinned L8 packs> sbatch --export=ALL r3a_build.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r3abuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
test ! -e bin && test ! -e build && test ! -e baseline
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
BP=$C8_DATA/pkg/c17688158e2b
t0=$(date +%s)
make -j16 2>&1 | tee "$E/make_all.log" | tail -3
make -j16 gmp 2>&1 | tee "$E/make_gmp.log" | tail -3
make -j16 profile quaddiff inspect 2>&1 | tee "$E/make_extra.log" | tail -3
make c7ref > "$E/make_c7ref.log" 2>&1; tail -2 "$E/make_c7ref.log"
echo "builds in $(( $(date +%s) - t0 )) s"
mkdir baseline; cp "$BP/bin/c8d2_decimal" "$BP/bin/c8d2_gmp" baseline/
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp baseline/c8d2_decimal baseline/c8d2_gmp | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_quad_differential.build.txt bin/c8d2_quad_ranges.build.txt bin/ref/c7d2_decimal.build.json bin/ref/c7d2_gmp.build.json "$E/build_records/"
F="-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math"; A=$TMPDIR/asm; mkdir -p "$A"
g++ $F -S "$BP/src/c8d2_integrate.cpp" -o "$A/base_decimal.s" & g++ $F -DC8_USE_GMP -S "$BP/src/c8d2_integrate.cpp" -o "$A/base_gmp.s" &
g++ $F -S src/c8d2_integrate.cpp -o "$A/new_decimal.s" & g++ $F -DC8_USE_GMP -S src/c8d2_integrate.cpp -o "$A/new_gmp.s" & wait
for b in decimal gmp; do python3 benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts/asm_compare.py "$A/base_$b.s" "$A/new_$b.s" --output "$E/asm_compare_$b.json" | head -40; done
python3 - "$E" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
want = {'baseline/c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
        'baseline/c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3'}
got = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['baseline/c8d2_decimal', 'baseline/c8d2_gmp', 'bin/c8d2_decimal', 'bin/c8d2_gmp']}
rec = {'baseline_expected': want, 'sha256': got, 'baseline_ok': all(got[p] == h for p, h in want.items()),
       'candidate_differs_from_baseline': got['bin/c8d2_gmp'] != got['baseline/c8d2_gmp'] and got['bin/c8d2_decimal'] != got['baseline/c8d2_decimal']}
(E / 'binaries_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1))
sys.exit(0 if rec['baseline_ok'] else 3)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is)"
