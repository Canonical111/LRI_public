#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-int-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b integration (branch c8; Expanse, site deviation U1): build one cumulative step in the git-archive export of
# its commit (C8_PACKAGE) and run the A-RPL-1/2/3 subset there.
#   1. The two L8 packs hard-linked from C8_L8_PACKS (make re-hashes every pack against inputs/manifest.json); make,
#      make gmp inspect, make profile ratiohist, make c7ref, and make quaddiff where the Makefile has it (R3a onwards).
#   2. bin/baseline/c8d2_{decimal,gmp}: byte copies of the Stage-3 baseline (C8_BASELINE_BIN; tag c8-stage3 build,
#      sha256 3dbd51bb... and 5c5328af..., checked), the A-RPL-7 reference of the later gate jobs.
#   3. tests/validate.py default parts (describe, refusals, the replay subset of A-RPL-1/2/3, invariance, inspector with
#      the order-trace build, class B, diagnostics) at 4 jobs x 4 threads.
#   With INT_VARIANTS=1 (the R4f step, the export of the commit that holds the GMP_PREFIX knob) also, after the builds
#   of INT_S2 and INT_S3 (their exports, already built: sbatch --dependency=afterok):
#   4. bin/c8d2_{decimal,gmp} must be byte-identical to INT_S3's (the R4f merge leaves the default build unchanged);
#   5. the GMP_PREFIX builds against ~/c8d2/opt/gmp-6.2.1-zen2 (R4f's host-tuned GMP 6.2.1, libgmp sha256 4267ffeb...):
#      $C8_DATA/work/<sha12>/int-zen2-S3src (this export's src: +R5 +R3a +R4a) and int-zen2-S2src (INT_S2's src: +R5
#      +R3a, the candidate if R4a is reverted), each from this export's Makefile and build-record tools; a default
#      build of int-default-S2src must equal INT_S2's bin/c8d2_gmp byte for byte; ldd must resolve libgmp to the prefix;
#   With INT_FINAL_ZEN2=1 (the final candidate, if R4f is kept): $C8_DATA/work/<sha12>/int-zen2-final, this export's src
#      built with GMP_PREFIX=zen2, ldd checked.
#   6. optionally INT_SMOKE=1: a smoke run of int_speed.py (2 binaries, 4 graphs per sector, fake topology, no pinning;
#      never a measurement) to catch script errors before the node job.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir> [C8_BASELINE_BIN=<dir>] [INT_VARIANTS=1 INT_S2=<export>
#        INT_S3=<export>] [INT_SMOKE=1] sbatch --export=ALL [--dependency=afterok:...] int_build.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
BASE=${C8_BASELINE_BIN:-$C8_DATA/pkg/c17688158e2b/bin}
S3DEC=3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a; S3GMP=5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3
ZEN2=$HOME/c8d2/opt/gmp-6.2.1-zen2; ZEN2LIB=4267ffeb5e20d1ee2a27e3b3afd51c9b4733125a7cf57554349c23df81ea3ee2
TAG=$(basename "$C8_PACKAGE"); RUN=intbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; baseline $BASE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
QD=""; grep -q '^quaddiff:' Makefile && QD=quaddiff
{ make -j16 && make -j16 gmp inspect && make -j16 profile ratiohist && make c7ref && { [ -z "$QD" ] || make -j16 quaddiff; }; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s (quaddiff: ${QD:-not in this commit})"
mkdir bin/baseline && cp -p "$BASE/c8d2_decimal" "$BASE/c8d2_gmp" bin/baseline/ || exit 3
[ "$(sha256sum bin/baseline/c8d2_decimal | cut -c1-64)" = $S3DEC ] && [ "$(sha256sum bin/baseline/c8d2_gmp | cut -c1-64)" = $S3GMP ] || { echo "bin/baseline is not the Stage-3 build" >&2; exit 3; }
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp"
[ -n "$QD" ] && X="$X bin/c8d2_quad_differential bin/c8d2_quad_ranges"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.log" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/$name.log" | cut -c1-300; [ $c -eq 0 ] || status=1; }
run validate python3 -B tests/validate.py --jobs 4 --threads 4 --output "$E/validate.json"
if [ "${INT_VARIANTS:-0}" = 1 ]; then
  : "${INT_S2:?}" "${INT_S3:?}"
  python3 - "$E" "$INT_S3" <<'PY' || status=1
import hashlib, json, sys
from pathlib import Path
E, S3 = Path(sys.argv[1]), Path(sys.argv[2]); h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rec = {k: {'this': h(f'bin/{k}'), 'S3': h(S3 / 'bin' / k)} for k in ('c8d2_decimal', 'c8d2_gmp', 'c8d2_gmp_prof', 'c8d2_gmp_ratiohist')}
rec = {'S3_export': str(S3), 'binaries': rec, 'identical': all(v['this'] == v['S3'] for v in rec.values()),
       'rule': 'the R4f merge (GMP_PREFIX knob, build-record fields) leaves the default build byte-identical'}
(E / 'default_vs_S3.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['identical'] else 3)
PY
  [ "$(sha256sum "$(readlink -f "$ZEN2/lib/libgmp.so.10")" | cut -c1-64)" = $ZEN2LIB ] || { echo "$ZEN2 is not R4f's zen2 GMP" >&2; exit 3; }
  W=$C8_DATA/work/$TAG
  mk() {  # mk <dir> <src dir> <GMP_PREFIX or ->: this export's Makefile and build-record tools with <src dir>'s src/
    local d=$1 src=$2 gp=$3; test ! -e "$d" || { echo "$d exists; refusing" >&2; return 65; }
    mkdir -p "$d/tools" && cp -R "$src/src" "$d/src" && cp Makefile "$d/" && cp tools/build_record.py tools/common.py "$d/tools/" || return 3
    diff -r "$src/src" "$d/src" > /dev/null || { echo "$d/src differs from $src/src" >&2; return 3; }
    if [ "$gp" = - ]; then make -C "$d" -j2 bin/c8d2_gmp > "$d/make.log" 2>&1; else make -C "$d" -j3 bin/c8d2_gmp bin/c8d2_gmp_prof GMP_PREFIX="$gp" > "$d/make.log" 2>&1; fi
  }
  mk "$W/int-zen2-S3src" "$C8_PACKAGE" "$ZEN2" || { echo "zen2 S3src build FAILED"; status=1; }
  mk "$W/int-zen2-S2src" "$INT_S2" "$ZEN2" || { echo "zen2 S2src build FAILED"; status=1; }
  mk "$W/int-default-S2src" "$INT_S2" - || { echo "default S2src build FAILED"; status=1; }
  for d in int-zen2-S3src int-zen2-S2src; do { echo "# $d"; echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; ldd "$W/$d/bin/c8d2_gmp"; readelf -d "$W/$d/bin/c8d2_gmp" | grep -E 'NEEDED|RPATH|RUNPATH'; } >> "$E/ldd_variants.txt"; done
  mkdir -p "$E/variant_build_records"; for d in int-zen2-S3src int-zen2-S2src int-default-S2src; do cp "$W/$d/bin/c8d2_gmp.build.json" "$E/variant_build_records/$d.c8d2_gmp.build.json" 2>/dev/null; cp "$W/$d/make.log" "$E/variant_build_records/$d.make.log" 2>/dev/null; done
  sha256sum "$W"/int-*/bin/c8d2_gmp* 2>/dev/null | grep -v build.json | tee "$E/variants.sha256"
  python3 - "$E" "$W" "$INT_S2" "$ZEN2" <<'PY' || status=1
import hashlib, json, sys
from pathlib import Path
E, W, S2, Z = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
lib = str(Path(Z, 'lib/libgmp.so.10').resolve()); rec = {'zen2_prefix': Z, 'zen2_libgmp': lib, 'zen2_libgmp_sha256': h(lib), 'variants': {}}
for d in ('int-zen2-S3src', 'int-zen2-S2src'):
    br = json.loads((W / d / 'bin/c8d2_gmp.build.json').read_text()); gl = br.get('gmp_library') or {}
    rec['variants'][d] = {'gmp_sha256': h(W / d / 'bin/c8d2_gmp'), 'GMP_PREFIX': br.get('GMP_PREFIX'), 'gmp_library': gl,
                          'resolves_to_prefix': gl.get('realpath') == lib and gl.get('sha256') == h(lib),
                          'rpath_has_prefix': f'{Z}/lib' in (gl.get('rpath') or '').split(':'), 'runpath': gl.get('runpath')}
d = W / 'int-default-S2src/bin/c8d2_gmp'
rec['default_S2src_gmp'] = {'sha256': h(d), 'S2_export_gmp': h(S2 / 'bin/c8d2_gmp'), 'identical': h(d) == h(S2 / 'bin/c8d2_gmp')}
rec['ok'] = rec['default_S2src_gmp']['identical'] and all(v['resolves_to_prefix'] and v['rpath_has_prefix'] and not v['runpath'] for v in rec['variants'].values())
(E / 'variants_check.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['ok'] else 3)
PY
fi
if [ "${INT_FINAL_ZEN2:-0}" = 1 ]; then  # the final candidate's own GMP_PREFIX build (only if R4f is kept as the opt-in knob)
  [ "$(sha256sum "$(readlink -f "$ZEN2/lib/libgmp.so.10")" | cut -c1-64)" = $ZEN2LIB ] || { echo "$ZEN2 is not R4f's zen2 GMP" >&2; exit 3; }
  d=$C8_DATA/work/$TAG/int-zen2-final; test ! -e "$d" || { echo "$d exists; refusing" >&2; exit 65; }
  mkdir -p "$d/tools" && cp -R src "$d/src" && cp Makefile "$d/" && cp tools/build_record.py tools/common.py "$d/tools/" || exit 3
  make -C "$d" -j3 bin/c8d2_gmp bin/c8d2_gmp_prof GMP_PREFIX="$ZEN2" > "$d/make.log" 2>&1 || { echo "zen2 final build FAILED"; tail -20 "$d/make.log"; status=1; }
  { echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; ldd "$d/bin/c8d2_gmp"; readelf -d "$d/bin/c8d2_gmp" | grep -E 'NEEDED|RPATH|RUNPATH'; } > "$E/ldd_final_zen2.txt"
  mkdir -p "$E/variant_build_records"; cp "$d/bin/c8d2_gmp.build.json" "$E/variant_build_records/int-zen2-final.c8d2_gmp.build.json"; cp "$d/make.log" "$E/variant_build_records/int-zen2-final.make.log"
  sha256sum "$d/bin/c8d2_gmp" "$d/bin/c8d2_gmp_prof" | tee "$E/final_zen2.sha256"
  grep -q "libgmp.so.10 => $ZEN2/lib/libgmp.so.10" "$E/ldd_final_zen2.txt" || { echo "the final zen2 worker does not load $ZEN2's libgmp" >&2; status=1; }
fi
if [ "${INT_SMOKE:-0}" = 1 ]; then
  run speed_smoke python3 -B benchmarks/expanse_2026-10-c8/stage4b/integration/scripts/int_speed.py --exe B0=bin/baseline/c8d2_gmp --exe B3=bin/c8d2_gmp \
    --step all=B0:B3 --cost-model benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json --repeats 1 --shape 2x4 \
    --fake-topology 1x2x8 --smoke-sample 4 --output "$E/speed_smoke" --scratch "$TMPDIR"
fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
