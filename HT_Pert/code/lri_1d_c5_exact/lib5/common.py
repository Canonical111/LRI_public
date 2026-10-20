"""Shared constants of the 1D exact-diagram engine (conventions: PLAN.md sec. 3, INTERFACES.md)."""
from fractions import Fraction as Fr
from math import comb

G1 = Fr(1, 3)
MAXLEGS = {"V": 4, "M": 2}
MOFF = 3                                   # storage index i = physical shell index m + MOFF  (m >= -3)
PS = (0, 1, 2, 3)
# linear functionals sum_p w_p X_p at order k >= 2:  r = -(X1-X0)/2, g = -(X3-X0+6r)/3, C = Pi X
W_R = (Fr(1, 2), Fr(-1, 2), Fr(0), Fr(0))
W_G = (Fr(-2, 3), Fr(1), Fr(0), Fr(-1, 3))
W_C = (Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3))
FUNCTIONALS = {"r": W_R, "g": W_G, "C": W_C}
ONE = (Fr(1), Fr(1), Fr(1), Fr(1))         # prefactor vector f(p) = 1


def vcoef(kind, m):
    """Coefficient of :Z^{maxlegs-m}: (x) :chi^m: in the vertex (V = :phi^4:/12, M = :phi^2:)."""
    if kind == "V":
        return Fr(comb(4, m), 12)
    if kind == "M":
        return Fr(comb(2, m), 1)
    raise ValueError(kind)


def vpp(p):
    return Fr(p * (p - 1), 2)


def pvec(f):
    """Prefactor vector (f(0), f(1), f(2), f(3)) as exact Fractions."""
    return tuple(Fr(f(p)) for p in PS)


def pmul(a, b):
    return tuple(x * y for x, y in zip(a, b))
