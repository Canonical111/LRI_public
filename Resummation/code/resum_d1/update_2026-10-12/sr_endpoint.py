#!/usr/bin/env python3
"""1d endpoint-v Borel resummation with the short-range series through C^SR_K, K = 4..8 (2026-10-12).

Generalizes resummation/baseline/calculate.py (mode 'endpoint_v'), whose helpers are copied here unchanged in
substance (conv, qpower, compose, polynomial, laguerre, integral_grid). The frozen package is not modified.

Construction: with t = sqrt(x), q = 4x = 1 - eps, v = 1 - 2 sqrt(x),
  S_K = sum_{n=0}^{K} C^SR_n t^n,   F = S_K + q^{(K+1)/2} R[H](v),   H = (F - S_K) q^{-(K+1)/2},
H expanded in eps from the GFF coefficients C_0..C_N, substituted eps = 2v - v^2, resummed in v with the
candidate action A_v = A_eps/2 (CB) or by Pade-Borel (PB, no action). K = 4 is the archived baseline.
C^SR_1..C^SR_7: closed forms (compendium eq. thermal-main); C^SR_8 = 247.38120480499... numerical (conjectured
zeta form); independent re-derivation 242.83 +- 2.37 (LRI_SRI_C6C7_independent RESULTS_C8.md): run as '8alt'.
No HT, NRG or MC value enters.

2026-10-13 (C8(1) final): C8 is read through update_2026-10-13/C8_1_ext/c8_1_switch.py. LRI_C8_1=final (default) uses
C8(1) = 8059766.723129955 (c8_1_final.json); LRI_C8_1=previous uses the frozen evidence.json value 8066723.342964563
and reproduces the 2026-10-12 outputs. C0..C7 unchanged. cb() and pb() take an optional coefficient list c (default C).
The main program writes to <switch output root>/sr_endpoint/ (results JSON, key-point CSV, reference residuals);
the 2026-10-12 outputs next to this file are not overwritten. Previous version: history/C8_1_before_ext_20261013/.
"""
import csv, json, math, sys
from pathlib import Path
import mpmath as mp
import numpy as np
from scipy.linalg import eigh_tridiagonal
from scipy.integrate import quad

mp.mp.dps = 65
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'update_2026-10-13'/'C8_1_ext'))
import c8_1_switch as SW
EV = json.loads((HERE.parent/'baseline/inputs/evidence.json').read_text())
C8IN = SW.c8_inputs()
def coefficients(c8):
    return [mp.mpf('.5'), -mp.mpf(1)/6, mp.mpf('0.6571312639810638'),
            mp.mpf('-3.719856322901833422489885712662776926'),
            mp.mpf('45.42488010356'), mp.mpf('-731.13947662454'),
            mp.mpf(EV['C6_headline']['C6_unrounded']), mp.mpf(str(EV['C7']['C7_full'])),
            mp.mpf(c8)]
C = coefficients(C8IN['C8'])
C_PREVIOUS = coefficients(SW.c8_inputs('previous')['C8'])
assert C_PREVIOUS[8] == mp.mpf(str(EV['C8']['C8_full']))
ACTION = 9*mp.pi**2/mp.gamma(mp.mpf(1)/4)**4
z2, z3, z4, z5, z6 = (mp.zeta(k) for k in (2, 3, 4, 5, 6))
CSR = {0: mp.mpf(1), 1: mp.mpf(-2), 2: mp.mpf(1)/2,
       3: mp.mpf(39)/16 + 2*z2,
       4: 4 - 4*z2 - 8*z3,
       5: mp.mpf(11249)/1024 - mp.mpf(361)/16*z2 + 24*z3 + mp.mpf(49)/2*z4,
       6: 26 - 38*z2 + 104*z3 - 80*z4 - 272*z5 + 112*z2*z3,
       7: (mp.mpf(1798583)/32768 - mp.mpf(90637)/1024*z2 + mp.mpf(453)/4*z3 - mp.mpf(16835)/64*z4
           + 1224*z5 - 540*z2*z3 + mp.mpf(4335)/8*z6 - 320*z3**2),
       8: mp.mpf('247.3812048049935484073550747661')}
C8ALT = mp.mpf('242.83')
XKEY = [0, .001, .01, .025, .05, .0625, .075, .0875, .1, .1125, .125, .1375, .15, .1625, .1727335,
        .175, .1875, .2, .225, .24, .249, .25]

def conv(a, b, n):
    return [sum(a[j]*b[k-j] for j in range(k+1) if j < len(a) and k-j < len(b)) for k in range(n+1)]
def qpower(p, n):                      # coefficients of (1-eps)^p
    return [(-1)**k*mp.binomial(p, k) for k in range(n+1)]
def compose(a, z, n):
    out = [mp.mpf(0)]*(n+1); power = [mp.mpf(1)] + [mp.mpf(0)]*n
    for a_k in a:
        out = [u+a_k*v for u, v in zip(out, power)]; power = conv(power, z, n)
    return out
def polynomial(c, b, alpha, A):        # [w^k] (1-w)^alpha B_b(4 A w/(1-w)^2)
    n = len(c)-1; b = mp.mpf(b); alpha = mp.mpf(alpha)
    return [sum(c[j]/mp.gamma(j+b+1)*(4*A)**j*(-1)**(k-j)*mp.binomial(alpha-2*j, k-j) for j in range(k+1))
            for k in range(n+1)]
_lag = {}
def laguerre(n, b):
    if (n, b) not in _lag:
        k = np.arange(n, dtype=float); j = np.arange(1, n, dtype=float)
        t, v = eigh_tridiagonal(2*k+b+1, np.sqrt(j*(j+b)))
        wt = math.gamma(b+1)*v[0, :]**2
        assert abs(wt.sum()/math.gamma(b+1)-1) < 2e-13
        _lag[(n, b)] = (t, wt)
    return _lag[(n, b)]
def integral_grid(p, b, alpha, A, arguments, nquad=240):
    t, wt = laguerre(nquad, b)
    z = np.asarray(arguments)[:, None]*t[None, :]/float(A)
    w = z/(np.sqrt(1+z)+1)**2
    return (np.polynomial.polynomial.polyval(w, np.asarray(p, dtype=float))/(1-w)**alpha).dot(wt)

def csr(K, alt=False):
    c = [CSR[n] for n in range(K+1)]
    if alt and K >= 8: c[8] = C8ALT
    return c
def base(x, K, alt=False):
    t = np.sqrt(np.asarray(x, dtype=float))
    return sum(float(a)*t**n for n, a in enumerate(csr(K, alt)))
def hseries(order, K, alt=False, c=None):
    """GFF series of H = (F - S_K) q^{-(K+1)/2} in eps, then eps = 2v - v^2."""
    c = (C if c is None else c)[:order+1]
    s = [sum(a/mp.mpf(2)**n*qpower(mp.mpf(n)/2, order)[k] for n, a in enumerate(csr(K, alt))) for k in range(order+1)]
    p = mp.mpf(K+1)/2
    h = conv([u-v for u, v in zip(c, s)], qpower(-p, order), order)
    back = [u+v for u, v in zip(s, conv(h, qpower(p, order), order))]
    assert max(abs(u-v)/(1+abs(v)) for u, v in zip(back, c)) < mp.mpf('1e-55')
    return compose(h, [0, 2, -1], order)
def cb(x, K, order=8, b=3, alpha=0, alt=False, afactor=1, c=None):
    A = ACTION/2/mp.mpf(str(afactor)); hv = hseries(order, K, alt, c)
    x = np.asarray(x, dtype=float)
    y = integral_grid(polynomial(hv, b, alpha, A), b, alpha, A, 1-2*np.sqrt(x))
    return base(x, K, alt) + (4*x)**((K+1)/2)*y
def pb(x, K, L=5, M=3, b=3, alt=False, c=None):
    hv = hseries(8, K, alt, c)
    bc = [v/mp.gamma(k+b+1) for k, v in enumerate(hv)]
    p, q = mp.pade(bc, L, M)
    roots = np.roots([float(v) for v in q[::-1]])
    if any(z.real > 0 and abs(z.imag) < 1e-8*max(1, abs(z)) for z in roots):
        return None, roots
    pp = np.array([float(v) for v in p]); qq = np.array([float(v) for v in q])
    t, wt = laguerre(240, b)
    x = np.asarray(x, dtype=float)
    z = (1-2*np.sqrt(x))[:, None]*t[None, :]
    rem = (np.polynomial.polynomial.polyval(z, pp)/np.polynomial.polynomial.polyval(z, qq)).dot(wt)
    return base(x, K, alt) + (4*x)**((K+1)/2)*rem, roots

def keypoint_rows(out):
    """Key-point table (the 2026-10-12 sr_endpoint_keypoints.csv layout): interior XKEY points."""
    V = out['variants']; rows = []
    for i, x in enumerate(out['x']):
        if x in (0, .25):
            continue
        r = {'Delta_sigma': x,
             'env_K5_K8_lo': min(V['K%d' % K]['core_min'][i] for K in (5, 6, 7, 8)),
             'env_K5_K8_hi': max(V['K%d' % K]['core_max'][i] for K in (5, 6, 7, 8)),
             'K4_core_lo': V['K4']['core_min'][i], 'K4_core_hi': V['K4']['core_max'][i]}
        for K in (4, 5, 6, 7, 8):
            r['CB8_K%d' % K] = V['K%d' % K]['CB8'][i]
        r['CB8_K8alt'] = V['K8alt']['CB8'][i]
        for K in (4, 5, 6, 7):
            r['PB8_K%d' % K] = V['K%d' % K]['PB8_53'][i] if V['K%d' % K]['PB8_53'] is not None else ''
        rows.append(r)
    return rows


def reference_rows():
    """Residuals of every reference row (refreshed 43 + 6 literature MC) from CB8 at K=8 and K=4, exactly at each x."""
    rows = []
    refs = list(csv.DictReader(open(SW.references_csv())))   # NRG rev 2 with LRI_C8_1=final (2026-10-13)
    lit = json.loads((HERE.parent/'inputs/mc_literature.json').read_text())
    for r in refs+lit:
        x = float(r['x']); y = float(r['y'])
        k8 = float(cb(np.array([x]), 8)[0]); k4 = float(cb(np.array([x]), 4)[0])
        rows.append({**{k: str(r.get(k, '') if r.get(k) is not None else '') for k in ('method', 'x', 'y', 'error', 'stat', 'status', 'source')},
                     'CB8_K8': k8, 'method_minus_K8': y-k8, 'CB8_K4': k4, 'method_minus_K4': y-k4,
                     'displayed': not (r['method'] == 'HT' and abs(x-.001) < 1e-12)})
    return rows


def writecsv(path, rows):
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    OUTD = SW.out_root()/'sr_endpoint'; OUTD.mkdir(parents=True, exist_ok=True)
    print('C8 switch:', json.dumps(SW.describe()), flush=True)
    X = np.array(XKEY); grid = np.linspace(0, .25, 501)
    variants = [(4, False), (5, False), (6, False), (7, False), (8, False), (8, True)]
    out = {'x': XKEY, 'variants': {}}
    for K, alt in variants:
        name = f'K{K}' + ('alt' if alt else '')
        base8 = cb(X, K, alt=alt)
        core = [cb(X, K, o, b, a, alt) for o in (6, 7, 8) for b in (2, 3, 4) for a in (-1, 0, 1)]
        pbv, roots = pb(X, K, alt=alt)
        g = cb(grid, K, alt=alt); i = int(np.argmin(g))
        out['variants'][name] = {'CB8': base8.tolist(), 'core_min': np.min(core, 0).tolist(),
                                 'core_max': np.max(core, 0).tolist(),
                                 'PB8_53': None if pbv is None else pbv.tolist(),
                                 'PB_poles': [[float(z.real), float(z.imag)] for z in roots],
                                 'min_x': float(grid[i]), 'min_y': float(g[i])}
        print(f'{name:6} min CB8 {g[i]:.6f} at x={grid[i]:.3f}; PB8 admissible: {pbv is not None}', flush=True)
    (OUTD/'sr_endpoint_results.json').write_text(json.dumps(out, indent=1))
    writecsv(OUTD/'sr_endpoint_keypoints.csv', keypoint_rows(out))
    writecsv(OUTD/'reference_residuals_K8.csv', reference_rows())
    # regression: K=4 must reproduce the archived baseline (inputs/curve.csv endpoint_v_L8), computed with the
    # coefficients of that table (the PREVIOUS C8); with LRI_C8_1=final the change of the K=4 curve is reported too
    arch = {round(float(r['Delta_sigma']), 7): r for r in csv.DictReader(open(HERE.parent/'inputs/curve.csv'))}
    k4 = out['variants']['K4']['CB8']; k4prev = cb(X, 4, c=C_PREVIOUS); dev, devprev = [], []
    for x, y, yp in zip(XKEY, k4, k4prev):
        r = arch.get(round(x, 7))
        if r and 'endpoint_v_L8' in r:
            dev.append(abs(y-float(r['endpoint_v_L8']))); devprev.append(abs(yp-float(r['endpoint_v_L8'])))
    print('K=4 regression vs archived endpoint_v_L8 (previous C8): max |diff| =', max(devprev), 'over', len(devprev), 'points', flush=True)
    assert max(devprev) < 1e-12
    if SW.MODE != 'previous':
        print('K=4 CB8 with the active C8 minus archived endpoint_v_L8: max |diff| =', max(dev), flush=True)
    print('wrote', OUTD, flush=True)
