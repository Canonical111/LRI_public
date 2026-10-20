"""Verifier (hi72) high-precision weighted least squares with python-flint arb (own implementation).
Solves min || W (X c - y) || via column-scaled normal equations at PREC bits; inputs are exact doubles.
"""
import math
import numpy as np
from flint import arb, arb_mat, ctx
ctx.prec = 320


def A(x):
    return arb(float(x)) if not isinstance(x, arb) else x


def solve(cols, y, w=None, want_pinv0=False):
    """cols: list of lists of arb (len n each); y: list of arb; w: optional per-row weights (floats, multiply rows).
    returns coef (arb list), residual floats (unweighted), and optionally row 0 of pinv (float, acting on unweighted y)."""
    n = len(y); m = len(cols)
    if w is None:
        wa = [arb(1)] * n
    else:
        wa = [arb(float(v)) for v in w]
    sc = [sum((cols[j][i] * wa[i]) ** 2 for i in range(n)).sqrt() for j in range(m)]
    X = arb_mat(n, m)
    for i in range(n):
        for j in range(m):
            X[i, j] = cols[j][i] * wa[i] / sc[j]
    Y = arb_mat(n, 1, [y[i] * wa[i] for i in range(n)])
    Xt = X.transpose()
    G = Xt * X
    s = G.solve(Xt * Y, algorithm='approx')
    coef = [s[j, 0] / sc[j] for j in range(m)]
    res = []
    for i in range(n):
        v = -y[i]
        for j in range(m):
            v += coef[j] * cols[j][i]
        res.append(float(v.mid()))
    out = dict(coef=coef, res=np.array(res))
    if want_pinv0:
        Gi = G.solve(arb_mat([[arb(1) if a == b else arb(0) for b in range(m)] for a in range(m)]), algorithm='approx')
        P = Gi * Xt
        out['p0'] = np.array([float((P[0, i] * wa[i] / sc[0]).mid()) for i in range(n)])
    return out


def evalc(coef, cols_at):
    return [float(sum((coef[j] * cols_at[j][i] for j in range(len(coef))), arb(0)).mid()) for i in range(len(cols_at[0]))]
