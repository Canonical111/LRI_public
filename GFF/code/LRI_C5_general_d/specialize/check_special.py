#!/usr/bin/env python3
"""Quick checks (Mac, 30 digits) of the integer-dimension structure used in general_d.tex / RESULT.md:

 (1) d = 1 duplication   N_b^r Xi_r(t;b) = (-1)^r N_b^r 2^{-rb} Omega_r(2t; b)     (r = 3, 4; b = 1/2 and 0.45)
 (2) d = 2 square        N_b^r Xi_r(t;b) = (-1)^r N_b^r Omega_r(t; b/2)^2          (r = 3, 4; b = 1 and 1.1)
     at the nodes of the generic formulas: t = 0, tau = 0 (t = -b/4), tau = 1/2 (t = 1/2 - b/4),
     against the five-Horn samples of L/L_general.py (Wheel3.samples()).
 (3) the elliptic mode system at x = 1/2 (gc:L2proof):  A' = 2 pi B - 2 log2 A,  B' = (3 pi/2) A - 2 log2 B,
     a = A(1/2) = 8 N_e/pi, b = B(1/2) = 8 M_e/pi, M_e = (B_- + B_+)/64, N_e = (B_- - B_+)/32.
 (4) L_1 and L_2 from the mode formula vs eq:KLpsiReflected and gc:L2closed.
"""
import os
import sys

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
import omega as om  # noqa: E402
from jet import J, val, der  # noqa: E402
from L_general import Wheel3  # noqa: E402

mp.mp.dps = 30
G = 15


def rel(a, b):
    a, b = mp.mpmathify(a), mp.mpmathify(b)
    return abs(a - b) / max(abs(b), mp.mpf(10) ** (-mp.mp.dps))


def samples(r, d, b):
    w = Wheel3(r, d, b)
    sm = w.samples()
    return sm


def main():
    out = []
    with mp.workdps(30 + G):
        # (1) d = 1
        for r in (4, 3):
            for b in (mp.mpf(1) / 2, mp.mpf('0.45')):
                sm = samples(r, 1, b)
                N = sm['N']
                pre = (-1) ** r * N ** r * mp.mpf(2) ** (-r * b)
                Xt = pre * om.Omega(mp.mpf(0), b, r)
                X0 = pre * om.Omega(-b / 2, b, r)
                Xh = pre * om.Omega(1 - b / 2, b, r)
                devs = [rel(Xt, sm['Xt']), rel(Xh, sm['Xh'])]
                if r == 4:
                    devs.append(rel(X0, sm['X0']))
                out.append(('d=1 duplication r=%d b=%s' % (r, mp.nstr(b, 3)), max(devs)))
        # (2) d = 2
        for r in (4, 3):
            for b in (mp.mpf(1), mp.mpf('1.1')):
                sm = samples(r, 2, b)
                N = sm['N']
                x = b / 2
                pre = (-1) ** r * N ** r
                Xt = pre * om.Omega(mp.mpf(0), x, r) ** 2
                X0 = pre * om.Omega(-b / 4, x, r) ** 2
                Xh = pre * om.Omega(mp.mpf(1) / 2 - b / 4, x, r) ** 2
                devs = [rel(Xt, sm['Xt'])]
                if r == 4:
                    devs += [rel(X0, sm['X0']), rel(Xh, sm['Xh'])]
                else:
                    devs.append(abs(Xh) + abs(sm['Xh']))   # Mh = 0 at d = 2 (Z note, Prop. special (b))
                out.append(('d=2 square r=%d b=%s' % (r, mp.nstr(b, 3)), max(devs)))
        # (3) modes at x = 1/2 and their x-derivatives (jets)
        x = J(mp.mpf(1) / 2, 1)
        A, B = om.modes(x)
        a, bb, ap, bp = val(A), val(B), der(A), der(B)
        G4 = mp.gamma(mp.mpf(1) / 4) ** 4
        Fminus = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
        Fplus = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
        Bm, Bp = G4 * Fminus, 64 * mp.pi ** 4 / G4 * Fplus
        Me, Ne = (Bm + Bp) / 64, (Bm - Bp) / 32
        out.append(('a = 8 N_e/pi', rel(a, 8 * Ne / mp.pi)))
        out.append(('b = 8 M_e/pi', rel(bb, 8 * Me / mp.pi)))
        L2 = mp.log(2)
        out.append(("A'(1/2) = 2 pi b - 2 log2 a", rel(ap, 2 * mp.pi * bb - 2 * L2 * a)))
        out.append(("B'(1/2) = 3pi/2 a - 2 log2 b", rel(bp, 3 * mp.pi / 2 * a - 2 * L2 * bb)))
        # third sample consistency (two modes): t = 0
        n2 = om.Nx(mp.mpf(1) / 2) ** 2
        tt = mp.mpf('0.1')
        out.append(('two-mode check at t=0.1', rel(n2 * om.Omega(tt, mp.mpf(1) / 2), a + bb * mp.cos(2 * mp.pi * (tt + mp.mpf(1) / 4)))))
        # (4) L_1, L_2 from the modes
        pi = mp.pi
        L1_closed = -(128 * pi + 640 * L2) * Me - (96 * pi + 512 * L2) * Ne
        Ad = (pi + 4 * L2)
        P4_1 = 13 * Bm - 3 * Bp
        L1_note = -(3 * Ad - pi) / 6 * P4_1 - 2 * pi / 3 * Bm
        out.append(('lp:eq:MN = eq:KLpsiReflected', rel(L1_closed, L1_note)))
        # mode formula d=1 (general_d.tex gdr:L1modes): L_1 = 32 pi [(-3pi/2 - 8 log2) c0 + (-2 pi - 10 log2) c2]
        c0, c2 = a / 4, bb / 4
        L1_modes = 32 * pi * ((-3 * pi / 2 - 8 * L2) * c0 + (-2 * pi - 10 * L2) * c2)
        out.append(('L_1 from modes vs closed', rel(L1_modes, L1_closed)))
        # generic d=1 jet of W_4 directly from modes: W_4(1;b) = F_b [(3+2c^2) c0 + 5 c2] c, c0 = 2^{-4b} A/N_b^2
        bj = J(mp.mpf(1) / 2, 1)
        Am, Bmd = om.modes(bj)
        nn = om.Nx(bj) ** 2
        two = J(mp.mpf(2) ** (-2), -4 * mp.log(2) * mp.mpf(2) ** (-2))   # 2^{-4b} at b = 1/2
        c0j = two * Am / nn
        c2j = two * Bmd / nn
        from jet import jgamma, jrgamma, jsinpi, jcospi
        Nw = mp.sqrt(pi) * jgamma((1 - bj) / 2) * jrgamma(bj / 2)
        s, c = jsinpi(bj / 2), jcospi(bj / 2)
        W = 4 * Nw ** 4 * c / (pi * s ** 7) * ((3 + 2 * c ** 2) * c0j + 5 * c2j)
        out.append(('d=1: W_4 = P4(1) from modes', rel(val(W), P4_1)))
        out.append(('d=1: dW_4/db = L_1 from modes', rel(der(W), L1_closed)))
        # d = 2: Xi = Omega(t; b/2)^2, x = b/2
        bj2 = J(mp.mpf(1), 1)
        xj = bj2 / 2
        Am, Bmd = om.modes(xj)
        n4 = om.Nx(xj) ** 4
        c0j = (Am ** 2 + Bmd ** 2 / 2) / n4
        c1j = 2 * Am * Bmd / n4
        c2j = Bmd ** 2 / (2 * n4)
        Nw = jgamma((2 - bj2) / 2) * jrgamma(bj2 / 2)
        s, c = jsinpi(bj2 / 2), jcospi(bj2 / 2)
        W = 4 * Nw ** 4 / (pi * s ** 7) * (c * (3 + 2 * c ** 2) * c0j + (1 + 4 * c ** 2) * c1j + 5 * c * c2j)
        P4_2 = (Bm ** 2 - Bp ** 2) / (4 * pi ** 3)
        out.append(('d=2: W_4 = P4(2) from modes', rel(val(W), P4_2)))
        out.append(('d=2: dW_4/db = -2log2 P4(2)', rel(der(W), -2 * L2 * P4_2)))
    for k, v in out:
        print('%-40s %s' % (k, mp.nstr(v, 3)))


if __name__ == '__main__':
    main()
