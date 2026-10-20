#!/usr/bin/env python3
"""Numerical check of the printed pole-node forms gdr:taylorW / gdr:taylorQP and, through b-derivatives,
of gdr:taylorLZ (the differentiated pole-node series), review formula-from-text.

F_r(u;b) = sum_{l,n} d_l [ -u N_b g_l(a_l+n+u;b) ]^r = sum d_l T_ln^r exp(r sum_m lambda_m u^m/m!)
         = sum_{l,n} d_l [ c(u;b) (sigma+u)_{l+n} (1-g+u)_n / ((2q+u)_{l+n} (1+u)_n) ]^r,
c(u;b) = -u N_b Gamma(sigma+u) Gamma(-u) / (Gamma(2q+u) Gamma(g-u)).
With F_r = sum_k mu_k u^k (Cauchy circle in u):  sum dT^r = mu_0, sum dT^r lambda_1 = mu_1/r,
sum dT^4 (4 lambda_1^2 + lambda_2) = mu_2/2, so the PRINTED forms read
  W3 = 2 pi^2 mu_0 - 2 kappa_b mu_1,   W4 = 2 kappa_b mu_2 - (4 pi^2/3) kappa_b mu_0 - 2 pi^2 mu_1,
kappa_b = pi cot(pi b/2).  L = d/db W4, Z = (1/9) d^2/db^2 W3 by a second Cauchy circle in b.
"""
import sys
import json
import time
import mpmath as mp
import gmpy2
from gmpy2 import mpfr, mpc
from kron_samples import setprec, m2g, m2g_real, g2m, dseq, ratio_pow_seq, to_fix, kron_mul, richardson, default_Ms


def h_gen(alpha, beta, gam, dlt, r, M, P, dvals):
    X = ratio_pow_seq(alpha, beta, r, M)
    Z = ratio_pow_seq(gam, dlt, r, M)
    dI = [to_fix(v, P) for v in dvals[:M + 1]]
    Zr = [to_fix(v.real, P) for v in Z]
    Zi = [to_fix(v.imag, P) for v in Z]
    cr = kron_mul(dI, Zr, M + 1)
    ci = kron_mul(dI, Zi, M + 1) if any(Zi) else [0] * (M + 1)
    sc = mpfr(2) ** (-2 * P)
    out = []
    acc = mpc(0)
    for m in range(M + 1):
        acc += X[m] * mpc(mpfr(cr[m]) * sc, mpfr(ci[m]) * sc)
        out.append(acc)
    return out


def F(d, b, u, r, Mmax, dvals, Ms, J=(10, 10), P=240):
    """F_r(u;b) (mpmath complex)."""
    q = d / 4
    sig = b / 2
    g = (d - b) / 2
    Nb = mp.gamma(2 * q) * mp.gamma(g) / mp.gamma(sig)
    cu = -u * Nb * mp.gamma(sig + u) * mp.gamma(-u) / (mp.gamma(2 * q + u) * mp.gamma(g - u))
    parts = h_gen(m2g(sig + u), m2g(2 * q + u), m2g(1 - g + u), m2g(1 + u), r, Mmax, P, dvals)
    F1 = d - 1 - r * g
    F2 = d - 2 * r * g
    S = richardson(parts, Ms, F1, F2, J[0], J[1])
    return cu ** r * S


def run(dstr, Mmax, Nb=12, Nu=12, rb='0.002', ru='0.002', J=(10, 10)):
    d = mp.mpf(dstr)
    b0 = d / 2
    rb = mp.mpf(rb)
    ru = mp.mpf(ru)
    dvals = dseq(m2g_real(d), Mmax + 2)
    Ms = default_Ms(Mmax, 2 * (J[0] + J[1]) + 8, 8)
    t0 = time.time()
    Wb = {}
    for j in range(Nb // 2 + 1):
        b = b0 + rb * mp.expjpi(2 * mp.mpf(j) / Nb)
        if j in (0, Nb // 2):
            b = mp.mpc(b.real, 0)
        mu = {}
        for r in (3, 4):
            vals = {}
            for k in range(Nu):
                if b.imag == 0 and k > Nu // 2:
                    vals[k] = mp.conj(vals[Nu - k])
                    continue
                u = ru * mp.expjpi(2 * mp.mpf(k) / Nu)
                if k in (0, Nu // 2):
                    u = mp.mpc(u.real, 0)
                vals[k] = F(d, b, u, r, Mmax, dvals, Ms, J)
            mu[r] = [sum(vals[k] * mp.expjpi(-2 * mp.mpf(k * p) / Nu) for k in range(Nu)) / (Nu * ru ** p)
                     for p in range(3)]
        kap = mp.pi * mp.cot(mp.pi * b / 2)
        W3 = 2 * mp.pi ** 2 * mu[3][0] - 2 * kap * mu[3][1]
        W4 = 2 * kap * mu[4][2] - 4 * mp.pi ** 2 / 3 * kap * mu[4][0] - 2 * mp.pi ** 2 * mu[4][1]
        Wb[j] = (W3, W4)
        print('b point', j, round(time.time() - t0, 1), 's', flush=True)
    for j in range(Nb // 2 + 1, Nb):
        Wb[j] = tuple(mp.conj(v) for v in Wb[Nb - j])
    coef = {}
    for i, name in enumerate(('W3', 'W4')):
        coef[name] = [sum(Wb[j][i] * mp.expjpi(-2 * mp.mpf(j * p) / Nb) for j in range(Nb)) / (Nb * rb ** p)
                      for p in range(3)]
    out = dict(d=dstr, Mmax=Mmax, Nb=Nb, Nu=Nu, rb=str(rb), ru=str(ru),
               threeQ_pole=mp.nstr(coef['W3'][0].real, 50), P4_pole=mp.nstr(coef['W4'][0].real, 50),
               L_pole=mp.nstr(coef['W4'][1].real, 50), Z_pole=mp.nstr((2 * coef['W3'][2] / 9).real, 50),
               dW3db_pole=mp.nstr(coef['W3'][1].real, 10), imag_max=mp.nstr(max(abs(coef[k][p].imag)
                                                                                for k in coef for p in range(3)), 5),
               time_s=round(time.time() - t0, 1))
    return out


if __name__ == '__main__':
    setprec(260)
    dstr = sys.argv[1]
    Mmax = int(sys.argv[2])
    Nb = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    res = run(dstr, Mmax, Nb, Nb)
    import os
    os.makedirs('results', exist_ok=True)
    fn = 'results/pole_d%s_M%d_N%d.json' % (dstr, Mmax, Nb)
    with open(fn, 'w') as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
