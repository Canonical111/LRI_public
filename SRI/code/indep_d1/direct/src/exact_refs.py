#!/usr/bin/env python3
"""High-precision references for the low-order moments, from the definitions.

1. Two-kink moments Z2, Q2, EZ2, EQ2 at finite eps, with v/delta Taylor
   coefficients obtained by Cauchy contour integration in the complex (v, delta)
   planes of the *unexpanded* kernel
       W_2(v,delta) = exp[-2 v f_delta(r)],  f_delta(r) = (r^delta-1)/delta,
   and of the two-sided endpoint factor U^even = sum_i q_i [f(X_i) - f(1-X_i)]
   (X_1 translation integral exact: int_0^y f_delta = (y^{1+delta}/(1+delta)-y)/delta).
   This checks the log-insertion algebra and the source convention used by the
   Gauss code independently of both.
2. Closed forms at v=1, delta=0:  Z2 = 1/eps + l - 1,  Q2 = -l - 1 + eps,
   and A3(eps) (elementary + dilogarithm, derived by hand below).

Usage: python3 exact_refs.py [--eps 0.1,0.01] [--dps 25] [--M 12] > ../results/exact_refs.json
"""
import argparse
import json

import mpmath as mp


def f_delta(r, d):
    if d == 0:
        return mp.log(r)
    return (mp.power(r, d) - 1) / d


def F_delta(y, d):
    """int_0^y f_delta(u) du."""
    if y == 0:
        return mp.mpf(0)
    if d == 0:
        return y * mp.log(y) - y
    return (mp.power(y, d + 1) / (d + 1) - y) / d


def two_kink(kind, E, v, d, eps):
    """Exact 1D integral of the two-kink moment at complex (v, d)."""
    def g(r):
        w = mp.exp(-2 * v * f_delta(r, d))
        lam = 1 - r
        if kind == 'Q':
            w = w * r
        if not E:
            return w * lam
        # q1=+1 at X1=x, q2=-1 at X2=x+r, U^even: f(X1)-f(1-X1)-f(X2)+f(1-X2)
        # int_0^lam: F(lam) - [F(1)-F(r)] - [F(1)-F(r)] + F(lam)
        T = 2 * F_delta(lam, d) - 2 * F_delta(mp.mpf(1), d) + 2 * F_delta(r, d)
        return w * T
    pts = [eps, 2 * eps, 4 * eps, 10 * eps, mp.mpf(1)] if 10 * eps < 1 else [eps, mp.mpf(1)]
    pts = sorted(set([p for p in pts if p <= 1]))
    return mp.quad(g, pts)


def taylor2(fun, ordmax, M, rz, rd):
    """[z^a d^b] of fun(1+z, d) for a+b<=ordmax by a M x M trapezoid on circles."""
    vals = {}
    for j in range(M):
        z = rz * mp.expjpi(2 * mp.mpf(j) / M)
        for k in range(M):
            dd = rd * mp.expjpi(2 * mp.mpf(k) / M)
            vals[(j, k)] = fun(1 + z, dd)
    out = {}
    for a in range(ordmax + 1):
        for b in range(ordmax + 1 - a):
            s = 0
            for j in range(M):
                for k in range(M):
                    s += vals[(j, k)] * mp.expjpi(-2 * mp.mpf(j * a + k * b) / M)
            out[(a, b)] = (s / (M * M) / (mp.power(rz, a) * mp.power(rd, b))).real
    return out


def A3_closed(eps):
    """A3 at v=1, delta=0: int over r,t>=eps, r+t<=1 of (1-r-t)(r+t)^2/(r^2 t^2).
    (r+t)^2/(r^2t^2) = 1/r^2 + 1/t^2 + 2/(rt); symmetric in r<->t.
    I1 = int_eps^a dr (a-r)^2/(2 r^2),  a = 1-eps
    I2 = int_eps^a dr/r [ (1-r) log((1-r)/eps) - (1-r-eps) ]
    A3 = 2 I1 + 2 I2."""
    e = mp.mpf(eps)
    a = 1 - e
    I1 = (-2 * a * mp.log(a) + a * a / e + 2 * a * mp.log(e) - e) / 2
    # int (1-r)log(1-r)/r dr = -Li2(r) + (1-r)log(1-r) + r
    def P1(r):
        return -mp.polylog(2, r) + (1 - r) * mp.log(1 - r) + r
    J1 = P1(a) - P1(e)
    J2 = -mp.log(e) * ((mp.log(a) - a) - (mp.log(e) - e))
    J3 = -(((1 - e) * mp.log(a) - a) - ((1 - e) * mp.log(e) - e))
    I2 = J1 + J2 + J3
    return 2 * I1 + 2 * I2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eps', default='0.125,0.1,0.05,0.02,0.01,0.005,0.002')
    ap.add_argument('--cauchy-eps', default='0.1,0.01')
    ap.add_argument('--dps', type=int, default=30)
    ap.add_argument('--M', type=int, default=24)
    ap.add_argument('--ord', type=int, default=3)
    a = ap.parse_args()
    mp.mp.dps = a.dps
    res = {'closed_forms': {}, 'cauchy_two_kink': {}, 'settings': dict(dps=a.dps, M=a.M, ord=a.ord)}
    for es in a.eps.split(','):
        e = mp.mpf(es)
        l = mp.log(e)
        res['closed_forms'][es] = {
            'Z2_base': mp.nstr(1 / e + l - 1, 22),
            'Q2_base': mp.nstr(-l - 1 + e, 22),
            'A3_base': mp.nstr(A3_closed(e), 22),
        }
    for es in a.cauchy_eps.split(','):
        e = mp.mpf(es)
        res['cauchy_two_kink'][es] = {}
        for kind, E in [('Z', 0), ('Q', 0), ('Z', 1), ('Q', 1)]:
            L = abs(mp.log(e))
            rz, rd = mp.mpf('0.25') / L, mp.mpf('0.5') / L ** 2   # radii adapted to the log growth (aliasing < 1e-20 at M=24)
            tay = taylor2(lambda v, d: two_kink(kind, E, v, d, e), a.ord, a.M, rz, rd)
            name = ('E' if E else '') + kind + '2'
            res['cauchy_two_kink'][es][name] = {'%d,%d' % k: mp.nstr(v, 18) for k, v in tay.items()}
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
