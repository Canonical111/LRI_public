#!/usr/bin/env python3
"""One-variable bilateral 'elliptic' function behind the d = 1 and d = 2 wheels (session specialize).

    Omega_r(w; x) = sin^r(pi(w+x)) sum_{m in Z} [Gamma(m+w+x)/Gamma(m+w+1)]^r
                  = sin^r(pi(w+x)) sum_{m>=0} [...]^r + (-1)^r sin^r(pi w) sum_{k>=0} [Gamma(1-w+k)/Gamma(2-w-x+k)]^r

(the second form is the note's Omega(t;x) of gc:L2proof for r = 4).  Exact b-derivatives via first-order jets
(L/jet.py) through the accelerated single sums of L/hypsums_jet.py.

Claims checked with this module (check_special.py):
  d = 1 (duplication):  Xi_r(t;b) = (-1)^r 2^{-r b} Omega_r(2t; b)
  d = 2 (square):       Xi_r(t;b) = (-1)^r Omega_r(t; b/2)^2
"""
import os
import sys

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
from jet import J, val, der, jgamma, jrgamma, jsinpi  # noqa: E402,F401
from hypsums_jet import GammaSeq, single_sum  # noqa: E402


def _ssum(a, b, r):
    """sum_{m>=0} [Gamma(m+a)/Gamma(m+b)]^r  (a, b may be jets)."""
    dps = mp.mp.dps
    N = max(60, int(1.2 * dps))
    K = max(30, int(0.8 * dps) + 10)
    pref = (jgamma(a) * jrgamma(b)) ** r
    return pref * single_sum(GammaSeq([(a, b, r)]), 0, N, K)


def Omega(w, x, r=4):
    """Omega_r(w;x); w, x may be jets.  w must not be an integer unless it is exactly 0 (then the reflected
    half carries sin^r(pi w) = 0)."""
    first = jsinpi(w + x) ** r * _ssum(w + x, w + 1, r)
    if not isinstance(w, J) and w == 0:
        return first
    second = (-1) ** r * jsinpi(w) ** r * _ssum(1 - w, 2 - w - x, r)
    return first + second


def Nx(x):
    """normalization of gc:L2modes: N_x = Gamma(1-x)/Gamma(x)."""
    return jgamma(1 - x) * jrgamma(x)


def modes(x):
    """(A(x), B(x)) with N_x^2 Omega_4(t;x) = A + B cos 2pi(t + x/2)  (gc:L2modes), from the samples at
    t = 1/4 - x/2 (cos = 0) and t = -x/2 (cos = 1)."""
    n2 = Nx(x) ** 2
    A = n2 * Omega(mp.mpf(1) / 4 - x / 2, x)
    B = n2 * Omega(-x / 2, x) - A
    return A, B
