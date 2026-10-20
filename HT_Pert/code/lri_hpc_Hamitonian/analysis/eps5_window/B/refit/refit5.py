#!/usr/bin/env python3
"""Refit C4/C5 of the raw thermal HT data with the complete Dconn correction (implementation B).

Corrections per even L (all from implementation B's own code except the raw thermal data):
  dC4g, dC5g   : package-equivalent g^2D operator response (capped space; = lri_eh d5_all to 9e-11)
  dC5g3        : third-order bubble g1^3 W on intermediates (= -2 dC4g exactly)
  sh4          : Dconn eps^4 reference-row shift = -B4/3 (topsum closed form, L<=288)
  rows5        : Dconn eps^4/eps^5 reference rows on C5 = rho5A*A4 + rho5B*B4 - B5/3
                 (rho from the capped space; A4,B4 closed form; B5 exact vacuum windows for L<=Lx, fitted beyond)
Correction sets (see SETS). C6, C7 raw. Fit machinery = diagnose_systematic.thermal_fit (copy, with Coff option).
"""
import json, sys, math
from pathlib import Path
import numpy as np
S = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(S)); sys.path.insert(0, str(S.parent))
from analyze_joint import MODELS, load, ls, eseries, design, C2, C3
import mpmath as mp
from fitwin import fit as wfit, F as WF

EXACT = {4: 45.42488010356, 5: -731.13947662454}
K = 0.06161193084267987
B5LOG = 5.5388e-4


def thermal_fit(L, Cfit, w, terms_of_k, Coff=None, fixed=None, free_exponents=False, maxorder=7):
    Coff = Cfit if Coff is None else Coff
    fixed = fixed or {}
    L = np.asarray(L, float); x = Cfit[:, 2] - C2
    lim = {2: C2, 3: C3}; w = dict(w); diag = {}
    for k in range(4, maxorder + 1):
        free = free_exponents and k >= 5
        if free: w[k - 2] = 0
        e = eseries(L, w, k - 2)
        off = np.zeros(len(L))
        for j in range(1, k - 1):
            off -= e[j] * (Coff[:, k - j] - lim[k - j])
        X = design(L, x, terms_of_k(k))
        if free: X = np.column_stack([X, -np.log(L) * x])
        y = Cfit[:, k] - off
        if k in fixed:
            p, d = ls(X[:, 1:], y - fixed[k]); p = np.r_[fixed[k], p]
        else:
            p, d = ls(X, y)
        d['max_residual'] = float(max(abs(X @ p - y)))
        diag[k] = d; lim[k] = float(p[0])
        if free: w[k - 2] = float(p[-1])
    return lim, diag


def const_terms(name): return lambda k: MODELS[name]


def corrections(Ls, Lx=None):
    B = S.parent
    rr = json.loads((B / 'rowresp_4_118.json').read_text())
    top = {}
    for line in open(B / 'top_a.jsonl'):
        r = json.loads(line); top[r['L']] = r
    vac = {}
    for f in B.glob('vacwin_L*.json'):
        w = json.loads(f.read_text()); L = w['L']; E = w['E']; j = 2 * L
        c = lambda jj: np.array(E[str(jj)]['conn'])
        vac[L] = dict(A=c(j) - c(j - 1), B=c(j) - c(j - 2))
    top5 = {}
    if (B / 'top5.jsonl').exists():
        for line in open(B / 'top5.jsonl'):
            r = json.loads(line); top5[r['L']] = r
    Lx_in = Lx
    Lx = Lx or max(vac)
    Lfit = [L for L in sorted(vac) if 40 <= L <= Lx]
    bases = {'a+': ['1', 'lg', '1/L', 'lg/L', '1/L2', 'lg/L2', '1/L3'], 'b+': ['1', '1/L', 'lg/L', 'lg2/L', '1/L2', 'lg/L2', '1/L3'],
             'c': ['1', 'lg', 'L-.5', '1/L', 'lg/L', '1/L2'], 'd': ['1', 'lg', 'lg2/L', 'lg/L', '1/L', '1/L2', 'lg/L2'],
             'e': ['1', 'lg', 'lg2', '1/L', 'lg/L', '1/L2', 'lg/L2'], 'f': ['1', 'L-.5', 'lgL-.5', '1/L', 'lg/L', '1/L2']}
    pB = {bn: wfit(Lfit, [vac[L]['B'][5] for L in Lfit], [WF[x] for x in b])[0] for bn, b in bases.items()}
    out = {}
    for L in Ls:
        L = int(L); x = rr[str(L)]
        A4 = top[L]['Yc'] / 81; B4 = (top[L]['Yc'] + top[L]['Z']) / 81
        if L in top5 and 'B5' in top5[L] and (Lx_in is None or L <= Lx_in):
            B5 = top5[L]['B5']; B5spread = 0.
            if L in vac: assert abs(vac[L]['B'][5] - B5) < 1e-10
        elif L in vac and L <= Lx:
            B5 = vac[L]['B'][5]; B5spread = 0.
            assert abs(vac[L]['A'][4] - A4) < 1e-11 and abs(vac[L]['B'][4] - B4) < 1e-11
        else:
            preds = [sum(p * float(WF[n](mp.mpf(L))) for p, n in zip(pB[bn], bases[bn])) for bn in bases]
            B5 = float(np.median(preds)); B5spread = float(max(preds) - min(preds))
        dC4g = x['g2D']['dC'][4]; dC5g = x['g2D']['dC'][5]
        dC5g3 = x['g2D+g3W']['dC'][5] - dC5g
        rho5A = x['rowA4']['dC'][5]; rho5B = x['rowB4']['dC'][5]
        out[L] = dict(dC4g=dC4g, dC5g=dC5g, dC5g3=dC5g3, sh4=-B4 / 3, A4=A4, B4=B4, B5=B5, B5spread=B5spread,
                      rho5A=rho5A, rho5B=rho5B, rows5=rho5A * A4 + rho5B * B4 - B5 / 3, rows5_4=rho5A * A4 + rho5B * B4)
        out[L]['dC5_complete'] = dC5g + dC5g3 + out[L]['rows5']
        out[L]['dC4_complete'] = dC4g + out[L]['sh4']
    return out


SETS = {
    'raw': lambda c, z: (0., 0.),
    'pkg': lambda c, z: (c['dC4g'] - z / 17496, c['dC5g'] - B5LOG * z),
    'pkg+sh4': lambda c, z: (c['dC4g'] - z / 17496 + c['sh4'], c['dC5g'] - B5LOG * z),
    'pkg+sh4+g3W(log kept)': lambda c, z: (c['dC4g'] - z / 17496 + c['sh4'], c['dC5g'] - B5LOG * z + c['dC5g3']),
    'pkg+sh4+g3W': lambda c, z: (c['dC4g'] - z / 17496 + c['sh4'], c['dC5g'] - B5LOG * z + c['dC5g3'] + 2 * z / 17496),
    'Dconn': lambda c, z: (c['dC4g'] - z / 17496 + c['sh4'], c['dC5g'] - B5LOG * z + c['dC5g3'] + 2 * z / 17496 + c['rows5']),
    'Dconn(g3W log kept)': lambda c, z: (c['dC4g'] - z / 17496 + c['sh4'], c['dC5g'] - B5LOG * z + c['dC5g3'] + c['rows5']),
    'Dconn(no log subtraction)': lambda c, z: (c['dC4g'] + c['sh4'], c['dC5g'] + c['dC5g3'] + c['rows5']),
}


def main(hi=118, Lx=None, los=(40, 50, 60, 70), tag=''):
    th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
    L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'] for r in th])
    ex = json.loads((S / 'extended_summary.json').read_text())
    w_ext = {int(k): v_ for k, v_ in ex['gap_reference']['extended'].items()}
    w_orig = {int(k): v_ for k, v_ in ex['gap_reference']['original'].items()}
    keep = (L >= 4) & (L <= hi)
    L = L[keep]; C = C[keep]
    corr = corrections(L, Lx)
    z = np.log(L)
    variants = {name: (const_terms(name), w_ext, False) for name in MODELS if name != 'minimal'}
    for name in ('A', 'B', 'D'):
        variants[f'{name}+free_exponents'] = (const_terms(name), w_ext, True)
    for name in ('A', 'D'):
        variants[f'{name}+z^j/L'] = (lambda k, n=name: MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]], w_ext, False)
        variants[f'{name}+z^j/L^1.5'] = (lambda k, n=name: MODELS[n] + [(1.5, j) for j in range(2, k - 1) if (1.5, j) not in MODELS[n]], w_ext, False)
        variants[f'{name}+L^-0.75'] = (lambda k, n=name: MODELS[n] + [(0.75, 0)], w_ext, False)
    variants['E+L^-0.5'] = (lambda k: MODELS['E'] + [(0.5, 0)], w_ext, False)
    variants['E+L^-0.5,zL^-0.5'] = (lambda k: MODELS['E'] + [(0.5, 0), (0.5, 1)], w_ext, False)
    Ccorr = {}
    for sname, fn in SETS.items():
        Cc = C.copy()
        for i, l in enumerate(L):
            d4, d5 = fn(corr[int(l)], math.log(l))
            Cc[i, 4] += d4; Cc[i, 5] += d5
        Ccorr[sname] = Cc
    rows = []
    for lo in los:
        m = (L >= lo) & (L <= hi)
        for label, (tk, w, free) in variants.items():
            row = dict(lo=lo, hi=hi, variant=label)
            try:
                for sname, Cc in Ccorr.items():
                    lim, dg = thermal_fit(L[m], Cc[m], w, tk, free_exponents=free)
                    row[sname] = {4: lim[4], 5: lim[5], 'res4': dg[4]['max_residual'], 'res5': dg[5]['max_residual']}
            except ValueError:
                continue
            rows.append(row)
    out = dict(hi=hi, Lx=Lx, corrections={int(k): v for k, v in corr.items()}, rows=rows)
    (S / f'refit5{tag}.json').write_text(json.dumps(out, indent=1, default=float))
    names = list(SETS)
    print(f"hi={hi} B5 exact for L<={Lx or 'max'}; C5 intercepts (miss vs exact {EXACT[5]})")
    print(f"{'lo':>3} {'variant':20s} " + ' '.join(f'{n[:14]:>14s}' for n in names))
    for r in rows:
        print(f"{r['lo']:3d} {r['variant']:20s} " + ' '.join(f"{r[n][5]:14.4f}" for n in names))
    print('C4:')
    for r in rows:
        print(f"{r['lo']:3d} {r['variant']:20s} " + ' '.join(f"{r[n][4]:14.5f}" for n in names[:3]) + f"  res5(raw/Dconn) {r['raw']['res5']:.1e} {r['Dconn']['res5']:.1e}")
    return out


if __name__ == '__main__':
    hi = int(sys.argv[1]) if len(sys.argv) > 1 else 118
    Lx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    main(hi, Lx, tag=f'_hi{hi}' + (f'_Lx{Lx}' if Lx else ''))
