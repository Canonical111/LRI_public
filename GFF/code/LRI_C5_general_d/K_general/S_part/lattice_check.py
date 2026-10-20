#!/usr/bin/env python3
"""Per-spin two-mode periodization lemma for the S family at generic d, and an evaluation of <t^2 S_tau>_d from REAL-AXIS
lattice sums (no nu-quadrature at finite spin).

Notation: q = d/4, alpha0 = q/2 - tau/4, beta0 = 3q/2 + tau/4 (alpha0 + beta0 = 2q), kappa = beta0 - alpha0 = q + tau/2,
          g_l(s) = Gamma(l/2+alpha0+s)Gamma(l/2+alpha0-s) / (Gamma(l/2+beta0+s)Gamma(l/2+beta0-s)),
          so that t_l^2 S_tau = Gamma(2q)^2 g_l(i nu)^2   (gs:RS).
Lemma (4 kappa > 1):
     I_l := int_{-i oo}^{i oo} ds/(2 pi i) g_l(s)^2
          = [ sin^2(pi alpha0) f_+(l) - cos^2(pi alpha0) f_-(l) ] / (2 pi sin(2 pi alpha0)),
     f_+(l) = sum_{s in l/2 + Z} g_l(s)^2,   f_-(l) = sum_{s in (l+1)/2 + Z} g_l(s)^2.
Check 1: I_l (lattice) vs I_l (quadrature) for a few spins.
Check 2: Gamma(2q)^2 [ sum_{l<L} d_l I_l(lattice) + spectral Stirling tail (l >= L) ]  vs  C(tau) X_d(tau)^2.
usage: lattice_check.py d tau dps L K NSUM
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H
from spec_S import mult_fp, S_closed


def phi(k, a0, b0):
    return mp.gamma(k + a0) / mp.gamma(k + b0)


def onesided_tail(factors, pref, N, K):
    """sum_{n>=N} pref * prod Gamma(n+al)^m/Gamma(n+be)^m via the Stirling expansion and Euler-Maclaurin Hurwitz zeta."""
    P, E = H.stirling_series(factors, K)
    return pref * mp.fsum(E[k] * H.hz(P + k, N) for k in range(K + 1) if E[k] != 0)


def f_plus(l, a0, b0, N, K):
    # T(n) = phi(l+n)^2 phi(-n)^2, symmetric under n -> -l-n:  sum_Z = 2 sum_{n>=0} - T(0) + sum_{n=-l}^{-1}
    T = lambda n: (phi(l + n, a0, b0) * phi(-n, a0, b0)) ** 2
    pos = mp.fsum(T(n) for n in range(N))
    pref = (mp.sin(mp.pi * b0) / mp.sin(mp.pi * a0)) ** 2            # phi(-n) = [sin pi b0/sin pi a0] Gamma(n+1-b0)/Gamma(n+1-a0)
    pos += onesided_tail([(l + a0, l + b0, 2), (1 - b0, 1 - a0, 2)], pref, N, K)
    mid = mp.fsum(T(n) for n in range(-l, 0))
    return 2 * pos - T(0) + mid


def f_minus(l, a0, b0, N, K):
    # T'(n) = phi(l+n+1/2)^2 phi(-n-1/2)^2, symmetric under n -> -l-1-n:  sum_Z = 2 sum_{n>=0} + sum_{n=-l}^{-1}
    h = mp.mpf(1) / 2
    T = lambda n: (phi(l + n + h, a0, b0) * phi(-n - h, a0, b0)) ** 2
    pos = mp.fsum(T(n) for n in range(N))
    pref = (mp.cos(mp.pi * b0) / mp.cos(mp.pi * a0)) ** 2            # phi(-n-1/2) = [cos pi b0/cos pi a0] Gamma(n+3/2-b0)/Gamma(n+3/2-a0)
    pos += onesided_tail([(l + h + a0, l + h + b0, 2), (h + 1 - b0, h + 1 - a0, 2)], pref, N, K)
    mid = mp.fsum(T(n) for n in range(-l, 0))
    return 2 * pos + mid


def I_lattice(l, a0, b0, N, K):
    N = N + 4 * l                     # the 1/n Stirling expansion of Gamma(n+l+a0)/Gamma(n+l+b0) needs n >> l
    fp, fm = f_plus(l, a0, b0, N, K), f_minus(l, a0, b0, N, K)
    return (mp.sin(mp.pi * a0) ** 2 * fp - mp.cos(mp.pi * a0) ** 2 * fm) / (2 * mp.pi * mp.sin(2 * mp.pi * a0)), fp, fm


def I_quad(l, a0, b0):
    al, be = mp.mpf(l) / 2 + a0, mp.mpf(l) / 2 + b0
    g = lambda nu: (mp.gamma(al + 1j * nu) * mp.gamma(al - 1j * nu) / (mp.gamma(be + 1j * nu) * mp.gamma(be - 1j * nu))).real ** 2
    sc = max(l, 1)
    return mp.quad(g, [0, sc * mp.mpf('0.3'), sc * mp.mpf('1.5'), 6 * sc, 40 * sc, mp.inf]) / mp.pi


if __name__ == '__main__':
    d, tau = mp.mpf(sys.argv[1]), sys.argv[2]
    dps, L, K, N = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    mp.mp.dps = dps
    d = mp.mpf(sys.argv[1]); tau = mp.mpf(tau); q = d / 4
    a0, b0 = q / 2 - tau / 4, 3 * q / 2 + tau / 4
    st = time.time()
    out = dict(d=sys.argv[1], tau=sys.argv[2], dps=dps, L=L, K=K, N=N, perspin={})
    for l in (0, 1, 2, 5):
        Il, fp, fm = I_lattice(l, a0, b0, N, K)
        Iq = I_quad(l, a0, b0)
        out['perspin'][l] = dict(I_lattice=mp.nstr(Il, 30), I_quad=mp.nstr(Iq, 30), rel=mp.nstr(abs(Il - Iq) / abs(Iq), 4),
                                 f_plus=mp.nstr(fp, 20), f_minus=mp.nstr(fm, 20))
    tot = mp.fsum(mult_fp(d, l) * I_lattice(l, a0, b0, N, K)[0] for l in range(L))
    pref = mp.gamma(2 * q) ** 2
    Sx = [(q / 2 - tau / 4, 3 * q / 2 + tau / 4, 2)]
    tl = H.tail(pref, Sx, Sx, L, K, d)
    val = pref * tot + tl
    c = S_closed(d, tau)
    out.update(total_lattice=mp.nstr(val, dps), closed=mp.nstr(c, dps), rel_total=mp.nstr(abs(val - c) / abs(c), 4),
               seconds=round(time.time() - st, 1))
    print(json.dumps(out), flush=True)
