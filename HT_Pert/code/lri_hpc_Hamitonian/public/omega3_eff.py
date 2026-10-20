#!/usr/bin/env python3
"""Effective omega_3 of the d = 1 HT tail fits that reach the exact C5 (HT_Pert/code/lri_hpc_Hamitonian).

The joint tail model ties the Lambda^{-1/2} log Lambda amplitude of C5(Lambda) to the phi^6-gap exponent
omega_3 = 556.2 (analysis/extended/extended_summary.json, gap_reference.extended). Fits on the window-corrected data
(Dconn: C4 + dC4_g2D + shift4, C5 + dC5_Dconn from analysis/eps5_window/reconcile/dC_reconciled.json) that free this
amplitude land near the exact C5. This script measures the omega_3 they effectively use, in two families:
  free   free-exponent fits, analysis/extended/analyze_joint.py ThermalModel(MODELS[b], omega, free_exponents=True)
         on Lambda in [lo, 118], b in A, B, D, E (as analysis/eps5_window/challenge-theory/freeomega.py, which only
         prints them; it uses lo 40, 60, 70); omega_3,eff = the fitted omega_3.
  E+zh   basis E plus a free column c Lambda^{-1/2} log Lambda at orders 4 and 5, fitted with the re-implementation
         analysis/eps5_window/challenge-num/myfit.py (as challenge-num/hzh.py, which prints the fits but not c).
         With x = C2(Lambda) - C2 ~ a Lambda^{-1/2} (a = least-squares slope of x on Lambda^{-1/2} over the window,
         about -0.280), the column equals a shift of omega_3 in the tied term -omega_3 x log Lambda:
         omega_3,eff = omega_3 - c / a  (= omega_3 + c/0.2795, the reading of the eps^5 numerical skeptic).
lo runs over 40, 50, 60, 70 in both families. Rule for the quoted range (fixed here, applied to every row): keep the
fits whose C5 lands within 0.25 of the exact C5 = -731.13947662454 (|miss| <= 0.25, the size of the freed-tail
misses -0.217..+0.058 of challenge-theory/freelead2.json), and quote min and max of omega_3,eff rounded to the nearest
10. Writes JSON (every fit, the selection, the range) to --out and prints a summary.
Needs a re-pointed copy of the analysis (public/repoint.py): --tree <work>/tree.
usage: python3 public/omega3_eff.py --tree .work/tree --out .work/omega3_eff.json"""
import argparse
import json
import os
import sys

import numpy as np

EX5 = -731.13947662454
SEL = 0.25
LOS = (40, 50, 60, 70)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    ext = os.path.join(tree, 'analysis', 'extended')
    sys.dont_write_bytecode = True
    sys.path.insert(0, ext)
    sys.path.insert(0, os.path.join(tree, 'analysis', 'eps5_window', 'challenge-num'))
    from analyze_joint import MODELS, load, ThermalModel  # noqa: E402  (shipped model code)
    import myfit  # noqa: E402  (shipped re-implementation, re-pointed copy)
    R = {int(k): v for k, v in json.load(open(os.path.join(tree, 'analysis', 'eps5_window', 'reconcile',
                                                           'dC_reconciled.json'))).items()}
    w = {int(k): v for k, v in json.load(open(os.path.join(ext, 'extended_summary.json')))
         ['gap_reference']['extended'].items()}
    cwd = os.getcwd()
    os.chdir(ext)
    th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
    os.chdir(cwd)
    L = np.array([r['cutoff'] for r in th], float)
    C = np.array([r['C'][:6] for r in th])
    col = lambda k, LL: np.array([R[int(l)][k] for l in LL])
    X = C.copy()
    X[:, 4] += col('dC4_g2D', L) + col('shift4', L)
    X[:, 5] += col('dC5_Dconn', L)
    rows = []
    for lo in LOS:
        m = (L >= lo) & (L <= 118)
        for b in 'ABDE':
            try:
                tm = ThermalModel(MODELS[b], w, free_exponents=True).fit(L[m], X[m], maxorder=5)
            except ValueError as e:
                rows.append(dict(family='free', basis=b, lo=lo, error=str(e)))
                continue
            rows.append(dict(family='free', basis=b, lo=lo, C4=float(tm.lim[4]), C5=float(tm.lim[5]),
                             miss5=float(tm.lim[5] - EX5), omega3_eff=float(tm.w[3])))
    LL, CC = myfit.rows()
    D = CC.copy()
    D[:, 4] += col('dC4_g2D', LL) + col('shift4', LL)
    D[:, 5] += col('dC5_Dconn', LL)
    tb = myfit.BASES['E'] + [(0.5, 1)]
    for lo in LOS:
        m = LL >= lo
        Lm, Dm = LL[m], D[m]
        lim, info = myfit.fit(Lm, Dm, tb, tb, w)
        x = Dm[:, 2] - myfit.C2INF
        lim2 = {2: myfit.C2INF, 3: myfit.C3INF, 4: lim[4]}
        e = myfit.ecoef(Lm, w, 3)
        y = Dm[:, 5] + sum(e[j] * (Dm[:, 5 - j] - lim2[5 - j]) for j in range(1, 4))
        Xd = np.column_stack([np.ones_like(Lm), x] + [Lm ** (-p) * np.log(Lm) ** j for p, j in tb])
        p, res, gain = myfit.solve(Xd, y)
        slope = float(np.sum(x * Lm ** -0.5) / np.sum(Lm ** -1.0))
        rows.append(dict(family='E+zh', basis='E', lo=lo, C4=float(lim[4]), C5=float(lim[5]),
                         miss5=float(lim[5] - EX5), zh_coefficient=float(p[-1]), x_slope=slope,
                         omega3_eff=float(w[3] - p[-1] / slope), max_residual5=float(res)))
    sel = [r for r in rows if 'omega3_eff' in r and abs(r['miss5']) <= SEL]
    lo_v, hi_v = min(r['omega3_eff'] for r in sel), max(r['omega3_eff'] for r in sel)
    out = dict(about=__doc__.split('\n')[0], omega3_gap=w[3], exact_C5=EX5, selection=f'|C5 - exact| <= {SEL}',
               lo_values=list(LOS), rows=rows, selected=[(r['family'], r['basis'], r['lo']) for r in sel],
               excluded=[(r['family'], r['basis'], r['lo'], round(r.get('miss5', float('nan')), 3)) for r in rows
                         if r not in sel],
               range=[lo_v, hi_v], quoted_rule='min and max over the selected fits, each rounded to the nearest 10',
               range_rounded=[int(round(lo_v, -1)), int(round(hi_v, -1))])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    for r in rows:
        if 'omega3_eff' in r:
            print(f"{r['family']:5s} {r['basis']} lo={r['lo']}: C5 miss {r['miss5']:+.3f}  omega3_eff {r['omega3_eff']:.1f}"
                  f"{'' if r in sel else '  (not selected)'}")
    print(f"omega3_eff over {len(sel)} selected fits: {lo_v:.1f} .. {hi_v:.1f} -> {out['range_rounded'][0]}--"
          f"{out['range_rounded'][1]} (gap omega3 {w[3]:.1f})")


if __name__ == '__main__':
    main()
