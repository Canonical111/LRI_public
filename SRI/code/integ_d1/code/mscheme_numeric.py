"""Numeric magnetization-scheme pipeline (same definitions as mscheme_invariants.py, truncated power series in mpmath):
F(u, X, delta) = X + sum f[m,n,k] u^m X^n delta^k;  u* = delta/4, F(u*, X*, delta) = 0;
T_h = 2u* F_u, D_h = -8u*(1+X*) F_X;  T = (1-delta/2) T_h, D = (1-delta/2)^2 D_h;
Delta_eps = 1 + T/2 - sqrt(T^2/4 - D),  delta = 2 t^2,  C_n = [t^n] Delta_eps.
C_{2N-1}, C_{2N} use only the f's of total degree m+n+k <= N."""
import mpmath as mp


def smul(a, b, N):
    r = [mp.mpf(0)] * (N + 1)
    for i, x in enumerate(a[:N + 1]):
        if x == 0: continue
        for j, y in enumerate(b[:N + 1 - i]):
            r[i + j] += x * y
    return r


def spow(a, p, N):
    r = [mp.mpf(1)] + [mp.mpf(0)] * N
    for _ in range(p): r = smul(r, a, N)
    return r


def C_numeric(f, order):
    """f: {(m,n,k): value} (the exact X term and f_0_n_0 = 0 (n >= 2) are implicit). Returns [C_1..C_{2 order}]."""
    N = order
    d = [mp.mpf(0), mp.mpf(1)] + [mp.mpf(0)] * (N - 1)          # delta
    u = [mp.mpf(0), mp.mpf(1) / 4] + [mp.mpf(0)] * (N - 1)      # u* = delta/4
    terms = {k: v for k, v in f.items() if sum(k) <= N and not (k[0] == 0 and k[2] == 0)}

    def F_and_derivs(X):
        F = list(X); Fu = [mp.mpf(0)] * (N + 1); FX = [mp.mpf(1)] + [mp.mpf(0)] * N
        for (m, n, k), c in terms.items():
            base = smul(spow(d, k, N), [c] + [mp.mpf(0)] * N, N)
            mon = smul(smul(spow(u, m, N), spow(X, n, N), N), base, N)
            F = [a + b for a, b in zip(F, mon)]
            if m >= 1:
                t = smul(smul(spow(u, m - 1, N), spow(X, n, N), N), base, N)
                Fu = [a + m * b for a, b in zip(Fu, t)]
            if n >= 1:
                t = smul(smul(spow(u, m, N), spow(X, n - 1, N), N), base, N)
                FX = [a + n * b for a, b in zip(FX, t)]
        return F, Fu, FX
    # fixed point by iteration X <- X - F (F = X + ...): converges order by order
    X = [mp.mpf(0)] * (N + 1)
    for _ in range(N + 2):
        F, _, _ = F_and_derivs(X)
        X = [a - b for a, b in zip(X, F)]
    F, Fu, FX = F_and_derivs(X)
    assert max(abs(x) for x in F) < mp.mpf(10) ** (-mp.mp.dps + 8), 'fixed point not converged'
    Th = smul(smul([mp.mpf(2)] + [0] * N, u, N), Fu, N)
    onepX = [X[0] + 1] + X[1:]
    Dh = smul(smul(smul([mp.mpf(-8)] + [0] * N, u, N), onepX, N), FX, N)
    hm = [mp.mpf(1), mp.mpf(-1) / 2] + [mp.mpf(0)] * (N - 1)
    T = smul(hm, Th, N); D = smul(smul(hm, hm, N), Dh, N)
    # to t: delta = 2 t^2 -> coefficient of t^{2i} = 2^i x_i
    M = 2 * N + 1
    Tt = [mp.mpf(0)] * (M + 1); Dt = [mp.mpf(0)] * (M + 1)
    for i in range(N + 1):
        Tt[2 * i] = T[i] * 2 ** i; Dt[2 * i] = D[i] * 2 ** i
    disc = [a / 4 - b for a, b in zip(smul(Tt, Tt, M), Dt)]           # = 4 t^2 (1 + ...)
    q = [disc[i + 2] / 4 for i in range(M - 1)] + [mp.mpf(0), mp.mpf(0)]
    # sqrt(q) with q0 = 1
    s = [mp.mpf(0)] * (M + 1); s[0] = mp.sqrt(q[0])
    for i in range(1, M + 1):
        s[i] = (q[i] - sum(s[j] * s[i - j] for j in range(1, i))) / (2 * s[0])
    root = [mp.mpf(0)] + [2 * x for x in s[:M]]                      # 2 t sqrt(q)
    De = [(1 if i == 0 else 0) + Tt[i] / 2 - root[i] for i in range(M + 1)]
    return [De[i] for i in range(1, 2 * N + 1)]
