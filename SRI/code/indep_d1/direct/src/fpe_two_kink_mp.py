#!/usr/bin/env python3
"""Two-kink moments Z2, Q2, EZ2, EQ2 at one cutoff, Taylor coefficients [z^a delta^b]
(v=1+z) for a+b<=ord, by mpmath quadrature at 45 digits (independent of the C code).

Source term (first eta derivative, reflection form):
  T_E(delta) = 2 sum_i q_i int_0^Lam f_delta(X_1+c_i) dX_1,  c_1=0, c_2=r, Lam=1-r,
             = 2 sum_k delta^k [P_{k+1}(1-r) - P_{k+1}(1) + P_{k+1}(r)]/(k+1)!,
  P_j(y) = int_0^y log^j u du.
"""
import argparse
import json
import math

import mpmath as mp


def Pint(j, y):
    if y == 0:
        return mp.mpf(0)
    L = mp.log(y)
    s = mp.mpf(0)
    fac = mp.mpf(1)
    for i in range(j, -1, -1):
        s += (-1) ** (j - i) * fac * L ** i
        fac *= i
    return y * s


def series_coeffs(r, kind, E, ordr):
    L = mp.log(r)
    S = [None] + [-(L ** k) for k in range(1, ordr + 2)]          # q1 q2 = -1
    s1 = 2 * S[1]
    d = [mp.mpf(0)] + [2 * S[k + 1] / mp.factorial(k + 1) for k in range(1, ordr + 1)]
    G = [mp.mpf(1)] + [mp.mpf(0)] * ordr
    for b in range(1, ordr + 1):
        G[b] = sum(k * d[k] * G[b - k] for k in range(1, b + 1)) / b
    H = [G[:]] + [[mp.mpf(0)] * (ordr + 1) for _ in range(ordr)]
    for j in range(1, ordr + 1):
        for b in range(ordr + 1):
            H[j][b] = sum(d[k] * H[j - 1][b - k] for k in range(1, b + 1)) / j
    sp = [mp.mpf(1)]
    for a in range(1, ordr + 1):
        sp.append(sp[-1] * s1 / a)
    EX = {}
    for a in range(ordr + 1):
        for b in range(ordr + 1 - a):
            EX[(a, b)] = sum(sp[a - j] * H[j][b] for j in range(a + 1))
    base = 1 / (r * r)
    if kind == 'Q':
        base *= r
    if not E:
        T = [1 - r] + [mp.mpf(0)] * ordr
    else:
        T = [2 * (Pint(k + 1, 1 - r) - Pint(k + 1, mp.mpf(1)) + Pint(k + 1, r)) / mp.factorial(k + 1)
             for k in range(ordr + 1)]
    out = {}
    for (a, b), v in EX.items():
        out[(a, b)] = base * sum(EX[(a, b - bb)] * T[bb] for bb in range(b + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-k', dest='kind', required=True)
    ap.add_argument('-E', action='store_true')
    ap.add_argument('-e', dest='eps', required=True)
    ap.add_argument('-o', dest='ord', type=int, default=3)
    ap.add_argument('--dps', type=int, default=45)
    a = ap.parse_args()
    mp.mp.dps = a.dps
    eps = mp.mpf(a.eps)
    pts = [eps]
    x = eps
    while x * 4 < 1:
        x *= 4
        pts.append(x)
    pts.append(mp.mpf(1))
    keys = [(i, j) for i in range(a.ord + 1) for j in range(a.ord + 1 - i)]
    res = {}
    for kk in keys:
        res['%d,%d' % kk] = mp.nstr(mp.quad(lambda r: series_coeffs(r, a.kind, a.E, a.ord)[kk], pts), 40)
    print(json.dumps(dict(n=2, kind=a.kind, E=int(a.E), eps=a.eps, ord=a.ord, dps=a.dps, method='mpmath tanh-sinh',
                          coef=res)))


if __name__ == '__main__':
    main()
