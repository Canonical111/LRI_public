#!/usr/bin/env python3
"""Check of the pole-node Taylor form (sym_taylor.py):
   N_b^r Xi(t) = Phi_r(x+t) + O(t^r),  Phi_r(u) = [N_b sin pi(u+x) sin pi(u-y) phi(u) psit(u)]^r h_u  (right half-lattice),
   W_3 = omega_0 Phi(x) + omega_1 Phi'(x),   W_4 = omega_0 Phi + omega_1 Phi' + omega_2 Phi''   (theta = pi b/2),
against the multi-node values of L/L_general.py.  Taylor coefficients from a Cauchy circle in u.  Mac, 30 digits."""
import os
import sys

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
from L_general import Wheel3  # noqa: E402

mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
G = 12


def omegas(r, th):
    s, c, pi = mp.sin(th), mp.cos(th), mp.pi
    if r == 3:
        return [2 * (2 * s ** 2 - 3) / (pi * s ** 5), 2 * c / (pi ** 2 * s ** 4)]
    return [4 * (mp.cos(2 * th) + 4) * c / (pi * s ** 7), 2 * (3 * s ** 2 - 4) / (pi ** 2 * s ** 6),
            c / (pi ** 3 * s ** 5)]


def check(r, d, b, M=24, rho=mp.mpf('0.08')):
    w = Wheel3(r, d, b)
    x, y, N = w.x, w.y, w.Nb()

    def Phi(u):
        return (N * mp.sinpi(u + x) * mp.sinpi(u - y) * w.phi(u) * w.psit(u)) ** r * w.hR(u)[0]
    vals = [Phi(x + rho * mp.expjpi(2 * mp.mpf(k) / M)) for k in range(M)]
    taylor = []
    for j in range(r - 1):
        a = mp.fsum(vals[k] * mp.expjpi(-2 * mp.mpf(j * k) / M) for k in range(M)) / M / rho ** j
        taylor.append(a * mp.factorial(j))
    W_taylor = mp.fsum(o * t for o, t in zip(omegas(r, mp.pi * b / 2), taylor))
    W_nodes = w.W()
    return mp.re(W_taylor), mp.re(W_nodes)


def task(args):
    dstr, r, off = args
    with mp.workdps(mp.mp.dps + G):
        d = mp.mpf(dstr)
        b = d / 2 + mp.mpf(off)
        Wt, Wn = check(r, d, b)
        return 'd=%s r=%d b=%s  W(Taylor)=%s  W(nodes)=%s  rel=%s' % (
            mp.nstr(d, 3), r, mp.nstr(b, 4), mp.nstr(Wt, 25), mp.nstr(Wn, 25), mp.nstr(abs(Wt / Wn - 1), 3))


if __name__ == '__main__':
    from multiprocessing import Pool
    jobs = [(d, r, off) for d in ('1.5', '2.5') for r in (3, 4) for off in ('0', '0.04')]
    with Pool(len(jobs)) as p:
        for line in p.map(task, jobs):
            print(line, flush=True)
