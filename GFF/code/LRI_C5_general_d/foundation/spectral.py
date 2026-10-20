#!/usr/bin/env python3
"""Independent spectral evaluation of the balanced wheel (condensed note gs:balancedWheel, gs:trace):
    W_r(d;b) = N_b^r sum_l d_l(d) (1/pi) int_0^inf G_l(nu)^r dnu,
    G_l(nu)  = Gamma(a+i nu) Gamma(a-i nu) / (Gamma(c+i nu) Gamma(c-i nu)),  a = l/2 + b/4,  c = l/2 + d/2 - b/4,
    N_b = Gamma(d/2) Gamma((d-b)/2)/Gamma(b/2).
Spins l < L: tanh-sinh quadrature (analytic in b, so complex b is allowed).  Spins l >= L: Stirling expansion in
x = l/2 + i nu and the exact integral (1/2pi) int_R x^-p xbar^-p' dnu = l^(1-p-p') Gamma(p+p'-1)/(Gamma(p)Gamma(p')),
then the multiplicity expansion and Hurwitz zeta values (Euler-Maclaurin, hypsums.hz_batch).
This shares no code path with the finite-sample formula except the Hurwitz zeta routine.
"""
import sys
import mpmath as mp
from hypsums import hz_batch, _series_exp


def mult(d, l):
    if l == 0:
        return mp.mpf(1)
    if d == 1:
        return mp.mpf(1) if l == 1 else mp.mpf(0)
    return (2 * l + d - 2) * mp.gamma(l + d - 2) * mp.rgamma(d - 1) * mp.rgamma(l + 1)


def stirling_ratio(al, be, r, K):
    """[Gamma(x+al)/Gamma(x+be)]^r = x^{-p} sum_k E_k x^-k,  p = r(be-al)."""
    L = [mp.mpc(0)] * (K + 1)
    for j in range(1, K + 1):
        L[j] = r * (-1) ** (j + 1) * (mp.bernpoly(j + 1, al) - mp.bernpoly(j + 1, be)) / (j * (j + 1))
    return r * (be - al), _series_exp(L, K)


def per_spin_quad(r, d, b, l):
    a = mp.mpf(l) / 2 + b / 4
    c = mp.mpf(l) / 2 + d / 2 - b / 4
    sc = mp.mpf(max(l, 1)) / 2

    def f(nu):
        x = 1j * nu
        return mp.exp(r * (mp.loggamma(a + x) + mp.loggamma(a - x) - mp.loggamma(c + x) - mp.loggamma(c - x)))
    br = [0] + [sc * mp.mpf(z) for z in ('0.3', '1.5', '6', '40', '300')] + [mp.inf]
    return mp.quad(f, br) / mp.pi


def tail(r, d, b, L, K):
    p, E = stirling_ratio(b / 4, d / 2 - b / 4, r, K)
    H = []
    for n in range(K + 1):
        H.append(mp.fsum(E[k] * E[n - k] * mp.gamma(2 * p + n - 1) * mp.rgamma(p + k) * mp.rgamma(p + n - k)
                         for k in range(n + 1)))
    # multiplicity: d_l = (2l + d - 2) Gamma(l+d-2)/(Gamma(d-1) Gamma(l+1)) = (2l+d-2) l^(d-3) sum_j g_j l^-j / Gamma(d-1)
    if d == 2:
        g, base, rg = [mp.mpf(1)] + [0] * K, 2, 1      # d_l = 2:  2 l^0
        tot = mp.fsum(H[n] * 2 * z for n, z in enumerate(hz_batch(2 * p - 1, L, K)))
        return tot
    if d == 3:
        z1 = hz_batch(2 * p - 2, L, K)    # sum l^(1-2p-n) * l
        z0 = hz_batch(2 * p - 1, L, K)
        return mp.fsum(H[n] * (2 * z1[n] + z0[n]) for n in range(K + 1))
    pd, gj = stirling_ratio(d - 2, mp.mpf(1), 1, K)   # Gamma(l+d-2)/Gamma(l+1) = l^(d-3) sum g_j l^-j
    # coefficient of l^(1-2p-m) * l^(d-3-j) * (2l + d - 2)
    s1 = hz_batch(2 * p - d + 1, L, 2 * K)            # 2 * l^(d-1-2p-n-j)
    s2 = hz_batch(2 * p - d + 2, L, 2 * K)            # (d-2) l^(d-2-2p-n-j)
    tot = mp.mpc(0)
    for n in range(K + 1):
        for j in range(K + 1 - n):
            tot += H[n] * gj[j] * (2 * s1[n + j] + (d - 2) * s2[n + j])
    return tot * mp.rgamma(d - 1)


def W_spectral(r, d, b, L=40, K=None, info=None):
    d = mp.mpmathify(d)
    b = mp.mpmathify(b)
    K = K or int(0.7 * mp.mp.dps) + 10
    Nb = mp.gamma(d / 2) * mp.gamma((d - b) / 2) * mp.rgamma(b / 2)
    if d == 1:
        s = per_spin_quad(r, d, b, 0) + per_spin_quad(r, d, b, 1)
        return Nb ** r * s
    head = mp.fsum(mult(d, l) * per_spin_quad(r, d, b, l) for l in range(L))
    tl = tail(r, d, b, L, K)
    if info is not None:
        info.update(head=head, tail=tl)
    return Nb ** r * (head + tl)


if __name__ == '__main__':
    import time
    r, d, b = int(sys.argv[1]), mp.mpmathify(sys.argv[2]), mp.mpmathify(sys.argv[3])
    dps = int(sys.argv[4]) if len(sys.argv) > 4 else 25
    L = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    mp.mp.dps = dps + 10
    st = time.time()
    v = W_spectral(r, d, b, L)
    print('spectral W_%d(d=%s;b=%s) =' % (r, sys.argv[2], sys.argv[3]), mp.nstr(v, dps), ' [%.1f s]' % (time.time() - st))
