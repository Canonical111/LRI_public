#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=64G -t 00:30:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# C8(2) L8 pilot preparation on symmetry (2026-10-06): build the pilot's executables in the git-archive export of the
# final package head (C8_PACKAGE = pkg/<sha12> of ba68f40) on one AMD node with Ubuntu GCC 11.4, once, on the EXACT
# default path (no NUMERICS, no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS/OPTFLAGS overrides). Template:
# s6fix4/scripts/s4build.slurm (jobs 570572, 570582), reduced to the targets a pilot needs.
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/ (a mismatch: nothing linked, exit 3).
#   2. make -j48 all gmp inspect (all and gmp run `make inputs`: tools/prepare_inputs.py verifies every pack, the L8
#      packs included, the small inputs and the vendored pins), then make c7ref.
#   3. A-RPL-8: every executable equal (sha256) to fix round 4's build of 900e590 (job 570582,
#      benchmarks/symmetry_2026-10-c8/s6fix4/s4build.570582.0/binaries_end.sha256, in this export): bin/c8d2_decimal
#      a18ce425..., bin/c8d2_gmp 7741f733..., bin/c8d2_inspect 38361979..., bin/ref/c7d2_decimal e696d7f3...,
#      bin/ref/c7d2_gmp 7e3c8c92.... Every build record: macro_overrides [], no parameter override, development false,
#      required flags present, Boost 1_77, NUMERICS exact, executable_sha256 = the file, build_directory = this export (W3).
# A mismatch exits 3 (stop and report).
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-ppbuild ppbuild.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=/mnt/beegfs/zzheng1/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=ppbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
sha256sum inputs/manifest.json | tee "$E/inputs_manifest.sha256"
t0=$(date +%s)
{ make -j48 all gmp inspect && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_inspect.build.txt "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
ldd bin/c8d2_gmp > "$E/ldd_c8d2_gmp.txt" 2>&1
python3 - "$E" "$C8_PACKAGE" <<'PY'
import json, os, sys
from pathlib import Path
E, PKG = Path(sys.argv[1]), Path(sys.argv[2])
ref = PKG / 'benchmarks/symmetry_2026-10-c8/s6fix4/s4build.570582.0/binaries_end.sha256'   # fix round 4's build of 900e590 (in this export)
rd = lambda f: {l.split()[1]: l.split()[0] for l in Path(f).read_text().splitlines()}
want, got = rd(ref), rd(E / 'binaries.sha256')
rec = {'reference': str(ref), 'binaries': {k: {'sha256': v, 'fix4_570582': want.get(k), 'identical': want.get(k) == v} for k, v in got.items()}}
rec['byte_identical'] = all(v['identical'] for v in rec['binaries'].values())
brs = {p.name: json.loads(p.read_text()) for p in sorted((E / 'build_records').glob('*.build.json'))}
own = {k: v for k, v in brs.items() if not k.startswith('ref_')}
rec['build_records'] = {k: {x: v.get(x) for x in ('macro_overrides', 'parameter_overrides', 'development', 'required_flags_present', 'diagnostic', 'NUMERICS',
                                                    'BOOST_LIB_VERSION', 'executable_sha256', 'compiler', 'build_directory')} for k, v in own.items()}
rec['z3_macro_overrides_empty'] = all(v.get('macro_overrides') == [] for v in own.values())
rec['no_parameter_overrides'] = all(not v.get('parameter_overrides') and v.get('development') is False for v in own.values())
rec['production_required_flags'] = all(v.get('required_flags_present') is True for v in own.values())
rec['numerics_exact'] = all(v.get('NUMERICS') in (None, 'exact') for v in own.values())
rec['records_describe_their_executables'] = all(v.get('executable_sha256') == got.get('bin/' + k[:-len('.build.json')]) for k, v in own.items())
rec['w3_build_directory_is_the_export'] = all(os.path.realpath(v.get('build_directory') or '/nonexistent') == str(PKG.resolve()) for v in own.values())
boost = {k: v.get('BOOST_LIB_VERSION') for k, v in brs.items()}
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
rec['inspect_boost_1_77'] = 'BOOST_LIB_VERSION: 1_77' in (E / 'build_records' / 'c8d2_inspect.build.txt').read_text()
d = {k: json.loads((E / 'describe' / f'{k}.json').read_text()) for k in ('c8d2_decimal', 'c8d2_gmp')}
rec['describe_numerics'] = {k: v.get('numerics') for k, v in d.items()}
rec['describe_diagnostic'] = {k: v.get('diagnostic') for k, v in d.items()}
rec['describe_exact'] = all(v.get('numerics') in (None, 'exact') and v.get('diagnostic') is False for v in d.values())
rec['ok'] = (rec['byte_identical'] and rec['z3_macro_overrides_empty'] and rec['no_parameter_overrides'] and rec['production_required_flags'] and rec['numerics_exact']
             and rec['records_describe_their_executables'] and rec['w3_build_directory_is_the_export'] and rec['boost_1_77_everywhere'] and rec['inspect_boost_1_77']
             and rec['describe_exact'])
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('A-RPL-8 byte-identical to 570582:', rec['byte_identical'], {k: v['sha256'][:12] for k, v in rec['binaries'].items()})
print('macro_overrides []:', rec['z3_macro_overrides_empty'], '; no parameter overrides:', rec['no_parameter_overrides'], '; required flags:', rec['production_required_flags'],
      '; numerics exact:', rec['numerics_exact'], '; describe exact:', rec['describe_exact'], '; Boost 1_77:', rec['boost_1_77_everywhere'], rec['inspect_boost_1_77'],
      '; build_directory = export (W3):', rec['w3_build_directory_is_the_export'], '; records describe their executables:', rec['records_describe_their_executables'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
sha256sum $X > "$E/binaries_end.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
