#!/usr/bin/env python3
"""Model dependence of the d = 1 HT limits at 0.075 <= Ds <= 0.2 (diagnostic; added 2026-10-13 after the NRG re-analysis).

The quoted HT errors are half-spreads of one fit family (F1/F2/F3 x N_min) on one prescription (consistent window).
This script estimates the two model dependences the half-spread does not cover:
  tail model    alternative descriptions of the approach N -> infinity of the same window series:
                F4 = D + a N^-w1 + b N^-(w1+dw) with both exponents free (N_min 12..20, same acceptance);
                a drifting exponent: omega_eff(N) continued linearly in ln N from its last four values and the slope at
                N = 40 integrated to infinity;
                the bracket [Delta(40), Delta(40) + slope(40)/omega_eff(35)], which holds if Delta(N) keeps rising and
                omega_eff does not decrease beyond N = 40 (no fit).
  prescription  the same truncation without the window (raw, energy zero-mode basis, prod1-7 composite series of
                extrapolate.py, N <= 40 at Ds >= 0.1, N <= 28 at 0.075) extrapolated with the same fit family.
The shifts are reported as measured and are not combined into a model-dependence error: HT has no strict error bar,
and a scale built after the HT-NRG gap was seen would read as agreement within errors (author's decision, 2026-10-14).
Comparison with NRG: (HT - NRG) / sqrt(half-spread^2 + NRG total^2), fit errors only.
Usage: python3 public/model_dependence_ht1d.py [--nrg ../../results/HT_1d/nrg_reference.json] [--json model_dependence.json] > model_dependence.md
The shipped model_dependence.json was computed in the production analysis environment (Python 3.10.12, numpy 1.24.4,
scipy 1.11.1); the F4 refits differ slightly in other versions (replay: exact from the shipped rows, refit within 2e-4).
"""
import argparse, contextlib, io, json, math, sys, warnings
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.optimize import curve_fit
warnings.filterwarnings('ignore')
PKG = Path(__file__).resolve().parents[1]
import os, shutil, tempfile

def F4(N, D, a_, w1, b, dw): return D + a_ * N ** -w1 + b * N ** -(w1 + dw)
def fitF4(N, y):
    best = None
    for w0 in (0.4, 0.6, 0.8, 1.0):
        for dw0 in (0.3, 0.7, 1.5):
            for bs in (1, -1):
                try: p, _ = curve_fit(F4, N, y, p0=[y[-1] + 0.01, -0.05, w0, bs * 0.05, dw0], bounds=([0, -10, 0.05, -10, 0.05], [2, 10, 4, 10, 6]), maxfev=40000)
                except Exception: continue
                r = float(np.sqrt(np.mean((F4(N, *p) - y) ** 2)))
                if best is None or r < best[1]: best = (p, r)
    return best
def local(N, y):
    s = [(math.sqrt(N[i] * N[i + 1]), (y[i + 1] - y[i]) / math.log(N[i + 1] / N[i])) for i in range(len(N) - 1)]
    om = [(s[i + 1][0], -math.log(s[i + 2][1] / s[i][1]) / math.log(s[i + 2][0] / s[i][0])) for i in range(0, len(s) - 2, 2) if s[i][1] * s[i + 2][1] > 0]
    return s, om

def compute(nrg_path, X=None):
    """Rows for Ds = 0.2 .. 0.075. X: dens_v1 extrapolation list (default: the shipped one)."""
    tmp = Path(tempfile.mkdtemp()); [shutil.copy2(PKG / f, tmp / f) for f in ('extrapolate.py', 'collected.json')]
    sys.path.insert(0, str(tmp))
    with contextlib.redirect_stdout(io.StringIO()):
        import extrapolate as E
    X = {x['delta']: x for x in (X or json.loads((PKG / 'dens_v1_extrapolation.json').read_text()))}
    NR = {round(r['ds'], 6): r for r in json.loads(Path(nrg_path).read_text())}
    RAW = {r['delta']: r for r in json.loads((PKG / 'extrapolation.json').read_text())['results'] if r['prescription'] == 'raw'}
    rows = []
    for d in (0.2, 0.175, 0.15, 0.125, 0.1, 0.075):
        x = X[d]; N = np.array(x['cuts'], float); y = np.array(x['values']); s, om = local(N, y)
        s40, w34 = s[-1][1], om[-1][1]
        lnN = np.log([o[0] for o in om[-4:]]); wv = np.array([o[1] for o in om[-4:]]); rate, c = np.polyfit(lnN, wv, 1)
        w40 = c + rate * math.log(39.0)
        drift = y[-1] + s40 * quad(lambda t: math.exp(-(w40 * t + 0.5 * max(rate, 0.) * t * t)), 0, np.inf)[0]
        f4 = []
        for nmin in (12, 14, 16, 18, 20):
            m = N >= nmin; b = fitF4(N[m], y[m])
            if b and b[1] < E.RMS_TOL and abs(b[0][0] - y[-1]) < 0.05: f4.append(float(b[0][0]))
        win, sp = x['fit']['D_inf'], x['fit']['spread_half']
        rs, _, _ = E.composite(d, 'none', None)
        rsm = RAW[d]['fit']  # the shipped composite raw extrapolation (extrapolation.json; replay A4 checks its refit)
        tail = max([abs(v - win) for v in f4] + [abs(drift - win)])
        presc = abs(win - rsm['D_inf']) / 2
        n = NR.get(d, {}); nv = n.get('Delta_E'); ne = n.get('total') or n.get('total_uncertainty') or 0.
        rows.append(dict(delta=d, N40=float(y[-1]), window=win, half_spread=sp, F4=[min(f4), max(f4)] if f4 else None, drift=float(drift),
                         bracket=[float(y[-1]), float(y[-1] + s40 / w34)], raw=rsm['D_inf'], raw_cut=max(rs), tail_shift=tail,
                         presc_half=presc, nrg=nv, nrg_err=ne, pull_fit=((win - nv) / math.hypot(sp, ne)) if nv else None))
    return rows

def table(rows, nrg_name):
    L = ['# Model dependence of the d = 1 HT limits (window prescription), 0.075 <= Ds <= 0.2', '',
         'Written by code/lri_dressed_phi4_hpc_analysis/public/model_dependence_ht1d.py; definitions in its docstring. NRG: %s.' % nrg_name, '',
         '| Ds | Delta(40) | window D_inf (fit) | F4 range | drifting omega | bracket upper | raw D_inf (N_max) | tail shift | 1/2 (window - raw) | NRG | (HT - NRG) / fit and NRG errors |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append('| %g | %.6f | %.6f(%.0e) | %s | %.6f | %.6f | %.6f (%d) | %.1e | %.1e | %s | %s |' % (
            r['delta'], r['N40'], r['window'], r['half_spread'], ('%.6f-%.6f' % tuple(r['F4'])) if r['F4'] else '-', r['drift'], r['bracket'][1],
            r['raw'], r['raw_cut'], r['tail_shift'], r['presc_half'],
            ('%.6f(%.0e)' % (r['nrg'], r['nrg_err'])) if r['nrg'] else '-', ('%.1f' % r['pull_fit']) if r['nrg'] else '-'))
    return '\n'.join(L) + '\n'

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--nrg', default=str(PKG / '../../results/HT_1d/nrg_reference.json'))
    ap.add_argument('--json', help='also write the rows (the shipped results/HT_1d/model_dependence.json)'); a = ap.parse_args()
    rows = compute(a.nrg); sys.stdout.write(table(rows, Path(a.nrg).name))
    if a.json: Path(a.json).write_text(json.dumps(rows, indent=1) + '\n')
