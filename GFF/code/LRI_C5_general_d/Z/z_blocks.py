#!/usr/bin/env python3
"""Sample blocks of the two-node finite formula for the balanced three-wheel W_3(d;b) and its rim jets.

Two-node formula (derived in Z_general_d.tex; numerically confirmed):
    W_3(d;b) = u(b) R(b) + v(b) Mh(b),
    u(b) = 2 pi^2 (1 + 2 cos(pi b/2)) / sin^2(pi b/2),
    v(b) = cos(pi b/2) (1 + cos(pi b/2))^2 / (2 pi sin^3(pi b/2)),
    R(b)  = sum_{l,n>=0} d_l T_ln(b)^3,  T_ln(b) = (sigma)_{l+n} (1-g)_n / ((2q)_{l+n} n!)          [node t = 0]
          = R0(b) + R1(b),  R0 = 7F6(1; sigma^3, (1-g)^3; (2q)^3, 1^3; 1),
                            R1 = 4q (sigma/2q)^3 H[U+; V+](t=0)                       (two-variable Horn)
    Mh(b) = N_b^3 S_3(t_b; b),  t_b = (1 - sigma)/2  (self-mirror node)
          = sum_l d_l sum_{n in Z} [N_b g_l(n + (l+1)/2; b)]^3                         [midpoint lattice]
          = M0(b) + M1(b) + MC(b),  M0 = 2 N_b^3 A0(t_b),  M1 = 2 N_b^3 A+(t_b),  MC = N_b^3 C(t_b)
with q = d/4, sigma = b/2, g = 2q - sigma, N_b = Gamma(2q) Gamma(g)/Gamma(sigma); A0, A+, C are the sample blocks of
the foundation (wheel_general_b.Wheel), evaluated with its accelerated Horn sums (hypsums.py).

This file provides the five block functions of b (any complex b in the strip), used by the Cauchy-circle engine
(z_cauchy.py) and as the reference implementation for the exact-jet engine (z_jets.py).
"""
import os
import sys

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'foundation'))
from wheel_general_b import Wheel  # noqa: E402
from hypsums import GammaSeq, single_sum, conv_sum  # noqa: E402

BLOCKS = ('R0', 'R1', 'M0', 'M1', 'MC')


def blocks(d, b, **kw):
    """dict of the five block values at (d, b): R0, R1 (node t=0) and M0, M1, MC (node t_b=(1-b/2)/2).
    Integer d = 1, 2, 3 must be passed as python ints (exact polynomial multiplicities)."""
    w = Wheel(3, d, b, **kw)
    r, q, s, g = 3, w.q, w.sig, w.g
    out = {}
    # node t = 0: residue-prefactor sum, l = 0 part (a 7F6 at unit argument) and l >= 1 part (Horn)
    out['R0'] = single_sum(GammaSeq([(s, 2 * q, r), (1 - g, 1, r)]), 0, w.N, w.K)
    F = GammaSeq([(1 + s, 1 + 2 * q, r)])
    Gs = GammaSeq([(1 - g, 1, r)])
    pre = w.pref4q * (s / (2 * q)) ** r
    if w.mult == 'delta':
        out['R1'] = pre * single_sum(F.product(Gs), 0, w.N, w.K)
    else:
        out['R1'] = pre * conv_sum(F, w.mult, Gs, M=w.M, N=w.N, K=w.K, muY=getattr(w, 'muD', None))
    # self-mirror node t_b = (1 - sigma)/2: mirrored blocks coincide with the direct ones
    tb = (1 - s) / 2
    N3 = w.Nb() ** r
    out['M0'] = 2 * N3 * w.A0(tb)
    out['M1'] = 2 * N3 * w.Aplus(tb)
    out['MC'] = N3 * w.Cmid(tb)
    return out


def RM(d, b, **kw):
    bl = blocks(d, b, **kw)
    return bl['R0'] + bl['R1'], bl['M0'] + bl['M1'] + bl['MC'], bl


def uv(b):
    """elementary coefficients u(b), v(b) of W_3 = u R + v Mh."""
    sg, cg = mp.sin(mp.pi * b / 2), mp.cos(mp.pi * b / 2)
    return 2 * mp.pi ** 2 * (1 + 2 * cg) / sg ** 2, cg * (1 + cg) ** 2 / (2 * mp.pi * sg ** 3)


def uv_jets(q):
    """(u, u', u''), (v, v', v'') at b = d/2 = 2q (closed forms, s = sin(pi q), c = cos(pi q))."""
    s, c, pi = mp.sin(mp.pi * q), mp.cos(mp.pi * q), mp.pi
    u = (2 * pi ** 2 * (1 + 2 * c) / s ** 2,
         -2 * pi ** 3 * (1 + c + c ** 2) / s ** 3,
         pi ** 4 * (1 + 5 * c + 2 * c ** 2 + c ** 3) / s ** 4)
    v = (c * (1 + c) ** 2 / (2 * pi * s ** 3),
         -(1 + c) ** 2 * (1 + 2 * c) / (4 * s ** 4),
         pi * (1 + c) ** 3 * (2 + c) / (4 * s ** 5))
    return u, v


def assemble(q, Rj, Mj):
    """W, W', Z from the jets Rj = (R, R', R''), Mj = (Mh, Mh', Mh'') at b = 2q:
       W  = u R + v Mh,   W' = u' R + u R' + v' Mh + v Mh'  (= 0),
       Z  = (1/9)[u'' R + 2 u' R' + u R'' + v'' Mh + 2 v' Mh' + v Mh'']."""
    u, v = uv_jets(q)
    W0 = u[0] * Rj[0] + v[0] * Mj[0]
    W1 = u[1] * Rj[0] + u[0] * Rj[1] + v[1] * Mj[0] + v[0] * Mj[1]
    W2 = (u[2] * Rj[0] + 2 * u[1] * Rj[1] + u[0] * Rj[2]
          + v[2] * Mj[0] + 2 * v[1] * Mj[1] + v[0] * Mj[2])
    return W0, W1, W2 / 9


def assemble_reduced(q, Rj, Mj, eliminate='auto'):
    """Z with one first derivative eliminated by W'(d/2) = 0:
       eliminate R'  (needs 1 + 2cos(pi q) != 0, i.e. d != 8/3),  or  Mh'  (needs cos(pi q) != 0, i.e. d != 2)."""
    u, v = uv_jets(q)
    if eliminate == 'auto':
        eliminate = 'R1' if abs(1 + 2 * mp.cos(mp.pi * q)) > abs(mp.cos(mp.pi * q)) else 'M1'
    if eliminate == 'R1':
        R1 = -(u[1] * Rj[0] + v[1] * Mj[0] + v[0] * Mj[1]) / u[0]
        Rj = (Rj[0], R1, Rj[2])
    else:
        M1 = -(u[1] * Rj[0] + u[0] * Rj[1] + v[1] * Mj[0]) / v[0]
        Mj = (Mj[0], M1, Mj[2])
    return assemble(q, Rj, Mj)[2], eliminate


def zero_mode_form(q, Rj, Mj):
    """Z in the (R, c0hat) basis, c0hat = N^3 c_{3,0} = (c(1+c)^2/8) Mh - pi^3 s^3 R/(1+c)  (s, c at the running b):
       9 Z = 6 pi^2 R''/s^2 - 3 pi^4 cos(pi d/2) R/s^4 + 3 pi c0/s^3 - 4 c c0'/s^4 + 4 c0''/(pi s^3)  at b = d/2,
    where R' has been eliminated with W' = 0 (uniform for 0 < d < 4).  Returns Z and (c0, c0', c0'')."""
    pi = mp.pi

    def kM(b):
        cg = mp.cos(pi * b / 2)
        return cg * (1 + cg) ** 2 / 8

    def kR(b):
        sg, cg = mp.sin(pi * b / 2), mp.cos(pi * b / 2)
        return -pi ** 3 * sg ** 3 / (1 + cg)
    b0 = 2 * q
    kMj = [kM(b0), mp.diff(kM, b0, 1), mp.diff(kM, b0, 2)]
    kRj = [kR(b0), mp.diff(kR, b0, 1), mp.diff(kR, b0, 2)]
    c0 = kMj[0] * Mj[0] + kRj[0] * Rj[0]
    c1 = kMj[1] * Mj[0] + kMj[0] * Mj[1] + kRj[1] * Rj[0] + kRj[0] * Rj[1]
    c2 = (kMj[2] * Mj[0] + 2 * kMj[1] * Mj[1] + kMj[0] * Mj[2]
          + kRj[2] * Rj[0] + 2 * kRj[1] * Rj[1] + kRj[0] * Rj[2])
    s, c = mp.sin(pi * q), mp.cos(pi * q)
    Z9 = (6 * pi ** 2 * Rj[2] / s ** 2 - 3 * pi ** 4 * mp.cos(2 * pi * q) * Rj[0] / s ** 4
          + 3 * pi * c0 / s ** 3 - 4 * c * c1 / s ** 4 + 4 * c2 / (pi * s ** 3))
    return Z9 / 9, (c0, c1, c2)
