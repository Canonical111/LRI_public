#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage 5 on symmetry (the plan's site): build every executable of the final commit in its git-archive export
# (C8_PACKAGE = pkg/5d7586e9f1ab) on one AMD node with Ubuntu GCC 11.4, for the final J-VAL-1..4, the sweeps, the smoke
# and the drills. The builds happen ONCE here; the J-VAL jobs never run make c7ref (it deletes and rebuilds bin/ref).
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs, built by job 569788 from the full inventory copy)
#      are re-hashed against this export's inputs/manifest.json, then hard-linked into inputs/packs/ (`make` re-hashes
#      every pack again in its `inputs` step).
#   2. make -j all gmp inspect profile ratiohist quaddiff probes sanitize, then make c7ref (default path: no NUMERICS,
#      no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides).
#   3. The Stage-3 baseline from tag c8-stage3 (C8_BASELINE_PKG = pkg/b4273c59e911, its own git-archive export) built
#      there with its own Makefile (bin/c8d2_decimal bin/c8d2_gmp), byte-copied into bin/baseline/ (A-RPL-7 G-L8SELF).
#   4. sha256 of every executable, --describe, build records; c7ref against the plan's symmetry hashes e696d7f3.../
#      7e3c8c92... (recorded; J-VAL-2 decides); BOOST_LIB_VERSION 1_77 in the build records.
# Usage: C8_PACKAGE=... C8_L8_PACKS=... C8_BASELINE_PKG=... sbatch --export=ALL -J c8d2-s5build s5build.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}" "${C8_BASELINE_PKG:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; packs $C8_L8_PACKS; baseline $C8_BASELINE_PKG; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
python3 - "$C8_L8_PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
import hashlib, json, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); man = json.loads(Path('inputs/manifest.json').read_text())['sha256']; rec = {}
for s in ('free', 'power'):
    p = src / f'{s}_L8.pack'; h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    rec[s] = {'source': str(p), 'bytes': p.stat().st_size, 'inode': p.stat().st_ino, 'sha256': h.hexdigest(),
              'manifest': man[f'packs/{s}_L8.pack'], 'equal': h.hexdigest() == man[f'packs/{s}_L8.pack']}
out.write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if all(v['equal'] for v in rec.values()) else 3)
PY
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
( cd "$C8_BASELINE_PKG" && test ! -e bin && make -j2 bin/c8d2_decimal bin/c8d2_gmp ) > "$E/make_baseline.log" 2>&1 & bpid=$!
{ make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
wait $bpid || { echo "baseline build FAILED"; tail -40 "$E/make_baseline.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"; grep -E 'SKIPPED|verified|"counts"' "$E/make.log" | head -5 | cut -c1-200
mkdir bin/baseline && cp -p "$C8_BASELINE_PKG/bin/c8d2_decimal" "$C8_BASELINE_PKG/bin/c8d2_gmp" bin/baseline/ || exit 3
cp -p "$C8_BASELINE_PKG/bin/c8d2_decimal.build.json" bin/baseline/c8d2_decimal.build.json; cp -p "$C8_BASELINE_PKG/bin/c8d2_gmp.build.json" bin/baseline/c8d2_gmp.build.json
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/c8d2_interleave_probe bin/c8d2_decimal_san bin/c8d2_gmp_san bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
for x in c8d2_decimal c8d2_gmp; do bin/baseline/$x --describe > "$E/describe/baseline_$x.json"; cp bin/baseline/$x.build.json "$E/build_records/baseline_$x.build.json"; done
cp bin/c8d2_decimal_san.build.json bin/c8d2_gmp_san.build.json "$E/build_records/"
bin/c8d2_inspect --describe > "$E/describe/c8d2_inspect.json" 2>&1; cp bin/c8d2_inspect.build.txt bin/c8d2_quad_differential.build.txt bin/c8d2_quad_ranges.build.txt bin/c8d2_interleave_probe.build.txt "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
python3 - "$E" <<'PY'
import hashlib, json, sys, glob
from pathlib import Path
E = Path(sys.argv[1]); h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
want = {'bin/ref/c7d2_decimal': 'e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5',
        'bin/ref/c7d2_gmp': '7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3'}
rec = {k: {'this': h(k), 'plan_symmetry': v, 'equal': h(k) == v} for k, v in want.items()}
boost = {}
for f in sorted(glob.glob(str(E / 'build_records' / '*.build.json'))):
    d = json.loads(Path(f).read_text()); boost[Path(f).name] = d.get('boost_lib_version') or d.get('BOOST_LIB_VERSION') or (d.get('macros') or {}).get('BOOST_LIB_VERSION')
doc = {'c7ref': rec, 'c7ref_equal_plan_hashes': all(v['equal'] for v in rec.values()), 'boost_lib_version_per_record': boost,
       'stage4a_symmetry_stage3_gmp_7a8aad7': '23624153cd3e8b45cf8438658c905893689bb9707516038b4717a60c8c26d3a3',
       'baseline_gmp': h('bin/baseline/c8d2_gmp'), 'baseline_decimal': h('bin/baseline/c8d2_decimal')}
(E / 'identity.json').write_text(json.dumps(doc, indent=1) + '\n'); print(json.dumps(doc, indent=1))
PY
grep -h BOOST_LIB_VERSION bin/c8d2_inspect.build.txt
rm -rf "$TMPDIR"
echo "finished $(date -Is), status 0"
exit 0
