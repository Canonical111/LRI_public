#!/usr/bin/env python3
"""Re-evaluate the identity check of the pilot build job 570620 from its own evidence (no rebuild, nothing executed).

Job 570620 (scripts/ppbuild.slurm) built every executable and wrote all its records, but exited 3 because of a defect
in the job script's own last check: it looked for the text `BOOST_LIB_VERSION: 1_77` in bin/c8d2_inspect.build.txt,
while make writes the macro's value with its quotes (`BOOST_LIB_VERSION: "1_77"`). Every other check had passed
(A-RPL-8 byte-identical, build records, describe). This script repeats the job's checks on the same files with the
inspect line parsed (quotes stripped) and writes identity_recheck.json beside the job's identity.json. Run on the
symmetry login node (a few small JSON and text files):
  python3 -B ppbuild_recheck.py /mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/ppbuild.570620.0 /mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
"""
import json, os, sys
from pathlib import Path
E, PKG = Path(sys.argv[1]), Path(sys.argv[2])
ref = PKG / 'benchmarks/symmetry_2026-10-c8/s6fix4/s4build.570582.0/binaries_end.sha256'
rd = lambda f: {l.split()[1]: l.split()[0] for l in Path(f).read_text().splitlines()}
want, got, end = rd(ref), rd(E / 'binaries.sha256'), rd(E / 'binaries_end.sha256')
cur = {}
import hashlib
for k in got:
    h = hashlib.sha256()
    with open(PKG / k, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    cur[k] = h.hexdigest()
rec = {'job': 570620, 'evidence': str(E), 'reference': str(ref),
       'binaries': {k: {'sha256': v, 'fix4_570582': want.get(k), 'identical': want.get(k) == v, 'end_of_job': end.get(k), 'now': cur.get(k)} for k, v in got.items()}}
rec['byte_identical'] = all(v['identical'] and v['end_of_job'] == v['sha256'] == v['now'] for v in rec['binaries'].values())
brs = {p.name: json.loads(p.read_text()) for p in sorted((E / 'build_records').glob('*.build.json'))}
own = {k: v for k, v in brs.items() if not k.startswith('ref_')}
rec['z3_macro_overrides_empty'] = all(v.get('macro_overrides') == [] for v in own.values())
rec['no_parameter_overrides'] = all(not v.get('parameter_overrides') and v.get('development') is False for v in own.values())
rec['production_required_flags'] = all(v.get('required_flags_present') is True for v in own.values())
rec['numerics_exact'] = all(v.get('NUMERICS') in (None, 'exact') for v in own.values())
rec['records_describe_their_executables'] = all(v.get('executable_sha256') == got.get('bin/' + k[:-len('.build.json')]) for k, v in own.items())
rec['w3_build_directory_is_the_export'] = all(os.path.realpath(v.get('build_directory') or '/nonexistent') == str(PKG.resolve()) for v in own.values())
boost = {k: v.get('BOOST_LIB_VERSION') for k, v in brs.items()}
line = [l for l in (E / 'build_records' / 'c8d2_inspect.build.txt').read_text().splitlines() if l.startswith('BOOST_LIB_VERSION:')]
boost['c8d2_inspect.build.txt'] = line[0].split(':', 1)[1].strip().strip('"') if line else None
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = all(v == '1_77' for v in boost.values())
d = {k: json.loads((E / 'describe' / f'{k}.json').read_text()) for k in ('c8d2_decimal', 'c8d2_gmp')}
rec['describe_exact'] = all(v.get('numerics') in (None, 'exact') and v.get('diagnostic') is False for v in d.values())
rec['ok'] = all(rec[k] for k in ('byte_identical', 'z3_macro_overrides_empty', 'no_parameter_overrides', 'production_required_flags', 'numerics_exact',
                                 'records_describe_their_executables', 'w3_build_directory_is_the_export', 'boost_1_77_everywhere', 'describe_exact'))
(E / 'identity_recheck.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: v for k, v in rec.items() if k != 'binaries'}, indent=1))
print({k: v['sha256'][:12] for k, v in rec['binaries'].items()})
sys.exit(0 if rec['ok'] else 3)
