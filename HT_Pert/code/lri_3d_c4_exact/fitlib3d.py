#!/usr/bin/env python3
"""Least-squares tower fits y(L) = sum_j c_j f_j(L) for the large-L asymptotics of the 3D coefficients.

Basis names: "1"; "L^a" (power, a may be half-integer or negative, e.g. "L^1", "L^0.5", "L^-1.5");
"lk*L^a" = (ln L)^k L^a, e.g. "l1*L^0" = ln L, "l1*L^-1".  Data are exact to ~1e-11 (full engine) or ~1e-15
(two-vertex window sums), so fits are deterministic; quoted uncertainties are systematic (spread over towers and
fit windows) and are checked against held-out larger L (blind tests)."""
import math

import numpy as np

C2_EXACT = (2 + 4 * math.log(2) - math.pi) / 9
C3_EXACT = -0.353581520433          # condensed note (12 digits)
C4_EXACT = 1.22806354532762307997   # LRI_C5_d3/inputs/three_dimension_addition.tex


def basis(name, L):
    L = np.asarray(L, dtype=float)
    if name == "1":
        return np.ones_like(L)
    k = 0
    if name.startswith("l"):
        lk, name = name.split("*")
        k = int(lk[1:])
    a = float(name[2:])
    return np.log(L) ** k * L ** a


def tower(powers, logs=None):
    """powers: list of exponents a (e.g. [-0.5, -1, -1.5]); logs: dict a -> max log power at that exponent."""
    names = []
    logs = logs or {}
    for a in powers:
        for k in range(logs.get(a, 0) + 1):
            names.append(("" if k == 0 else f"l{k}*") + f"L^{a:g}")
    return names


def fit(L, y, names, Lmin, Lmax=None, step=1):
    sel = (L >= Lmin) & ((L <= Lmax) if Lmax else True)
    Ls, ys = L[sel].astype(float)[::step], y[sel].astype(float)[::step]
    X = np.column_stack([basis(n, Ls) for n in names])
    sc = np.abs(X).max(axis=0)
    coef, *_ = np.linalg.lstsq(X / sc, ys, rcond=None)
    coef = coef / sc
    res = ys - X @ coef
    return dict(zip(names, coef)), float(np.abs(res).max()), len(Ls)


def predict(coef, L):
    return sum(c * basis(n, L) for n, c in coef.items())
