#!/usr/bin/env python3
"""Replay (and test) of lri_general_special_functions_update: C0..C5 at general dimension (note Sections 12-13).

Run from the package folder (GFF/code/lri_general_special_functions_update) as `make -f public.mk replay` or
`make -f public.mk test` (= replay plus --full). Nothing shipped is modified: the delivered scripts write their records in
place, so they run in a fresh copy of the package under public/out/work/.

replay (about 5 s, one core):
  1. integrity of the 71 shipped source files (public/SOURCE_SHA256SUMS, hashes from the bundle MANIFEST.json; complete).
  2. reruns sum4.py, sum5.py, exact_audit.py (exact SymPy fixed-point assembly of the saved graph rows; asserts the general
     C4, C5, the d=1 specialization and the cancellation of the mass Gamma terms), assemble_results.py (C0..C5 at d=1,2,3
     from the saved spectral masters, mpmath 50 digits) and symbolic_checks.py (C1..C3 by Lagrange inversion), and compares
     each output with the delivered record.
  3. compares the general formulas printed in the note (expected.json 'formulas') with the records, symbolically.
  4. recomputes every number the note and the paper quote from this package at the printed digits (expected.json 'values')
     and the cross-checks against values owned by other units (expected.json 'cross_checks').
test (--full, about 2.5 min on one core): additionally regenerates, in a second copy, everything the replay reads:
  derive_A.py, collect.py 3 0 8 / 4 0 27 / 5 0 129 (the graph reduction), sum4/sum5/exact_audit on the new rows,
  spectral_evaluate.py (the six masters at d=2,3,4) and assemble_results.py on the new masters, and runs the remaining
  delivered checks: graph_inventory.py + inventory_checks.py, tetrahedron.py, two_loop_master.py, primitive_spectral.py,
  kappa_mb.py, residue_checks.py, ordered_series_checks.py, wheel_spectrum.py, hypergeometric_series.py (prints only).
  Not run: check_A_d1.py (its input, an absent /mnt/data folder of the delivering session, is not part of the delivery;
  its record A_d1_checks.json ships as delivered).

Tolerances. SymPy and mpmath records are deterministic: compared exactly after dropping timing keys (tier 'exact' of
public/common.py). numpy/scipy records (spectral masters, tetrahedron, primitive spectral sums, kappa_mb, ordered series,
wheel spectrum): values relative 1e-8; difference-type fields and the least-squares angular-tail fits absolute 1e-6
(tier 'float'); coefficients reassembled from regenerated masters: absolute 1e-10. Quoted numbers: the record rounded
half-even to the printed decimals must equal the printed text. Distances of the quoted values to their rounding
boundaries: C2(2) 3.0e-13, C2(3) 5.4e-14 (exact polygamma values, no drift), C3(2) 1.3e-13 (exact Q2, no drift),
C3(3) 3.0e-13 (spectral Q3; drift between platforms below 6e-14), C4 and C5 at d=2,3 between 1.4e-10 and 2.7e-10
(drift below 3.1e-12). Cross-checks: coefficients absolute 1e-11 (C3(2) 1e-24: exact Q2 against the paper's 25 digits),
masters relative 1e-11 (the spectral masters of this package are accurate to about 1e-13 relative).
Checked: the delivered records (made on Linux with Python 3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0,
mpmath 1.3.0) were reproduced on macOS arm64 with Python 3.10.12, numpy 1.24.4, scipy 1.11.1, sympy 1.12,
mpmath 1.3.0 (gmpy2 backend), and the replay also with Python 3.10.11, numpy 1.23.5, scipy 1.10.0, sympy 1.11.1,
mpmath 1.2.1: all exact-tier records identical; float tier: masters within 4.6e-11 relative, tail fits within
2.2e-9 absolute, differences within 1.2e-8 absolute.
"""
import argparse, sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, row, load, verify_sums, work_copy, run, cmp_exact, cmp_float, quoted, close, report)  # noqa: E402

GS = 'code/general_special'
REC = PKG / 'verification/general_special'
# what each delivered script of code/general_special writes (in its own folder); deleted in the copy before each run
WRITES = {'sum4.py': 'sum4.json', 'sum5.py': 'sum5.json', 'exact_audit.py': 'exact_checks.json',
          'assemble_results.py': 'coefficient_values_new.json', 'derive_A.py': 'A_regular.json',
          'spectral_evaluate.py': 'spectral_master_values.json', 'kappa_mb.py': 'kappa_mb_checks.json',
          'residue_checks.py': 'local_residue_checks.json', 'ordered_series_checks.py': 'ordered_series_checks.json',
          'wheel_spectrum.py': 'wheel_spectral_raw.json'}


def gs_run(work, script, *args):
    out = f'rows_{args[0]}_{args[1]}_{args[2]}.json' if script == 'collect.py' else WRITES.get(script)
    return run(work, f'{GS}/{script}', *args, outputs=[f'{GS}/{out}'] if out else [])
NAMES = 'A R U V X M N Q K Z P4 P5 L d'.split()


def sym(expr):
    import sympy
    loc = {n: sympy.Symbol(n) for n in NAMES}; loc['Rational'] = sympy.Rational
    return sympy.sympify(expr, locals=loc)


def coeff_rows(path):
    rows = load(path)
    return {(r['d'], r.get('spins')): r for r in rows}


def replay(work, exp):
    verify_sums(PKG / 'public/SOURCE_SHA256SUMS')
    # delivered copies: the scripts write into code/general_special/, the delivered records sit in verification/
    for f in ('sum4.json', 'sum5.json', 'exact_checks.json', 'coefficient_values_new.json', 'spectral_master_values.json',
              'rows_3_0_8.json', 'rows_4_0_27.json', 'rows_5_0_129.json'):
        cmp_exact(f'shipped {GS}/{f} = verification copy', PKG / GS / f, REC / f)
    for s in ('sum4.py', 'sum5.py', 'exact_audit.py', 'assemble_results.py'):
        gs_run(work, s)
    for f in ('sum4.json', 'sum5.json', 'exact_checks.json', 'coefficient_values_new.json'):
        cmp_exact(f'{f}: recomputed = delivered record', work / GS / f, REC / f)
    run(work, 'code/symbolic_checks.py', '--output', work / 'new_symbolic_checks.json', show='--output <copy>')
    cmp_exact('symbolic_checks.json: recomputed = delivered record', work / 'new_symbolic_checks.json',
              PKG / 'verification/symbolic_checks.json')

    # --- general formulas (note gd:C03, gd:bc3, gs:C0C4, gs:C5, gs:b4, gs:c4, gs:D4, gs:D5)
    import sympy
    ex, sc, F = load(REC / 'exact_checks.json'), load(PKG / 'verification/symbolic_checks.json'), exp['formulas']
    for k in ('C1', 'C2', 'C3'):
        row(f'{k}(d) = {F[k]["expr"]} (Lagrange inversion residual)', sc['checks'][k], '0', sc['checks'][k] == '0', F[k]['note'])
    row('symbolic_checks all_exact', sc['all_exact'], True, sc['all_exact'] is True)
    for k in ('b3', 'c3', 'C4', 'C5', 'b4', 'c4', 'D4', 'D5'):
        ok = sympy.expand(sym(ex[k]) - sym(F[k]['expr'])) == 0
        row(f'{k}: note formula = exact_checks.json {k}', 'equal' if ok else 'differs', 'symbolically equal', ok, F[k]['note'])
    for k, v in ex['checks'].items():
        row(f'exact_checks {k}', v, True, v is True)
    gr = ex['graph_rows']
    row('graph rows (three, four nonprimitive, five regular, wheel, primitive, zero)',
        [gr[k] for k in ('three', 'four_nonprimitive', 'five_regular_nonzero', 'five_wheel', 'five_primitive', 'five_zero_combined')],
        [8, 26, 92, 6, 3, 28], [gr[k] for k in ('three', 'four_nonprimitive', 'five_regular_nonzero', 'five_wheel',
                                                 'five_primitive', 'five_zero_combined')] == [8, 26, 92, 6, 3, 28],
        'note App. A l.12449 (26 + 92 + 6 + 3 + 28 rows)')

    # --- quoted values
    cv = coeff_rows(REC / 'coefficient_values_new.json')
    idx = {'C2': 2, 'C3': 3, 'C4': 4, 'C5': 5}
    for v in exp['values']:
        if v['package'] != PKG.name: continue
        name, d = v['id'].split('(')[0], int(v['id'].split('(')[1][0])
        val = cv[(d, 512)]['coefficients'][idx[name]]
        quoted(f'{v["id"]} ({v["note"] or v["paper"]})', val, v['printed'], f'{v["paper"]}; owner {v["owner"]}')
        same = all(Decimal(cv[(d, s)]['coefficients'][idx[name]]).quantize(Decimal(1).scaleb(-len(v['printed'].split('.')[1])))
                   == Decimal(v['printed']) for s in (128, 256, 512))
        row(f'{v["id"]}: spin/node settings 128/384, 256/512, 512/768 round alike', same, True, same)
    import mpmath as mp
    mp.mp.dps = 50
    q2 = mp.gamma(mp.mpf(1) / 4) ** 8 / (24 * mp.pi ** 4)
    close('d=2 row: Q = Gamma(1/4)^8/(24 pi^4) (gc:Q2)', cv[(2, 512)]['Q'], mp.nstr(q2, 45), 1e-30)
    close('d=2 row: Z = 4 G Q2 (gs:Z2exact)', cv[(2, 512)]['Z'], mp.nstr(4 * mp.catalan * q2, 45), 1e-30)

    # --- cross-checks with values owned by other units
    X = {c['id']: c for c in exp['cross_checks']}
    r2, r3 = cv[(2, 512)], cv[(3, 512)]
    for cid, val, tol in (('C4(2) closed form', r2['coefficients'][4], 1e-11), ('C5(2) closed form', r2['coefficients'][5], 1e-11),
                          ('C3(2) closed form', r2['coefficients'][3], 1e-24),
                          ('C4(3) (rank-two masters)', r3['coefficients'][4], 1e-11),
                          ('C5(3) (50 digits)', r3['coefficients'][5], 1e-11)):
        close(f'cross-check {cid} (owner {X[cid]["owner"]})', val, X[cid]['value'], tol, note=X[cid]['source'])
    for cid, key, r in (('L2', 'L', r2), ('K2', 'K', r2), ('Q3', 'Q', r3), ('P4(3)', 'P4', r3), ('P5(3)', 'P5', r3),
                        ('K3', 'K', r3), ('L3', 'L', r3), ('Z3', 'Z', r3)):
        close(f'cross-check master {cid} (owner {X[cid]["owner"]})', r[key], X[cid]['value'], 1e-11, relative=True,
              note=X[cid]['source'])
    d1 = cv[(1, None)]['coefficients']
    for n, (val, txt) in enumerate(zip(d1, X['C0..C5(1)']['value'])):
        if n == 1: close('cross-check C1(1) = -1/6', val, txt, 1e-36); continue
        quoted(f'cross-check C{n}(1) via the general formula (owner C71d)', val, txt, X['C0..C5(1)']['source'])


def full(work):
    for s, a in (('derive_A.py', ()), ('collect.py', ('3', '0', '8')), ('collect.py', ('4', '0', '27')),
                 ('collect.py', ('5', '0', '129')), ('sum4.py', ()), ('sum5.py', ()), ('exact_audit.py', ())):
        gs_run(work, s, *a)
    for f in ('A_regular.json', 'rows_3_0_8.json', 'rows_4_0_27.json', 'rows_5_0_129.json', 'sum4.json', 'sum5.json',
              'exact_checks.json'):
        cmp_exact(f'{f}: regenerated from the graphs = delivered record', work / GS / f, REC / f)
    run(work, 'code/graph_inventory.py', '--output', work / 'new_graph_inventory.json', show='--output <copy>')
    cmp_exact('graph_inventory.json: regenerated = delivered', work / 'new_graph_inventory.json', PKG / 'verification/graph_inventory.json')
    run(work, 'code/inventory_checks.py', work / 'new_graph_inventory.json', '--output', work / 'new_inventory_checks.json',
        show='<copy>/new_graph_inventory.json --output <copy>')
    cmp_exact('inventory_checks.json: recomputed = delivered', work / 'new_inventory_checks.json', PKG / 'verification/inventory_checks.json')
    for s, rec, tier in (('tetrahedron', 'tetrahedron_checks', cmp_float), ('two_loop_master', 'two_loop_checks', cmp_exact),
                         ('primitive_spectral', 'primitive_spectral_checks', cmp_float)):
        run(work, f'code/{s}.py', '--output', work / f'new_{rec}.json', show='--output <copy>')
        tier(f'{rec}.json: recomputed vs delivered ({tier.__name__[4:]})', work / f'new_{rec}.json', PKG / f'verification/{rec}.json')
    gs_run(work, 'spectral_evaluate.py')
    cmp_float('spectral_master_values.json: regenerated masters vs delivered (float)', work / GS / 'spectral_master_values.json',
              REC / 'spectral_master_values.json')
    gs_run(work, 'assemble_results.py')
    new, old = coeff_rows(work / GS / 'coefficient_values_new.json'), coeff_rows(REC / 'coefficient_values_new.json')
    worst = max(abs(Decimal(a) - Decimal(b)) for k in old for a, b in zip(new[k]['coefficients'], old[k]['coefficients']))
    row('C0..C5 from regenerated masters vs delivered record (all rows)', f'max abs diff {float(worst):.1e}', '<= 1e-10',
        worst <= Decimal('1e-10'))
    for s, rec, tier in (('kappa_mb.py', 'kappa_mb_checks.json', cmp_float), ('residue_checks.py', 'local_residue_checks.json', cmp_exact),
                         ('ordered_series_checks.py', 'ordered_series_checks.json', cmp_float),
                         ('wheel_spectrum.py', 'wheel_spectral_raw.json', cmp_float)):
        gs_run(work, s)
        tier(f'{rec}: recomputed vs delivered ({tier.__name__[4:]})', work / GS / rec, REC / rec)
    gs_run(work, 'hypergeometric_series.py')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--expected', type=Path, default=PKG / '../../results/closed_forms_general/C0_C5/expected.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    ap.add_argument('--full', action='store_true', help='also regenerate the inputs and run the remaining checks (test)')
    a = ap.parse_args()
    exp = load(a.expected)
    out = a.out.resolve()
    replay(work_copy(out / 'work/replay/pkg'), exp)
    if a.full: full(work_copy(out / 'work/full/pkg'))
    return report(out, 'test' if a.full else 'replay')


if __name__ == '__main__':
    sys.exit(main())
