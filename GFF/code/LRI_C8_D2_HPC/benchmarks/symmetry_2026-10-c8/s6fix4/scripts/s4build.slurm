#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 4 on symmetry: build every executable of the merged fix-round-4 head in its git-archive export
# (C8_PACKAGE = pkg/<sha12>) on one AMD node with Ubuntu GCC 11.4, once, for the jobs that follow (s4val1, s4flag, s4des,
# s4mem). Fix round 4 changes no file under src/, so this is A-RPL-8: every executable must be byte-identical to fix round
# 3's build of b58e9b6 (job 570540, s6fix3/s3build.570540.0/), the gated dd+mp256 build a46f3060... included. Template:
# s6fix3/scripts/s3build.slurm (jobs 570533, 570540).
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/.
#   2. make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize, then make c7ref (the exact default path: no
#      NUMERICS, no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides); then make gmp NUMERICS=dd,mp256. Every executable
#      equal (sha256) to 570540's; the two sanitizer builds embed the export path and a GNU build-id, so they are compared
#      with pkg/b58e9b6f4afd's after both are normalized (the 12-character export tag and the build-id note zeroed).
#   3. Every build record: macro_overrides [], no parameter override, development false, the production builds
#      required_flags_present, Boost 1_77; and (W3, fix round 4) build_directory = this export, the directory make ran in.
# A mismatch exits 3 (stop and report).
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-s4build s4build.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s4build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
PREV=$D/pkg/b58e9b6f4afd   # fix round 3's build of b58e9b6 (job 570540): the reference of A-RPL-8 and of the sanitizer comparison
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); packs $C8_L8_PACKS; evidence $E"
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
python3 - "$E" "$C8_PACKAGE" "$PREV" <<'PY'
import json, re, subprocess, sys
from pathlib import Path
E, PKG, PREV = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ref = PKG / 'benchmarks/symmetry_2026-10-c8/s6fix3/s3build.570540.0'   # fix round 3's build of b58e9b6 (in this export)
rd = lambda f: {l.split()[1]: l.split()[0] for l in Path(f).read_text().splitlines()}
want = rd(ref / 'binaries_after_profile.sha256'); want['bin/c8d2_gmp_dd+mp256'] = (ref / 'profile.sha256').read_text().split()[0]
got, after = rd(E / 'binaries.sha256'), rd(E / 'binaries_after_profile.sha256'); got_all = dict(after); got_all['bin/c8d2_gmp_dd+mp256'] = (E / 'profile.sha256').read_text().split()[0]
SAN = ('bin/c8d2_decimal_san', 'bin/c8d2_gmp_san')
rec = {'reference': str(ref), 'binaries': {k: {'sha256': got_all.get(k), 'fix3_570540': v, 'identical': got_all.get(k) == v} for k, v in want.items()}}
rec['byte_identical'] = all(v['identical'] for k, v in rec['binaries'].items() if k not in SAN)
def norm(p: Path) -> tuple[bytes, str | None]:
    b = p.read_bytes(); out = subprocess.run(['readelf', '-n', str(p)], capture_output=True, text=True).stdout
    m = re.search(r'Build ID: ([0-9a-f]+)', out); bid = m.group(1) if m else None
    if bid: b = b.replace(bytes.fromhex(bid), b'\0' * (len(bid) // 2))
    return re.sub(rb'pkg/[0-9a-f]{12}', b'pkg/XXXXXXXXXXXX', b), bid
san = {}
for k in SAN:
    a, ba = norm(PREV / k); n, bn = norm(PKG / k)
    san[k] = {'sha256': [want.get(k), got_all.get(k)], 'build_ids': [ba, bn], 'bytes': [len(a), len(n)], 'equal_after_normalizing': a == n}
rec['sanitizers_vs_b58e9b6f4afd'] = san; rec['sanitizers_equal_after_normalizing'] = all(v['equal_after_normalizing'] for v in san.values())
rec['defaults_unchanged_by_profile_build'] = got == after
brs = {p.name: json.loads(p.read_text()) for p in sorted((E / 'build_records').glob('*.build.json'))}
own = {k: v for k, v in brs.items() if not k.startswith('ref_')}
rec['build_records'] = {k: {x: v.get(x) for x in ('macro_overrides', 'parameter_overrides', 'development', 'required_flags_present', 'diagnostic', 'NUMERICS',
                                                    'BOOST_LIB_VERSION', 'executable_sha256', 'compiler', 'build_directory')} for k, v in own.items()}
rec['z3_macro_overrides_empty'] = all(v.get('macro_overrides') == [] for v in own.values())
rec['no_parameter_overrides'] = all(not v.get('parameter_overrides') and v.get('development') is False for v in own.values())
prod = ('c8d2_decimal.build.json', 'c8d2_gmp.build.json', 'c8d2_gmp_dd+mp256.build.json')
rec['production_required_flags'] = all(own[k].get('required_flags_present') is True for k in prod)
rec['records_describe_their_executables'] = all(own[k].get('executable_sha256') == got_all.get('bin/' + k[:-len('.build.json')]) for k in prod)
rec['w3_build_directory'] = {k: v.get('build_directory') for k, v in own.items()}
import os; rec['w3_build_directory_is_the_export'] = all(os.path.realpath(v.get('build_directory') or '/nonexistent') == str(PKG.resolve()) for v in own.values())
boost = {k: v.get('BOOST_LIB_VERSION') for k, v in brs.items()}
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
d = json.loads((E / 'describe' / 'c8d2_gmp_dd+mp256.json').read_text()); np_ = d.get('numerics_params') or {}
rec['profile_ok'] = (d.get('numerics') == 'dd+mp256' and d.get('diagnostic') is False and not any(isinstance(v, dict) and (v.get('development') or v.get('stub')) for v in np_.values())
                     and own['c8d2_gmp_dd+mp256.build.json'].get('NUMERICS') == 'dd+mp256')
rec['ok'] = (rec['byte_identical'] and rec['sanitizers_equal_after_normalizing'] and rec['defaults_unchanged_by_profile_build'] and rec['z3_macro_overrides_empty']
             and rec['no_parameter_overrides'] and rec['production_required_flags'] and rec['records_describe_their_executables'] and rec['profile_ok']
             and rec['boost_1_77_everywhere'] and rec['w3_build_directory_is_the_export'])
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('A-RPL-8 byte-identical to 570540:', rec['byte_identical'], {k: (v['sha256'] or '')[:12] for k, v in rec['binaries'].items()})
print('sanitizers equal after normalizing:', rec['sanitizers_equal_after_normalizing'], '; defaults unchanged by the profile build:', rec['defaults_unchanged_by_profile_build'],
      '; macro_overrides []:', rec['z3_macro_overrides_empty'], '; no parameter overrides:', rec['no_parameter_overrides'], '; required flags:', rec['production_required_flags'],
      '; profile ok:', rec['profile_ok'], '; Boost 1_77:', rec['boost_1_77_everywhere'], '; build_directory = export (W3):', rec['w3_build_directory_is_the_export'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
sha256sum $X bin/c8d2_gmp_dd+mp256 > "$E/binaries_end.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
