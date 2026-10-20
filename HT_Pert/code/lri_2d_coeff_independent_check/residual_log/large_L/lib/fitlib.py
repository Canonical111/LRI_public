#!/usr/bin/env python3
"""Least-squares tower fits y(L) = sum_j c_j f_j(L) for the large-L asymptotics (mpmath-free, column-scaled
numpy lstsq in float64; the data are exact to ~1e-12 so the fits are deterministic and the quoted
uncertainties are systematic: spread over ansaetze and fit windows)."""
import numpy as np

REF = {2: 0.308065413582197915296547609537, 3: -0.874850012652633689512263602361,
       4: 5.04886843135484700761231670996}
A2 = -40.0 / (81.0 * np.pi)       # C2(L) - C2(inf) = A2/L + ...
OMEGA1 = 4.5                      # C3 tail l/L coefficient = -A2*omega1


def basis(name, L):
    l = np.log(L)
    if name == "1":
        return np.ones_like(L)
    if name == "l":
        return l
    if name == "l2":
        return l * l
    if name == "L":
        return L
    # "lk/Lj"
    num, den = name.split("/")
    k = 0 if num == "1" else (1 if num == "l" else int(num[1:]))
    j = int(den[1:]) if len(den) > 1 else 1
    return l ** k / L ** j


def fit(L, y, names, Lmin, Lmax=None, fixed=None):
    """fixed: dict name -> value (subtracted, not fitted). Returns dict of coefficients and max residual."""
    sel = (L >= Lmin) & ((L <= Lmax) if Lmax else True)
    Ls, ys = L[sel].astype(float), y[sel].astype(float).copy()
    if fixed:
        for n, v in fixed.items():
            ys -= v * basis(n, Ls)
    X = np.column_stack([basis(n, Ls) for n in names])
    sc = np.abs(X).max(axis=0)
    coef, *_ = np.linalg.lstsq(X / sc, ys, rcond=None)
    coef = coef / sc
    res = ys - X @ coef
    return dict(zip(names, coef)), float(np.abs(res).max()), int(sel.sum())


def tower(order_logs_1, order_logs_2, order_logs_3=None):
    """Standard tower: 1/L with logs 0..k1, 1/L^2 with logs 0..k2, 1/L^3 with logs 0..k3."""
    names = []
    for k in range(order_logs_1 + 1):
        names.append(("1" if k == 0 else ("l" if k == 1 else f"l{k}")) + "/L")
    for k in range(order_logs_2 + 1):
        names.append(("1" if k == 0 else ("l" if k == 1 else f"l{k}")) + "/L2")
    if order_logs_3 is not None:
        for k in range(order_logs_3 + 1):
            names.append(("1" if k == 0 else ("l" if k == 1 else f"l{k}")) + "/L3")
    return names
