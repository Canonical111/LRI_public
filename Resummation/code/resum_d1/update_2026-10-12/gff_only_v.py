#!/usr/bin/env python3
"""Can GFF-only CB use the square-root branch point at Delta_sigma = 0 (eps = 1)?
Variants (all with GFF C_0..C_8 only, unless stated):
  eps     : direct CB in eps (archived 'direct' mode; candidate action A)
  v       : CB in v = 1 - sqrt(1-eps) = 1 - 2 sqrt(x) (uniformizes the branch point), action A_v = A/2
  lam     : CB in lam = 2v/(2-v) (also sends the mirror point v = 2 to infinity), action A/2 at leading order
  v+F(1)  : as v, with only the exact value F(Delta_sigma=0) = 1 imposed: F = 1 + (1-v) R(v)
  K8      : endpoint-v with the short-range series through C^SR_8 (reference, uses short-range input)
Core band: N = 6,7,8; b = 2,3,4; alpha = -1,0,1. No HT/NRG/MC input.
"""
import numpy as np, mpmath as mp
import sr_endpoint as S
A = S.ACTION
def series_in(var, order, value_only=False):
    c = S.C[:order+1]
    if var == 'eps': return c, A
    if value_only:   # (F - 1)/(1 - v) with 1 - v = sqrt(1-eps) = (1-eps)^(1/2)
        c = [u - (1 if k == 0 else 0) for k, u in enumerate(c)]
        c = S.conv(c, S.qpower(mp.mpf(-1)/2, order), order)
    hv = S.compose(c, [0, 2, -1], order)                     # eps = 2v - v^2
    if var == 'v': return hv, A/2
    if var == 'lam':                                         # v = 2 lam/(2+lam) = lam - lam^2/2 + lam^3/4 - ...
        vl = [mp.mpf(0)] + [(-1)**(k-1)*mp.mpf(2)/mp.mpf(2)**k for k in range(1, order+1)]
        return S.compose(hv, vl, order), A/2
def curve(var, x, order=8, b=3, alpha=0, value_only=False):
    c, Aeff = series_in(var, order, value_only)
    x = np.asarray(x, float); v = 1 - 2*np.sqrt(x)
    arg = {'eps': 1 - 4*x, 'v': v, 'lam': 2*v/(2 - v)}[var]
    y = S.integral_grid(S.polynomial(c, b, alpha, Aeff), b, alpha, Aeff, arg)
    return 1 + (1 - v)*y if value_only else y
X = np.array([0.001, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.249])
ref = S.cb(X, 8)
rows = {}
for name, var, vo in [('eps', 'eps', False), ('v', 'v', False), ('lam', 'lam', False), ('v+F(1)', 'v', True)]:
    base = curve(var, X, value_only=vo)
    core = [curve(var, X, o, b, a, vo) for o in (6, 7, 8) for b in (2, 3, 4) for a in (-1, 0, 1)]
    rows[name] = (base, np.min(core, 0), np.max(core, 0))
print('Delta_sigma |   K8 ref  | GFF-only CB8 minus K8 ref (1e-3), [core band width 1e-3]')
print('            |           |   eps            v                lam              v+F(1)')
for i, x in enumerate(X):
    s = ' '.join(f"{1e3*(rows[k][0][i]-ref[i]):+8.2f} [{1e3*(rows[k][2][i]-rows[k][1][i]):6.2f}]" for k in rows)
    print(f"{x:<11} | {ref[i]:.6f} | {s}")
print('values at Delta_sigma=0.001 (exact limit 1 at 0):', {k: round(float(rows[k][0][0]), 4) for k in rows})
