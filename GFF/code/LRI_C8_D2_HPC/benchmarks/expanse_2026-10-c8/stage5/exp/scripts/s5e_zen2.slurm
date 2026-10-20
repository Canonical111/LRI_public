#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-s5e-zen2
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5 on Expanse: the gates owed by the opt-in GMP_PREFIX build (Stage 4b R4f; PLAN-REVIEW-LOG "Stage 4b done",
# owed items) before GMP_PREFIX may be used in production on Expanse. One exclusive compute node (2 x EPYC 7742).
# A node-local copy of the built export C8_PACKAGE (everything but bin/ and build/; the L8 packs as symlinks to the
# export's hard links, re-hashed by make) is built with GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2 (R4f's zen2 GMP 6.2.1,
# libgmp 4267ffeb...): make (decimal, no GMP), make gmp, make inspect, make profile ratiohist (the gmp diagnostic
# builds, also against the prefix) and make c7ref (the C7(2) reference, Spack GMP, never GMP_PREFIX). Then:
#   val2             `make test-full GMP_PREFIX=<zen2> OUTPUT=<evidence>/val2`: J-VAL-2 in full (A-RPL-1/2/3 on the L=2
#                    graph and all 3,773 L3-L7 kernels, both backends, gmp = the zen2 worker; chunk/layout invariance;
#                    class B; the diagnostic builds; the 450-digit point checks L3-L8; check_inputs, workflow, staging);
#   bk8              tests/validate.py --bk8 (A-RPL-4): decimal against the zen2 gmp worker, L7 and L8, 400 per sector;
#   forced_tiers     tests/forced_tiers.py (A-RPL-5) with the zen2 worker;
#   vs_default       tests/validate.py --l8self <export>/bin (A-RPL-7's comparison with the DEFAULT final build
#                    1d2a2181... as the reference): the L8 sweep sample, 2,000 kernels x 2 x 512 points, every
#                    scientific field of the zen2 worker exact against the default worker (and decimal against itself).
# The records are compared offline with G4b's records of the default build (stage4b/final; s5e_summary.py).
# Executables' sha256 are recorded before and after; make must not rebuild them.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<J-EXP-1> s5e_zen2.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
ZEN2=$HOME/c8d2/opt/gmp-6.2.1-zen2; ZEN2LIB=4267ffeb5e20d1ee2a27e3b3afd51c9b4733125a7cf57554349c23df81ea3ee2
DEFGMP=1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa; DEFDEC=99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf
TAG=$(basename "$C8_PACKAGE"); RUN=s5ezen2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; zen2 prefix $ZEN2; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"; g++ --version | head -1
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
[ "$(sha256sum "$(readlink -f "$ZEN2/lib/libgmp.so.10")" | cut -c1-64)" = $ZEN2LIB ] || { echo "$ZEN2 is not R4f's zen2 GMP" >&2; exit 3; }
for f in bin/c8d2_decimal bin/c8d2_gmp; do test -x "$C8_PACKAGE/$f" || { echo "missing $C8_PACKAGE/$f (J-EXP-1 builds it)" >&2; exit 69; }; done
[ "$(sha256sum "$C8_PACKAGE/bin/c8d2_gmp" | cut -c1-64)" = $DEFGMP ] && [ "$(sha256sum "$C8_PACKAGE/bin/c8d2_decimal" | cut -c1-64)" = $DEFDEC ] || { echo "the export's bin/ is not the final default build" >&2; exit 3; }
P=$L/pkg_zen2; mkdir "$P"
( cd "$C8_PACKAGE" && tar --exclude=./bin --exclude=./build --exclude=./inputs/packs/free_L8.pack --exclude=./inputs/packs/power_L8.pack -cf - . ) | tar -C "$P" -xf -
for s in free power; do ln -s "$C8_PACKAGE/inputs/packs/${s}_L8.pack" "$P/inputs/packs/${s}_L8.pack"; done
cd "$P" || exit 64
step() { echo "== $(date -Is) $*"; }
step "build with GMP_PREFIX=$ZEN2"
t0=$(date +%s)
{ make -j32 && make -j32 gmp GMP_PREFIX="$ZEN2" && make -j8 inspect && make -j8 profile ratiohist GMP_PREFIX="$ZEN2" && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
{ echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; for b in bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/ref/c7d2_gmp bin/c8d2_decimal; do echo "# $b"; ldd "$b" | grep -E 'libgmp|libquadmath|libgomp'; readelf -d "$b" | grep -E 'RPATH|RUNPATH'; done; } > "$E/ldd.txt" 2>&1
mkdir "$E/build_records"; for x in bin/*.build.json bin/ref/*.build.json; do cp "$x" "$E/build_records/$(echo "$x" | tr / _)"; done
python3 - "$E" "$ZEN2" <<'PY' || { echo "the zen2 build is not as required; no gate run" >&2; exit 3; }
import hashlib, json, sys
from pathlib import Path
E, Z = Path(sys.argv[1]), sys.argv[2]; h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
br = json.loads(Path('bin/c8d2_gmp.build.json').read_text()); gl = br.get('gmp_library') or {}
ldd = (E / 'ldd.txt').read_text()
rec = {'decimal_sha256': h('bin/c8d2_decimal'), 'decimal_is_default': h('bin/c8d2_decimal') == '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf',
       'zen2_gmp_sha256': h('bin/c8d2_gmp'), 'stage4b_zen2_gmp_aa84cd45': h('bin/c8d2_gmp').startswith('aa84cd45'),
       'build_record_GMP_PREFIX': br.get('GMP_PREFIX'), 'gmp_library': gl, 'BOOST_LIB_VERSION': br.get('BOOST_LIB_VERSION'),
       'development': br.get('development'), 'parameter_overrides': br.get('parameter_overrides'), 'NUMERICS': br.get('NUMERICS'),
       'loads_zen2': f'libgmp.so.10 => {Z}/lib/libgmp.so.10' in ldd.split('# bin/c8d2_gmp_prof')[0],
       'c7ref': {'c7d2_decimal': h('bin/ref/c7d2_decimal'), 'c7d2_gmp': h('bin/ref/c7d2_gmp'),
                 'equal_stage3': (h('bin/ref/c7d2_decimal'), h('bin/ref/c7d2_gmp')) == ('4537dcfd501dec8ba28062e1d09a5308f9ba604919bd7deabdec5ee768faaaaf', '6c82938635462c881b22d8ae92cfb1497ef3efe7bbd9c08cfa5ffda0e2770a52')}}
rec['ok'] = rec['decimal_is_default'] and rec['build_record_GMP_PREFIX'] == Z and rec['loads_zen2'] and rec['c7ref']['equal_stage3'] and rec['BOOST_LIB_VERSION'] == '1_77' and not rec['development'] and not rec['parameter_overrides']
(E / 'zen2_build.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['ok'] else 3)
PY
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/$name.stdout" | cut -c1-300; [ $c -eq 0 ] || status=1; return 0; }
run val2 make test-full GMP_PREFIX="$ZEN2" OUTPUT="$E/val2"
grep -E 'passed|FAILED|Error' "$E/val2.stdout" | cut -c1-240 | tail -20
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 32 --threads 4 --output "$E/bk8.json"
run forced_tiers python3 -B tests/forced_tiers.py --threads 128 --output "$E/forced_tiers.json"
run vs_default python3 -B tests/validate.py --only none --l8self "$C8_PACKAGE/bin" --jobs 32 --threads 4 --output "$E/vs_default_l8.json"
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged by the gates"; else echo "executables CHANGED during the gates" >&2; status=3; fi
cd /; rm -rf "$P" "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
