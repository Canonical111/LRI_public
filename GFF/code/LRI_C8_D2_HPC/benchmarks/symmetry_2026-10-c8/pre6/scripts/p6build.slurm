#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Pre-Stage-6 run on symmetry: build the executables of the design agent's head (F11 fix and route (b), 23540b2/99bbfdd,
# plus this folder's job scripts) in its git-archive export (C8_PACKAGE = pkg/<sha12>) on one AMD node with Ubuntu
# GCC 11.4, for the dd+mp256 profile cost sweep and the J-DES-5 re-check.
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/ (`make` re-hashes every pack again in its inputs step).
#   2. make (all: decimal and inputs), make gmp, then make gmp NUMERICS=dd,mp256 (the user-approved profile, no exp1);
#      the exact default path otherwise: no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides.
#   3. A-RPL-8: the default executables must be byte-identical to the Stage-5 symmetry build of 5d7586e
#      (s5build.570026.0: decimal 619ddf7d..., gmp 2cc5e88e...; src/ and the Makefile's compile rules are unchanged
#      since), and the profile executable to the build the dd+mp256 J-FLAG gate passed (570208/570210: d5df32ac...),
#      which a non-test route-(b) plan requires; every default executable keeps its sha256 across the profile build;
#      --describe of the profile: numerics dd+mp256, not diagnostic, no development parameter override, no stub.
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-p6build p6build.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=p6build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
{ make -j48 && make -j48 gmp; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "default builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp"
sha256sum $X | tee "$E/binaries.sha256"
t0=$(date +%s)
make gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "profile build in $(( $(date +%s) - t0 )) s"
sha256sum $X > "$E/binaries_after_profile.sha256"
sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_dd+mp256; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
python3 - "$E" <<'PY'
import json, sys
from pathlib import Path
E = Path(sys.argv[1])
# the Stage-5 symmetry build of 5d7586e (benchmarks/symmetry_2026-10-c8/stage5/s5build.570026.0/binaries.sha256) and the
# dd+mp256 build the J-FLAG gate passed (stage5/close/clbuild.570208.0/profile.sha256; gate 570210)
want = {'bin/c8d2_decimal': '619ddf7d1cf94d6229c841cd3fbe22574045ec65a1b69f8b827f1e26f180895f',
        'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17'}
gated = 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d'
rd = lambda f: {l.split()[1]: l.split()[0] for l in (E / f).read_text().splitlines()}
got, after = rd('binaries.sha256'), rd('binaries_after_profile.sha256')
boost = {p.name: json.loads(p.read_text()).get('BOOST_LIB_VERSION') for p in sorted((E / 'build_records').glob('*.build.json'))}
rec = {'A-RPL-8': {k: {'sha256': got.get(k), 'stage5_5d7586e': v, 'identical': got.get(k) == v} for k, v in want.items()}}
rec['default_identical'] = all(v['identical'] for v in rec['A-RPL-8'].values())
rec['defaults_unchanged_by_profile_build'] = got == after
d = json.loads((E / 'describe' / 'c8d2_gmp_dd+mp256.json').read_text())
br = json.loads((E / 'build_records' / 'c8d2_gmp_dd+mp256.build.json').read_text())
np_ = d.get('numerics_params') or {}
psha = (E / 'profile.sha256').read_text().split()[0]
rec['profile'] = {'sha256': psha, 'gated_build_570208_570210': gated, 'identical_to_gated_build': psha == gated,
                  'numerics': d.get('numerics'), 'diagnostic': d.get('diagnostic'), 'numerics_params': np_,
                  'development_overrides': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('development')),
                  'stubs': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('stub')),
                  'build_record_numerics': br.get('NUMERICS'), 'build_record_parameter_overrides': br.get('parameter_overrides'),
                  'build_record_command': br.get('command')}
rec['profile_ok'] = (d.get('numerics') == 'dd+mp256' and d.get('diagnostic') is False and not rec['profile']['development_overrides']
                     and not rec['profile']['stubs'] and br.get('NUMERICS') == 'dd+mp256' and not br.get('parameter_overrides'))
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
rec['ok'] = rec['default_identical'] and rec['defaults_unchanged_by_profile_build'] and rec['profile_ok'] and rec['profile']['identical_to_gated_build']
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('A-RPL-8 default executables identical to the Stage-5 build:', rec['default_identical'],
      '; defaults unchanged by the profile build:', rec['defaults_unchanged_by_profile_build'], '; profile dd+mp256 ok:', rec['profile_ok'],
      '; profile identical to the gated build d5df32ac:', rec['profile']['identical_to_gated_build'], '; BOOST 1_77 everywhere:', rec['boost_1_77_everywhere'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
