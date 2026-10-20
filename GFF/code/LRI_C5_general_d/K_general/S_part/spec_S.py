#!/usr/bin/env python3
"""Spectral evaluation of the S family  <t_l^2 S_tau>_d  (condensed note gs:RS, gs:trace) at generic d,
compared with the closed form  C(tau) X_d(tau)^2,  C = Gamma(2q)Gamma(tau)/Gamma(2q-tau),  X_d = [Gamma(q-tau/2)/Gamma(q+tau/2)]^2.

Uses the (copied, unmodified) spectral machinery of LRI_C5_general_d/refvals/hp_general_d.py:
finite spins l < L by tanh-sinh quadrature of the nu-symmetrized integrand, spins l >= L by the Stirling/Hurwitz tail.
With x = l/2 + i nu the integrand is  Gamma(2q)^2 [Gamma(x+q/2-tau/4)/Gamma(x+3q/2+tau/4)]^2 * (same in xb = l/2 - i nu).

usage: spec_S.py d tau dps L K  [prints JSON line]
"""
import sys, json, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H


def mult_fp(d, l):
    """fp:degeneracy form of d_l(d) (no spurious 0/0 at d = 1, 2): d_0 = 1, d_{k+1} = 4q (2q+1)_k (4q-1)_k / ((2q)_k (2)_k)."""
    if l == 0:
        return mp.mpf(1)
    q = mp.mpf(d) / 4; k = l - 1
    return 4 * q * mp.rf(2 * q + 1, k) * mp.rf(4 * q - 1, k) / (mp.rf(2 * q, k) * mp.rf(2, k))


H.multiplicity = mult_fp


def S_spectral(d, tau, L, K):
    q = d / 4
    a, bb = q / 2, 3 * q / 2
    pref = mp.gamma(2 * q) ** 2
    Sx = [(a - tau / 4, bb + tau / 4, 2)]          # Gamma(x+a-tau/4)^2/Gamma(x+bb+tau/4)^2
    breaks = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, 40, mp.inf]
    return H.spectral_combo([(1, pref, Sx, Sx)], L, K, d, breaks)


def S_closed(d, tau):
    q = d / 4
    C = mp.gamma(2 * q) * mp.gamma(tau) / mp.gamma(2 * q - tau)
    X = (mp.gamma(q - tau / 2) / mp.gamma(q + tau / 2)) ** 2
    return C * X ** 2


if __name__ == '__main__':
    d, tau = mp.mpf(sys.argv[1]), sys.argv[2]
    dps, L, K = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    mp.mp.dps = dps
    d = mp.mpf(sys.argv[1]); tau = mp.mpmathify(tau.replace('i', 'j'))
    st = time.time()
    v = S_spectral(d, tau, L, K)
    c = S_closed(d, tau)
    out = dict(d=sys.argv[1], tau=sys.argv[2], dps=dps, L=L, K=K, nutail=os.environ.get('HPG_NUTAIL', '0'), spectral=mp.nstr(v, dps),
               closed=mp.nstr(c, dps), reldiff=mp.nstr(abs(v - c) / abs(c), 5), seconds=round(time.time() - st, 1))
    print(json.dumps(out), flush=True)
