#!/usr/bin/env python3
"""Replay of the d = 1 resummation numbers from the shipped records (new tool, 2026-10-14). Run from code/resum_d1/.

Reads the final-mode outputs of the verbatim chain (update_2026-10-13/C8_1_ext/...) and checks, with a PASS/FAIL table:
  1. every quoted d = 1 number of the paper owned by this package (../../results/quoted_numbers.json, package
     "resum_d1": \\RSgffOnlyEnd, \\RSoneDmin, \\RSoneDminAt, \\RSoneDatOne, \\RSoneDatOneRange, \\RSoneDenv,
     \\RScoreKeight, \\RScoreKfour) and the 22 resummed values of tab:num1, recomputed from curve_K.csv; the ninth-order
     scenario (\\RSnineImplied, \\RSnineSpread, \\RSnineOnePct, \\RSnineCeightAmp) from c9_predictions_K.csv,
     c9cb8_sensitivity_K.csv and precision_budget_K.csv;
  2. consistency of the plotted data with the curve table: plot_data_1d_K8.json (the input of the figure script) equals
     curve_K.csv at all 1004 points, and its 49 reference rows equal comparison_points_K.csv;
  3. (shipped tree only) the two derived tables regenerated from the frozen inputs in ../../data/inputs with re-pointed
     copy of a verbatim script: references_nrg_rev2.csv (refresh_nrg_rev2.py, NRG values), and
     update_2026-10-14/k4_vs_k8_discrimination.csv (run with --ht <frozen HT record>); both must be byte-identical.
Rules: see the table. Tolerances: exact (same float) for 2; rounding to the written digits for 1 (rsum_lib).
Usage: python3 public/replay_d1.py [--tree DIR] [--out FILE]     (--tree: a rerun copy; default: this folder)
"""
import argparse, csv, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                    # code/resum_d1
RS = PKG.parent.parent                               # Resummation/
sys.path.insert(0, str(RS/'verify'))
import rsum_lib as L

EXT = Path('update_2026-10-13')/'C8_1_ext'
CURVE = EXT/'pipeline_K8'/'results'/'curve_K.csv'
POINTS = EXT/'pipeline_K8'/'results'/'comparison_points_K.csv'
PLOT = EXT/'pipeline_K8'/'plot_data_1d_K8.json'


def rows_at(curve):
    return {round(float(r['Delta_sigma']), 7): r for r in curve}


def envelope(r):
    lo = min(float(r['endpoint_v_K%d_core_min' % k]) for k in (5, 6, 7, 8))
    hi = max(float(r['endpoint_v_K%d_core_max' % k]) for k in (5, 6, 7, 8))
    return lo, hi


def quoted_numbers(tree, T):
    Q, tab = L.quoted(RS/'results'/'quoted_numbers.json')
    curve = list(csv.DictReader((tree/CURVE).open()))
    at = rows_at(curve)
    T.check('curve_K.csv grid', len(curve) == 1004 and at[0.0] is curve[0] and at[0.25] is curve[-1],
            '%d rows' % len(curve), '1004 rows, 0 to 0.25', 'shape of the shipped curve table')
    base = [(float(r['Delta_sigma']), float(r['endpoint_v_K8_L8'])) for r in curve]
    xm, ym = min(base, key=lambda p: p[1])
    T.quoted(Q['\\RSgffOnlyEnd'], [float(at[0.0]['direct_L8'])], 'GFF-only CB8 (direct_L8) at Delta_sigma = 0')
    T.quoted(Q['\\RSoneDmin'], [ym], 'minimum of the baseline endpoint_v_K8_L8 over the 1004-point grid')
    T.quoted(Q['\\RSoneDminAt'], [xm], 'grid point of that minimum')
    T.quoted(Q['\\RSoneDatOne'], [float(at[0.1]['endpoint_v_K8_L8'])], 'baseline at Delta_sigma = 0.1')
    T.quoted(Q['\\RSoneDatOneRange'], list(envelope(at[0.1])), 'K = 5..8 envelope at Delta_sigma = 0.1 (union of core bands)')
    widths = [(envelope(r)[1] - envelope(r)[0], float(r['Delta_sigma'])) for r in curve]
    wmax, xw = max(widths)
    T.quoted(Q['\\RSoneDenv'], [wmax], 'largest width of the K = 5..8 envelope over the grid (at %.4g)' % xw)
    for K, m in ((8, '\\RScoreKeight'), (4, '\\RScoreKfour')):
        r = at[0.05]
        T.quoted(Q[m], [float(r['endpoint_v_K%d_core_max' % K]) - float(r['endpoint_v_K%d_core_min' % K])],
                 'core-band width (N = 6-8, b_L = 2-4, alpha = -1,0,1) at Delta_sigma = 0.05, K = %d' % K)
    # ninth-order scenario (paper: paragraph "Higher orders" of Sec. "Around the generalized free field"): C9 implied by the eighth-order resummations,
    # response of the K = 8 curve to C9, amplification of the C8 term of the input budget
    res = EXT/'pipeline_K8'/'results'
    pred = [r for r in csv.DictReader((tree/res/'c9_predictions_K.csv').open())
            if r['mode'] == 'endpoint_v' and r['b'] == '3' and r['admissible'] == 'True'
            and ((r['method'] == 'CB' and r['K'] in ('4', '8')) or (r['method'] == 'PB' and r['K'] == '8'))]
    c9 = sorted(float(r['C9_prediction']) for r in pred)
    T.check('C9 predictions used', len(pred) == 3 and [r['shape'] for r in pred if r['method'] == 'PB'] == ['[3/5]'],
            '%d rows (%s)' % (len(pred), ', '.join('%s K=%s %s' % (r['method'], r['K'], r['shape']) for r in pred)),
            'CB8 K=4, CB8 K=8, PB[3/5] K=8', 'endpoint_v, b_L = 3: the eighth-order resummations admissible at K = 8, and K = 4 CB8')
    T.quoted(Q['\\RSnineImplied'], [c9[0], c9[-1]], 'smallest and largest C9(1) implied by those three resummations')
    T.quoted(Q['\\RSnineSpread'], [100 * (c9[-1] - c9[0]) / abs(sum(c9) / len(c9))],
             'their spread (max - min) relative to |mean|, in %')
    sens = [r for r in csv.DictReader((tree/res/'c9cb8_sensitivity_K.csv').open())
            if r['mode'] == 'endpoint_v' and r['K'] == '8' and round(float(r['Delta_sigma']), 7) == 0.1]
    T.quoted(Q['\\RSnineOnePct'], [float(sens[0]['change_for_1percent_of_reference'])],
             'K = 8 curve at Delta_sigma = 0.1: change for 1%% of |C9| (reference %s, the CB8 prediction)' % sens[0]['C9_reference'])
    bud = {r['order']: float(r['C8_component_before']) for r in csv.DictReader((tree/res/'precision_budget_K.csv').open())
           if r['K'] == '8' and r['grid'] == 'dense' and round(float(r['Delta_sigma']), 7) == 0.1}
    T.quoted(Q['\\RSnineCeightAmp'], [bud['9'] / bud['8']],
             'C8 term of the input budget at Delta_sigma = 0.1, K = 8: order 9 / order 8 (%.4g / %.4g)' % (bud['9'], bud['8']))
    for row in [t for t in tab if t['package'] == 'resum_d1']:
        r = at[round(float(row['Delta_sigma']), 7)]                 # every coupling of tab:num1 is a grid point
        v = float(r['endpoint_v_K8_L8'])
        ok = L.cell(v, row['text'])[0]
        T.check('%s d=1 %s Resummed' % (row['table'], row['Delta_sigma']), ok, '%.8f' % v, row['text'],
                'baseline CB8 (K = 8) at the grid point, rounded like the table')
    return curve


def plotted_vs_tables(tree, curve, T):
    P = json.loads((tree/PLOT).read_text())
    pc = P['curve']
    ok = len(pc) == len(curve)
    for p, r in zip(pc, curve):
        lo, hi = envelope(r)
        ok &= (float(p['x']) == float(r['Delta_sigma']) and float(p['CB8_K8']) == float(r['endpoint_v_K8_L8']) and
               float(p['env_lo']) == lo and float(p['env_hi']) == hi and float(p['direct_CB8']) == float(r['direct_L8']))
    T.check('plot data = curve table', ok, '%d points' % len(pc), 'identical floats',
            'plot_data_1d_K8.json curve (x, CB8_K8, env_lo, env_hi, direct_CB8) vs curve_K.csv')
    pts = list(csv.DictReader((tree/POINTS).open()))
    ok = len(P['references']) == len(pts) == 49
    for p, r in zip(P['references'], pts):
        ok &= all(str(p[k]) == r[k] for k in ('method', 'x', 'y', 'error', 'stat', 'status'))
        ok &= float(p['method_minus_K8']) == float(r['method_minus_K8'])
    T.check('plot data = comparison points', ok, '%d rows' % len(pts), '49 identical rows',
            'plot_data_1d_K8.json references vs comparison_points_K.csv')


def repoint(src, dst, subs):
    t = src.read_text()
    for old, new in subs:
        assert t.count(old) == 1, (src, old)
        t = t.replace(old, new)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(t)


def regenerate(work, T):
    data = RS/'data'/'inputs'
    # references_nrg_rev2.csv from the frozen NRG table and the 2026-10-12 reference table
    w = work/'repoint'
    shutil.rmtree(w, ignore_errors=True)
    (w/'update_2026-10-12').mkdir(parents=True)
    shutil.copy2(PKG/'update_2026-10-12'/'references_refreshed.csv', w/'update_2026-10-12'/'references_refreshed.csv')
    nrg = (data/'NRG'/'ds13_final.json').resolve()
    src = (PKG/'update_2026-10-13'/'refresh_nrg_rev2.py').read_text()
    src, n = re.subn(r'^NRG = .*$', lambda m: 'NRG = Path(%r)' % str(nrg), src, flags=re.M)   # the one line naming the NRG table
    assert n == 1, 'NRG line of refresh_nrg_rev2.py'
    (w/'update_2026-10-13').mkdir(parents=True, exist_ok=True)
    (w/'update_2026-10-13'/'refresh_nrg_rev2.py').write_text(src)
    r = subprocess.run([sys.executable, '-B', str(w/'update_2026-10-13'/'refresh_nrg_rev2.py')], capture_output=True, text=True)
    new = w/'update_2026-10-13'/'references_nrg_rev2.csv'
    ok = r.returncode == 0 and new.read_bytes() == (PKG/'update_2026-10-13'/'references_nrg_rev2.csv').read_bytes()
    T.check('references_nrg_rev2.csv regenerated', ok, 'exit %d, %s' % (r.returncode, 'identical' if ok else 'differs'),
            'byte-identical', 'refresh_nrg_rev2.py (verbatim; its NRG = ... line re-pointed to data/inputs/NRG/ds13_final.json)')
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
    # k4_vs_k8_discrimination.csv (2026-10-14 version) from the shipped comparison points and the frozen HT record
    ht = (data/'HT'/'HT_1d'/'model_dependence.json').resolve()
    out = w/'k4_vs_k8_discrimination.csv'
    r = subprocess.run([sys.executable, '-B', str(PKG/'update_2026-10-14'/'k4_vs_k8_discrimination.py'), '--ht', str(ht),
                        '--out', str(out)], capture_output=True, text=True)
    ok = r.returncode == 0 and out.read_bytes() == (PKG/'update_2026-10-14'/'k4_vs_k8_discrimination.csv').read_bytes()
    T.check('k4_vs_k8_discrimination.csv regenerated', ok, 'exit %d, %s' % (r.returncode, 'identical' if ok else 'differs'),
            'byte-identical', 'update_2026-10-14/k4_vs_k8_discrimination.py (verbatim; --ht data/inputs/HT/HT_1d/model_dependence.json)')
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default=str(PKG))
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    tree, work = Path(a.tree).resolve(), Path(a.work).resolve()
    T = L.Table('resum_d1 replay (%s)' % ('shipped records' if tree == PKG else 'rerun copy'))
    curve = quoted_numbers(tree, T)
    plotted_vs_tables(tree, curve, T)
    if tree == PKG:
        regenerate(work, T)
    return T.report(a.out or work/'replay_d1.txt')


if __name__ == '__main__':
    sys.exit(main())
