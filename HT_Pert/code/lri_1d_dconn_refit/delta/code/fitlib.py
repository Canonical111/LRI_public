"""Least-squares fits of shift sequences F(L) to sums of L^-p log^j L terms, in mpmath (50 digits)."""
import mpmath as mp
import numpy as np

mp.mp.dps = 50


def term_val(L, p, j, shift=0):
    x = mp.mpf(L) + shift
    return x ** (-mp.mpf(p)) * mp.log(x) ** j


def fit(Ls, ys, terms, shift=0, weights=None):
    """Unweighted (or weighted) LS with unit-norm column scaling. Returns dict with coef (mp), predict fn,
    max residual, condition number estimate (float)."""
    n, m = len(Ls), len(terms)
    if n < m:
        return None
    A = mp.matrix(n, m)
    b = mp.matrix(n, 1)
    for i, L in enumerate(Ls):
        w = mp.mpf(1) if weights is None else mp.mpf(weights[i])
        for c, (p, j) in enumerate(terms):
            A[i, c] = w * term_val(L, p, j, shift)
        b[i] = w * mp.mpf(ys[i])
    norms = [mp.sqrt(sum(A[i, c] ** 2 for i in range(n))) for c in range(m)]
    for c in range(m):
        for i in range(n):
            A[i, c] /= norms[c]
    sol, res = mp.qr_solve(A, b)
    coef = [sol[c] / norms[c] for c in range(m)]
    # residuals
    r = [b[i] - sum(A[i, c] * sol[c] for c in range(m)) for i in range(n)]
    maxres = max(abs(float(x)) for x in r)
    # condition number via numpy on scaled matrix (float is fine for a diagnostic)
    An = np.array([[float(A[i, c]) for c in range(m)] for i in range(n)])
    sv = np.linalg.svd(An, compute_uv=False)
    cond = float(sv[0] / sv[-1]) if sv[-1] > 0 else np.inf

    def predict(L):
        return float(sum(coef[c] * term_val(L, p, j, shift) for c, (p, j) in enumerate(terms)))
    return dict(coef=coef, predict=predict, maxres=maxres, rms=float(mp.sqrt(sum(x**2 for x in r) / n)),
                cond=cond, terms=terms, shift=shift, n=n)


# ---------------------------------------------------------------- model families
NONDEC = {
    'N1': [(0, 0), (0, 1)],
    'N2': [(0, 0), (0, 1), (0, 2)],
    'N3': [(0, 0), (0, 1), (0, 2), (0, 3)],
    'N0': [(0, 0)],
    'N4': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)],
}
TAILS = {
    'h1': [(0.5, 0), (1, 0)],
    'h2': [(0.5, 0), (1, 0), (1.5, 0)],
    'h3': [(0.5, 0), (1, 0), (1.5, 0), (2, 0)],
    'h1l': [(0.5, 0), (0.5, 1), (1, 0)],
    'h2l': [(0.5, 0), (0.5, 1), (1, 0), (1.5, 0)],
    'h2L': [(0.5, 0), (1, 0), (1, 1), (1.5, 0)],
    'h2ll': [(0.5, 0), (0.5, 1), (1, 0), (1, 1)],
    'h3l': [(0.5, 0), (0.5, 1), (1, 0), (1, 1), (1.5, 0)],
    'h3ll': [(0.5, 0), (0.5, 1), (0.5, 2), (1, 0), (1.5, 0)],
    'i1': [(1, 0), (2, 0)],
    'i2': [(1, 0), (1, 1), (2, 0)],
    'i3': [(1, 0), (1, 1), (2, 0), (2, 1)],
}


def all_models(nondec=('N1', 'N2', 'N3'), tails=None):
    tails = tails or list(TAILS)
    out = []
    for a in nondec:
        for t in tails:
            out.append((a + '+' + t, NONDEC[a] + TAILS[t]))
    return out
