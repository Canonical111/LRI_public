#!/usr/bin/env python3
"""Check of the B-jet (gs:Bjet) along non-resonant lines through the B point at generic d, using the general MB.
   Line: (p1,p2,z1,z2,e) = t*(v1,v2,v3,v4) , e = d/2 + t*v5.  Kite indices (gs:masterJ):
   a = e-p1+p2+z2-z1, b = d+p1-e-p2, c = d+p1-e-z2, f = d-p1;  star = y (nu1=c/2, nu2=f/2, nu3=e/2), bubble = x (a3=a/2, a4=b/2).
   K_d = lim (J - G2 - G1 + G0 - (2/p1) Delta_B) / (z1 z2)."""
import sys, json, time
import numpy as np
from scipy.optimize import linprog
import mpmath as mp
from kite_general import mb_value

def indices(d, t, v):
    p1, p2, z1, z2 = [t * x for x in v[:4]]; e = d / 2 + t * v[4]
    a = e - p1 + p2 + z2 - z1; b = d + p1 - e - p2; c = d + p1 - e - z2; f = d - p1
    return dict(nu1=c / 2, nu2=f / 2, nu3=e / 2, a3=a / 2, a4=b / 2), (p1, p2, z1, z2, e)

def contour(d, idx):
    n1, n2, n3, a3, a4 = [float(idx[k]) for k in ('nu1', 'nu2', 'nu3', 'a3', 'a4')]
    h = float(d) / 2; lam = n1 + n2 + n3 - h; cw = a3 + a4 - h
    A = [[1, 0, 1], [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, 1, 1], [0, -1, 1], [-1, -1, 1], [-1, -1, 1], [1, 1, 1]]
    b = [0, n2 - lam, -(a3 - h), 0, n1 - lam, -(a4 - h), lam, n3, cw]
    res = linprog([0, 0, -1], A_ub=A, b_ub=b, bounds=[(None, None), (None, None), (None, 1)])
    return (res.x[0], res.x[1], -res.fun) if res.status == 0 else None

def jet_gamma(d, pt):
    p1, p2, z1, z2, e = pt
    G = mp.gamma; rg = mp.rgamma; h = d / 2
    def B(a, b):
        return G(h) * G((d - a) / 2) * G((d - b) / 2) * G((a + b - d) / 2) * rg(a / 2) * rg(b / 2) * rg((2 * d - a - b) / 2)
    G2 = B(d + p1 - e, d - p1) * B(e + p2 - z1, d - p2)
    G1 = B(e - p1 + p2 + z2, d + p1 - e - z2) * B(d + p1 - e - p2, d - p1)
    G0 = B(d + p1 - e, d - p1) * B(e + p2, d - p2)
    DB = B(e + p2 + z2 - z1, d - p2) - B(e + p2 - z1, d - p2) - B(e + p2 + z2, d - p2) + B(e + p2, d - p2)
    return G2 + G1 - G0 + 2 / p1 * DB

if __name__ == '__main__':
    dstr = sys.argv[1]; v = [mp.mpf(x) for x in sys.argv[2].split(',')]; ts = [mp.mpf(x) for x in sys.argv[3].split(',')]
    digits = int(sys.argv[4]) if len(sys.argv) > 4 else 25
    mp.mp.dps = digits + 15
    d = mp.mpf(dstr)
    rows = []
    for t in ts:
        idx, pt = indices(d, t, v)
        c = contour(d, idx)
        if c is None or c[2] <= 1e-6:
            print('t=%s: no straight contour' % t); continue
        st = time.time()
        J, info = mb_value(dstr, *[mp.nstr(idx[k], digits + 12) for k in ('nu1', 'nu2', 'nu3', 'a3', 'a4')], repr(c[0]), repr(c[1]), digits=digits)
        Jm = mp.mpf(J.real.mid().str(digits + 10, radius=False))
        JG = jet_gamma(d, pt)
        ratio = (Jm - JG) / (pt[2] * pt[3])
        rows.append((t, ratio))
        print('t=%s  margin=%.4f N=%d  J=%s  JGjet=%s  (J-JGjet)/(z1 z2)=%s  (%.1f s)' % (mp.nstr(t, 6), c[2], info['N'], mp.nstr(Jm, 20), mp.nstr(JG, 20), mp.nstr(ratio, 20), time.time() - st), flush=True)
    # polynomial extrapolation to t=0
    if len(rows) >= 3:
        for deg in range(2, len(rows)):
            xs = [r[0] for r in rows[:deg + 1]]; ys = [r[1] for r in rows[:deg + 1]]
            # Lagrange at 0
            val = 0
            for i in range(len(xs)):
                li = 1
                for j in range(len(xs)):
                    if j != i: li *= (0 - xs[j]) / (xs[i] - xs[j])
                val += ys[i] * li
            print('  extrapolation with %d points: K = %s' % (deg + 1, mp.nstr(val, 20)))
