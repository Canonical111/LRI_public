#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Post-merge re-validation on symmetry (G5 fixes F1-F9 merged into c8): build every executable of the merged head in its
# git-archive export (C8_PACKAGE = pkg/<sha12>) on one AMD node with Ubuntu GCC 11.4, once, for J-VAL-1, J-VAL-4, the
# drills and the A-ORC-13 run.
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/ (`make` re-hashes every pack again in its inputs step).
#   2. make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize, then make c7ref (the exact default path: no
#      NUMERICS, no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides).
#   3. sha256 of every executable against the Stage-5 symmetry build of 5d7586e (s5build.570026.0, same compiler and
#      node type; src/ is unchanged since then, so every executable must be byte-identical), --describe, build records.
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-fxbuild fxbuild.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=fxbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; packs $C8_L8_PACKS; evidence $E"
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
{ make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/c8d2_interleave_probe bin/c8d2_decimal_san bin/c8d2_gmp_san"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_decimal_san.build.json bin/c8d2_gmp_san.build.json "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
python3 - "$E" <<'PY'
import json, sys
from pathlib import Path
E = Path(sys.argv[1])
# the Stage-5 symmetry build of 5d7586e (benchmarks/symmetry_2026-10-c8/stage5/s5build.570026.0/binaries.sha256)
want = {'bin/c8d2_decimal': '619ddf7d1cf94d6229c841cd3fbe22574045ec65a1b69f8b827f1e26f180895f',
        'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17',
        'bin/c8d2_gmp_prof': '69e990c03cfc0256024763fda615cb1a9cffca41ec9f0518defaf5945b2fe62f',
        'bin/c8d2_gmp_ratiohist': '4f4638a210fe9ec5f383b1201885890562f6e40986952162aff4ee40a1d977e8',
        'bin/c8d2_inspect': '10fe813393ac4ce1fa82140d6262407481659833cf10097359035c1c623a29d9',
        'bin/ref/c7d2_decimal': 'e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5',
        'bin/ref/c7d2_gmp': '7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3',
        'bin/c8d2_quad_differential': '1e7a8d34008294b45cc912e74caa97f18b4da303552672e2d124e256db269a79',
        'bin/c8d2_quad_ranges': 'f616b70b3e5f01d7247f5b2c39fc3d2d231740ab8c31b0a36732b651cbdaacf5',
        'bin/c8d2_interleave_probe': 'b0acd9fb991f3e65507be4d8b4218592a6ac5f48ae23b35f7fe050290e22fca1',
        'bin/c8d2_decimal_san': '3ad3d3747ef980d84f65475fb99de7b9cc5511eba7a93e45b1718cf13785b2db',
        'bin/c8d2_gmp_san': 'bcd3fa968ca864972e49d6c690d41c849d381731262821364eea1a4721d11013'}
got = {l.split()[1]: l.split()[0] for l in (E / 'binaries.sha256').read_text().splitlines()}
boost = {p.name: json.loads(p.read_text()).get('BOOST_LIB_VERSION') for p in sorted((E / 'build_records').glob('*.build.json'))}
rec = {'executables': {k: {'sha256': got.get(k), 'stage5_5d7586e': v, 'identical': got.get(k) == v} for k, v in want.items()},
       'BOOST_LIB_VERSION': boost}
rec['identical'] = all(v['identical'] for v in rec['executables'].values())
rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('identical to the Stage-5 build:', rec['identical'], '; BOOST 1_77 everywhere:', rec['boost_1_77_everywhere'])
sys.exit(0 if rec['identical'] else 3)
PY
s=$?
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
