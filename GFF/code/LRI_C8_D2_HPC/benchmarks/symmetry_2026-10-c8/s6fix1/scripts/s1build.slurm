#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 1 on symmetry: build every executable of the merged fix-round head in its git-archive export
# (C8_PACKAGE = pkg/<sha12>) on one AMD node with Ubuntu GCC 11.4, once, for J-VAL-1, the dd+mp256 J-FLAG gate re-run,
# the X8 check and the route-(b) re-freeze. src/ is unchanged since 5d7586e, so this is A-RPL-8:
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/ (`make` re-hashes every pack again in its inputs step).
#   2. make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize, then make c7ref (the exact default path: no
#      NUMERICS, no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides).
#   3. A-RPL-8: sha256 of every executable against the Stage-5 symmetry build of 5d7586e (s5build.570026.0; decimal
#      619ddf7d..., gmp 2cc5e88e...); the two sanitizer builds are compared with pkg/5d7586e9f1ab/bin/*_san after the
#      export path and the GNU build-id are normalized (as in stage5/close/clbuild.570208.0).
#   4. make gmp NUMERICS=dd,mp256 builds bin/c8d2_gmp_dd+mp256, which must be byte-identical to the build the profile cost
#      model and the 570210 gate recorded (d5df32ac...); every default executable keeps its sha256; --describe and the
#      build record of the profile.
#   5. X3 on real Linux: tests/thread_identity.py (A-RPL-6, both backends; every run's OpenMP team observed from
#      /proc/<pid>/task and required to equal the request), then again for gmp with OMP_THREAD_LIMIT=1 and
#      OMP_DYNAMIC=true inherited (the harness must strip them: same rows, the requested teams observed).
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-s1build s1build.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s1build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
S5=$D/pkg/5d7586e9f1ab
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
echo "default builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/c8d2_interleave_probe bin/c8d2_decimal_san bin/c8d2_gmp_san"
sha256sum $X | tee "$E/binaries.sha256"
t0=$(date +%s)
make gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "profile build in $(( $(date +%s) - t0 )) s"
sha256sum $X > "$E/binaries_after_profile.sha256"
sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist c8d2_gmp_dd+mp256; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_decimal_san.build.json bin/c8d2_gmp_san.build.json "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
for x in c8d2_decimal_san c8d2_gmp_san; do
  for f in "$S5/bin/$x" "bin/$x"; do readelf -n "$f" | sed -n 's/.*Build ID: *//p'; done > "$E/buildid_$x.txt"
done
python3 - "$E" "$S5" "$C8_PACKAGE" <<'PY'
import json, sys
from pathlib import Path
E, S5, PKG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
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
        'bin/c8d2_interleave_probe': 'b0acd9fb991f3e65507be4d8b4218592a6ac5f48ae23b35f7fe050290e22fca1'}
san = {'bin/c8d2_decimal_san': '3ad3d3747ef980d84f65475fb99de7b9cc5511eba7a93e45b1718cf13785b2db',
       'bin/c8d2_gmp_san': 'bcd3fa968ca864972e49d6c690d41c849d381731262821364eea1a4721d11013'}
rd = lambda f: {l.split()[1]: l.split()[0] for l in (E / f).read_text().splitlines()}
got, after = rd('binaries.sha256'), rd('binaries_after_profile.sha256')
boost = {p.name: json.loads(p.read_text()).get('BOOST_LIB_VERSION') for p in sorted((E / 'build_records').glob('*.build.json'))}
rec = {'A-RPL-8': {k: {'sha256': got.get(k), 'stage5_5d7586e': v, 'identical': got.get(k) == v} for k, v in want.items()}}
rec['default_identical'] = all(v['identical'] for v in rec['A-RPL-8'].values())
# sanitizer builds: equal once the export tag (12 hex characters of the path, same length) and the build-id are replaced
pairs = {}
for k, h in san.items():
    name = k.split('/')[-1]; a = (S5 / 'bin' / name).read_bytes(); b = (PKG / k).read_bytes()
    ids = [bytes.fromhex(x) for x in (E / f'buildid_{name}.txt').read_text().split()]
    occ = [a.count(str(S5).encode()), b.count(str(PKG).encode())]
    na = a.replace(str(S5).encode(), b'X' * len(str(S5))).replace(ids[0], b'\0' * len(ids[0]))
    nb = b.replace(str(PKG).encode(), b'X' * len(str(PKG))).replace(ids[1], b'\0' * len(ids[1]))
    diff = sum(x != y for x, y in zip(a, b)) if len(a) == len(b) else None
    pairs[name] = {'stage5_sha256': h, 'stage5_file_sha256_matches': __import__('hashlib').sha256(a).hexdigest() == h,
                   'new_sha256': got.get(k), 'bytes': [len(a), len(b)], 'differing_bytes': diff,
                   'build_id_stage5': ids[0].hex(), 'build_id_new': ids[1].hex(), 'export_path_occurrences': occ,
                   'equal_after_normalizing': na == nb}
rec['sanitizer'] = {'rule': 'the sanitizer builds embed the absolute build directory (one string, the export path) and hence a '
                            'different GNU build-id; equal after both are normalized means the same program', 'pairs': pairs,
                    'equivalent': all(p['equal_after_normalizing'] and p['stage5_file_sha256_matches'] for p in pairs.values())}
rec['defaults_unchanged_by_profile_build'] = got == after
d = json.loads((E / 'describe' / 'c8d2_gmp_dd+mp256.json').read_text())
br = json.loads((E / 'build_records' / 'c8d2_gmp_dd+mp256.build.json').read_text())
np_ = d.get('numerics_params') or {}
rec['profile'] = {'sha256': (E / 'profile.sha256').read_text().split()[0], 'numerics': d.get('numerics'), 'diagnostic': d.get('diagnostic'),
                  'numerics_params': np_, 'development_overrides': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('development')),
                  'stubs': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('stub')),
                  'build_record_numerics': br.get('NUMERICS'), 'build_record_parameter_overrides': br.get('parameter_overrides'),
                  'build_record_numerics_sources': br.get('numerics_sources'), 'build_record_command': br.get('command')}
rec['profile_ok'] = (d.get('numerics') == 'dd+mp256' and d.get('diagnostic') is False and not rec['profile']['development_overrides']
                     and not rec['profile']['stubs'] and br.get('NUMERICS') == 'dd+mp256' and not br.get('parameter_overrides'))
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
rec['profile']['d5df32ac_570210'] = 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d'
rec['profile']['identical_to_gated_build'] = rec['profile']['sha256'] == rec['profile']['d5df32ac_570210']
rec['ok'] = (rec['default_identical'] and rec['sanitizer']['equivalent'] and rec['defaults_unchanged_by_profile_build'] and rec['profile_ok']
             and rec['profile']['identical_to_gated_build'])
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('A-RPL-8 default executables identical to the Stage-5 build:', rec['default_identical'],
      '; sanitizer builds equivalent:', rec['sanitizer']['equivalent'], '; defaults unchanged by the profile build:',
      rec['defaults_unchanged_by_profile_build'], '; profile dd+mp256 ok:', rec['profile_ok'], '; profile = d5df32ac:', rec['profile']['identical_to_gated_build'], '; BOOST 1_77 everywhere:', rec['boost_1_77_everywhere'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
# 5. X3: thread identity with the observed OpenMP team sizes (whole node, 64 cores)
t0=$(date +%s)
python3 -B tests/thread_identity.py --output "$E/thread_identity.json" > "$E/thread_identity.log" 2>&1; c=$?
echo "thread_identity exit $c after $(( $(date +%s) - t0 )) s"; tail -3 "$E/thread_identity.log" | cut -c1-300; [ $c -eq 0 ] || s=3
t0=$(date +%s)
OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true python3 -B tests/thread_identity.py --backends gmp --output "$E/thread_identity_omp_env.json" > "$E/thread_identity_omp_env.log" 2>&1; c=$?
echo "thread_identity (inherited OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true) exit $c after $(( $(date +%s) - t0 )) s"; tail -3 "$E/thread_identity_omp_env.log" | cut -c1-300; [ $c -eq 0 ] || s=3
python3 - "$E" <<'PY'
import json, sys
from pathlib import Path
for f in ('thread_identity.json', 'thread_identity_omp_env.json'):
    p = Path(sys.argv[1]) / f
    if not p.exists(): print(f, 'MISSING'); continue
    d = json.loads(p.read_text())
    print(f, {k: d.get(k) for k in ('status', 'team_sizes_verified', 'teams_observed', 'wall_seconds')})
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
