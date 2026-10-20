#!/usr/bin/env python3
"""Replay (and test) of lri_general_closed_update: finite Horn arrays of the C5 masters and the Q2, Z2 identities
(note Section 14).

Run from the package folder (GFF/code/lri_general_closed_update) as `make -f public.mk replay` or `make -f public.mk test`
(= replay plus --full). Nothing shipped is modified: the delivered scripts write their records in place (into
verification/general_closed/), so they run in a fresh copy of the package under public/out/work/.

replay (about 20 s, one core):
  1. integrity: public/SOURCE_SHA256SUMS (the 31 shipped source files, hashes from the bundle MANIFEST.json; complete),
     verification/general_closed/array_manifest.json (the 7 Horn arrays; complete) and
     verification/general_closed/release_manifest.json (8 scripts and 2 note snapshots; ignore-missing, because the note
     snapshots are not shipped: the note is GFF/note).
  2. reruns kappa_regularization.py (SymPy; its stdout is K_regular_exact_log.txt), check_insertion_prefactors.py (336 exact
     rational checks), check_new_identities.py (60-digit Q2, Z2, K-term identities, P5 residues, d=1 Gamma integral) and
     horn_compiler.py for the masters Q, P4, L, Z, K into a scratch folder, and compares with the delivered records.
  3. recomputes the numbers the note and the paper quote from this package (expected.json 'values': Q2 and the Horn
     counts of L_d, Z_d, K_d) and checks Z2 = 4 G Q2 and the package README's counts.
test (--full, about 4 min on one core, 0.25 GB): additionally the full compiler (P5a and P5b, 15060 functions; 2.4 min),
  check_horn_compiler.py (1038 exact coefficient comparisons, 12 shift identities; about 1 min), check_primitive_sums.py and
  primitive_series.py (double-precision residue sums against spectral quadrature).

Tolerances. SymPy and mpmath outputs are deterministic: compared exactly after dropping timing keys; the gzip arrays are
compared on their decompressed bytes (the gzip header stores a write time, so regenerated .gz files never match
array_manifest.json, which is checked on the shipped files only). numpy outputs (primitive sums, raw P5 sums): values
relative 1e-8, residuals and differences absolute 1e-6. Quoted numbers at the printed digits; Q2 to 50 digits is exact
(mpmath at 60 digits).
Checked: the delivered records (made on Linux with Python 3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0,
mpmath 1.3.0) were reproduced on macOS arm64 with Python 3.10.12, numpy 1.24.4, scipy 1.11.1, sympy 1.12,
mpmath 1.3.0 (gmpy2 backend), and the replay also with Python 3.10.11, numpy 1.23.5, scipy 1.10.0, sympy 1.11.1,
mpmath 1.2.1: all exact-tier records and all seven decompressed arrays identical; float tier within 5.2e-14
relative and 3.2e-11 absolute.
"""
import argparse, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, row, load, verify_sums, verify_hashes, work_copy, run, cmp_exact, cmp_float, cmp_gz, quoted,
                    close, report)  # noqa: E402

GC = 'code/general_closed'
REC = PKG / 'verification/general_closed'
ARR = REC / 'horn_arrays'
SMALL = ('Q', 'P4', 'L', 'Z', 'K')


def compiler_checks(work, masters, label):
    out = work / 'new_horn_arrays'
    run(work, f'{GC}/horn_compiler.py', '--masters', ','.join(masters), '--out', out,
        show=f'--masters {",".join(masters)} --out <copy>/new_horn_arrays')
    for m in masters: cmp_gz(f'{m}_horn.json.gz: {label} = delivered (decompressed)', out / f'{m}_horn.json.gz', ARR / f'{m}_horn.json.gz')
    for f in ('scalar_parameters.json', 'atom_dictionary.json'):
        cmp_exact(f'{f}: {label} = delivered', out / f, ARR / f)
    new = {s['name']: s for s in load(out / 'summary.json')} if (out / 'summary.json').is_file() else {}
    old = {s['name']: s for s in load(ARR / 'summary.json')}
    same = all(new.get(m) == old[m] for m in masters)
    row(f'summary.json entries {",".join(masters)}: {label} = delivered', same, True, same)


def replay(work, exp):
    verify_sums(PKG / 'public/SOURCE_SHA256SUMS')
    am = load(REC / 'array_manifest.json')
    verify_hashes('verification/general_closed/array_manifest.json', {f'verification/general_closed/horn_arrays/{k}': v
                  for k, v in am['sha256'].items()}, PKG, ignore_missing=False)
    rm = load(REC / 'release_manifest.json')
    verify_hashes('verification/general_closed/release_manifest.json', rm['files'], PKG, ignore_missing=True)

    log = run(work, f'{GC}/kappa_regularization.py', outputs=['verification/general_closed/K_regular_poly.txt'])
    cmp_exact('K_regular_poly.txt: recomputed = delivered', work / 'verification/general_closed/K_regular_poly.txt', REC / 'K_regular_poly.txt')
    cmp_exact('K_regular_exact_log.txt = stdout of kappa_regularization.py', log or work / 'missing', REC / 'K_regular_exact_log.txt')
    for s, f in (('check_insertion_prefactors.py', 'insertion_prefactor_checks.json'), ('check_new_identities.py', 'identity_checks.json')):
        run(work, f'{GC}/{s}', outputs=[f'verification/general_closed/{f}'])
        cmp_exact(f'{f}: recomputed = delivered', work / 'verification/general_closed' / f, REC / f)
    compiler_checks(work, SMALL, 'recompiled')

    # --- quoted numbers and identities
    idc = load(REC / 'identity_checks.json')
    for v in exp['values']:
        if v['package'] != PKG.name: continue
        if v['id'].startswith('Q2'):
            quoted(f'{v["id"]} ({v["note"] or v["paper"]})', idc['Q2']['gamma_ratio'], v['printed'], f'owner {v["owner"]}')
        elif v['id'].startswith('Horn count'):
            name = {'L_d': 'L', 'Z_d': 'Z', 'K_d': 'K'}[v['id'].split()[-1]]
            s = {x['name']: x for x in load(ARR / 'summary.json')}[name]
            row(f'{v["id"]} ({v["note"]})', s['functions'], int(v['printed']), s['functions'] == int(v['printed']), f'owner {v["owner"]}')
            row(f'{v["id"]}: maximum variables per value (Sec 14.6 table)', s['max_variables'], 6, s['max_variables'] == 6)
    row('Q2: Gamma(1/4)^8/(24 pi^4) and the Gamma-ratio form agree (gc:Q2)', idc['Q2']['gamma_eighth'] == idc['Q2']['gamma_ratio'],
        True, idc['Q2']['gamma_eighth'] == idc['Q2']['gamma_ratio'], f'residual {idc["Q2"]["residual"][:10]}...')
    import mpmath as mp
    mp.mp.dps = 60
    q2 = mp.gamma(mp.mpf(1) / 4) ** 8 / (24 * mp.pi ** 4)
    close('Q2 record = Gamma(1/4)^8/(24 pi^4) recomputed here', idc['Q2']['gamma_ratio'], mp.nstr(q2, 58), 1e-55)
    close('Z2 record = 4 G Q2 (gs:Z2exact)', idc['Z2'], mp.nstr(4 * mp.catalan * q2, 58), 1e-55)
    S = {x['name']: x for x in load(ARR / 'summary.json')}
    readme = {'Q': (20, 4), 'P4': (56, 5), 'L': (244, 6), 'Z': (318, 6), 'K': (386, 6), 'P5a': (6024, 8), 'P5b': (9036, 8)}
    got = {k: (S[k]['functions'], S[k]['max_variables']) for k in readme}
    row('Horn values and maximum variables of all seven arrays (package README)', got, readme, got == readme)
    row('array_manifest functions = sum of the seven arrays', am['functions'], sum(v[0] for v in readme.values()),
        am['functions'] == sum(v[0] for v in readme.values()))
    nrows = 0
    for k in readme:
        terms = json.loads(gzip.decompress((ARR / f'{k}_horn.json.gz').read_bytes()))['terms']
        nrows += sum(len(t['upper']) + len(t['lower']) for t in terms)
    row('array_manifest parameter_rows = upper + lower rows of all arrays', nrows, am['parameter_rows'], nrows == am['parameter_rows'])
    hc, ip = load(REC / 'horn_compiler_checks.json'), load(REC / 'insertion_prefactor_checks.json')
    c = hc['counts']
    row('horn_compiler_checks: coefficients, sampled rows, shifts (package README)', [c['coefficients'], c['sampled_rows'], c['shifts']],
        [1038, 519, 12], [c['coefficients'], c['sampled_rows'], c['shifts']] == [1038, 519, 12])
    row('insertion prefactor checks: 336 exact rational, all passed (package README)', [ip['exact_rational_insertion_checks'], ip['all_passed']],
        [336, True], [ip['exact_rational_insertion_checks'], ip['all_passed']] == [336, True])


def full(work):
    compiler_checks(work, SMALL + ('P5a', 'P5b'), 'full compiler')
    run(work, f'{GC}/check_horn_compiler.py', outputs=['verification/general_closed/horn_compiler_checks.json'])
    cmp_exact('horn_compiler_checks.json: recomputed = delivered', work / 'verification/general_closed/horn_compiler_checks.json',
              REC / 'horn_compiler_checks.json')
    for s, f in (('check_primitive_sums.py', 'primitive_sum_checks.json'), ('primitive_series.py', 'P5_raw_checks.json')):
        run(work, f'{GC}/{s}', outputs=[f'verification/general_closed/{f}'])
        cmp_float(f'{f}: recomputed vs delivered (float)', work / 'verification/general_closed' / f, REC / f)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--expected', type=Path, default=PKG / '../../results/closed_forms_general/C0_C5/expected.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    ap.add_argument('--full', action='store_true', help='also the full compiler and the remaining checks (test)')
    a = ap.parse_args()
    exp, out = load(a.expected), a.out.resolve()
    replay(work_copy(out / 'work/replay/pkg'), exp)
    if a.full: full(work_copy(out / 'work/full/pkg'))
    return report(out, 'test' if a.full else 'replay')


if __name__ == '__main__':
    sys.exit(main())
