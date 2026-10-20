#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-r4a-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, R4a development (PLAN "Performance plan"; site deviation U1). In the export of the R4a commit:
#  1. every build (make, make gmp, make profile ratiohist, make inspect, make c7ref), the two L8 packs hard-linked from
#     C8_L8_PACKS (make re-hashes them against inputs/manifest.json); bin/c8d2_decimal must equal the Stage-3 baseline
#     byte for byte (3dbd51bb..., R4a changes only the gmp build); the other hashes are recorded;
#  2. the Stage-3 baseline executables copied from C8_BASELINE_BIN into bin/baseline/ and checked (gmp 5c5328af...,
#     decimal 3dbd51bb..., ratiohist c307f2a3..., prof d1cc6551...), for G-L8SELF and the comparisons;
#  3. the mpf call-sequence evidence: mpf_trace.so (LD_PRELOAD shim) and r4a_trace.py, baseline against R4a, release and
#     ratio-histogram builds, 1 thread (exit 1 of r4a_trace.py fails the job);
#  4. the differential test and MP-tier micro-benchmark r4a_mpdiff (the pre-R4a generic body, R4a, R4a + prefetch;
#     bitwise; shift != 0 points included) on the graphs of the four heavy fixture blocks, 16 threads.
# Staged graphs and scratch stay on node-local /scratch. Expected wall ~20 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir> C8_BASELINE_BIN=<dir> sbatch --export=ALL expanse_r4a_build.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}" "${C8_BASELINE_BIN:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4abuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
test ! -e bin && test ! -e build
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
t0=$(date +%s)
make -j16 2>&1 | tee "$E/make_all.log" | tail -3
make -j16 gmp 2>&1 | tee "$E/make_gmp.log" | tail -3
make -j16 profile ratiohist inspect 2>&1 | tee "$E/make_diag_inspect.log" | tail -3
make c7ref > "$E/make_c7ref.log" 2>&1; tail -2 "$E/make_c7ref.log"
echo "builds in $(( $(date +%s) - t0 )) s"
mkdir bin/baseline bin/dev
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do cp "$C8_BASELINE_BIN/$x" bin/baseline/; done
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/baseline/* | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
python3 - "$E" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
stage3 = {'c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3',
          'c8d2_gmp_prof': 'd1cc6551df116cd106ebf99985cf20035387acaad9ff1fcd77274a0b51de75d7',
          'c8d2_gmp_ratiohist': 'c307f2a314a67fea489d85073325edf12e4521ac08772789ecf7626f37326ecf'}
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rec = {'stage3': stage3, 'baseline_copies': {x: h(f'bin/baseline/{x}') for x in stage3}, 'candidate': {x: h(f'bin/{x}') for x in stage3}}
rec['baseline_copies_ok'] = rec['baseline_copies'] == stage3
rec['decimal_identical_to_stage3'] = rec['candidate']['c8d2_decimal'] == stage3['c8d2_decimal']
rec['gmp_changed'] = {x: rec['candidate'][x] != stage3[x] for x in ('c8d2_gmp', 'c8d2_gmp_prof', 'c8d2_gmp_ratiohist')}
rec['note'] = ('R4a changes only code under #ifdef C8_USE_GMP: the decimal worker must be byte-identical to the '
               'Stage-3 baseline (same node type, Spack GCC 13.3.0, Boost 1.77, GMP 6.2.1); the gmp builds change.')
(E / 'binaries_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
sys.exit(0 if rec['baseline_copies_ok'] and rec['decimal_identical_to_stage3'] else 3)
PY
D=benchmarks/expanse_2026-10-c8/stage4b/dev_r4a
gcc -O2 -fPIC -shared "$D/mpf_trace.c" -o bin/dev/mpf_trace.so -I"$C8_GMP/include" -ldl -lpthread
g++ -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math -DC8_USE_GMP "$D/r4a_mpdiff.cpp" -lquadmath -lgmp -o bin/dev/r4a_mpdiff
sha256sum bin/dev/* | tee "$E/dev_binaries.sha256"
status=0
python3 -B "$D/r4a_trace.py" --base bin/baseline --new bin --shim bin/dev/mpf_trace.so --output "$E/trace" --scratch "$TMPDIR" > "$E/trace.stdout" 2>&1 || status=$?
echo "r4a_trace exit $status"; grep -E '^(PASS|FAIL)' "$E/trace.stdout" || tail -20 "$E/trace.stdout"
# The differential test on every graph of the four heavy fixture blocks (staged from the packs, inventory sha256).
python3 - "$TMPDIR/graphs" > "$TMPDIR/graph_files.txt" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'tools')
import benchkit as bk
from common import load
m = bk.load_fixtures(); I = m['_inputs']; inv = load(I.where('inventory.json'))
for name in ('heavy_power_L8', 'heavy_free_L8', 'heavy_power_L7', 'heavy_free_L7'):
    b = bk.block_of(m, name); g = Path(sys.argv[1]) / name
    bk.stage_graphs(I, inv, b['sector'], b['L'], b['graphs'], g)
    for gid in b['graphs']: print(g / f"L{b['L']}" / f'G{gid}.txt')
PY
echo "$(wc -l < "$TMPDIR/graph_files.txt") graphs staged for r4a_mpdiff"
diff_status=0
OMP_NUM_THREADS=16 OMP_PROC_BIND=close OMP_PLACES=cores bin/dev/r4a_mpdiff "$E/mpdiff.json" 32 4 3 2026100409 .8 $(cat "$TMPDIR/graph_files.txt") > "$E/mpdiff.stdout" 2>&1 || diff_status=$?
echo "r4a_mpdiff exit $diff_status"; tail -3 "$E/mpdiff.stdout"
rm -rf "$TMPDIR"
echo "finished $(date -Is), trace status $status, mpdiff status $diff_status"
[ "$status" = 0 ] && [ "$diff_status" = 0 ]
