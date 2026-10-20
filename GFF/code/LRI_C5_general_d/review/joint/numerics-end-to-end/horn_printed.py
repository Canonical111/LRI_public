#!/usr/bin/env python3
"""Independent evaluation of the PRINTED sample definitions of gdr:samples4 (kappa_0, kappa_h, rho_0, rho_h, h_u, s_u)
and gdr:samples3/gdr:Tln (T3) at d = 1, 2, 3, b = d/2, by cumulative sums + Richardson in 1/M (integer exponents at
b = d/2), compared with the code samples (samples_dps60.json)."""
import json
import mpmath as mp
mp.mp.dps = 45
pi = mp.pi
MS = [600 * k for k in range(1, 13)]
MMAX = MS[-1]


def extrap(partial):
    """partial: dict M -> S_M; fit S + sum_{k=1}^{n-1} c_k M^{-k}"""
    Ms = sorted(partial)
    n = len(Ms)
    A = mp.matrix(n, n); y = mp.matrix(n, 1)
    for i, M in enumerate(Ms):
        A[i, 0] = 1
        for k in range(1, n):
            A[i, k] = mp.mpf(M) ** (-k)
        y[i] = partial[M]
    return mp.lu_solve(A, y)[0]


def ratio_seq(ups, downs, p, M):
    X = [mp.mpf(1)]
    for m in range(M):
        v = X[-1]
        for u in ups:
            v *= (u + m)
        for w in downs:
            v /= (w + m)
        X.append(v)
    return [x ** p for x in X]


def dl(d, l):
    if d == 1:
        return 1 if l <= 1 else 0
    if d == 2:
        return 1 if l == 0 else 2
    return 2 * l + 1


def h_u(d, u, x, y, r=4):
    A = ratio_seq([u + x], [u + y], r, MMAX)
    B = ratio_seq([u + 1 - y], [u + 1 - x], r, MMAX)
    # inner I_m = sum_{n<=m} d_{m-n} B_n, built incrementally for polynomial d_l
    part, S = {}, mp.mpf(0)
    cB, cnB = mp.mpf(0), mp.mpf(0)
    for m in range(MMAX + 1):
        cB += B[m]; cnB += m * B[m]
        if d == 1:
            I = B[m] + (B[m - 1] if m >= 1 else 0)
        elif d == 2:
            I = 2 * cB - B[m]
        else:
            I = (2 * m + 1) * cB - 2 * cnB
        S += A[m] * I
        if m in MS:
            part[m] = S
    return extrap(part)


def s_u(d, u, x, y, r=4):
    a = ratio_seq([u + x], [u + y], r, MMAX)
    if d == 1:
        return (a[0] ** 2 + 2 * a[0] * a[1]) if u == 0 else a[0] ** 2
    p0, p1, S0, S1 = {}, {}, mp.mpf(0), mp.mpf(0)
    for j in range(MMAX + 1):
        S0 += a[j]; S1 += j * a[j]
        if j in MS:
            p0[j] = S0; p1[j] = S1
    M0, M1 = extrap(p0), extrap(p1)
    if d == 2:
        return 2 * M0 ** 2 - (a[0] ** 2 if u == 0 else 0)
    return 4 * M0 * M1 + (4 * u + 1) * M0 ** 2


def T3(d, b):
    q = mp.mpf(d) / 4; sig = b / 2; g = (d - b) / 2
    # T_ln = (sig)_{l+n} (1-g)_n / ((2q)_{l+n} n!) ; sum d_l T^3 with m = l+n
    return h_like(d, [sig], [2 * q], [1 - g], [1], 3)


def h_like(d, aup, adn, bup, bdn, r):
    A = ratio_seq(aup, adn, r, MMAX)
    B = ratio_seq(bup, bdn, r, MMAX)
    part, S, cB, cnB = {}, mp.mpf(0), mp.mpf(0), mp.mpf(0)
    for m in range(MMAX + 1):
        cB += B[m]; cnB += m * B[m]
        I = (B[m] + (B[m - 1] if m >= 1 else 0)) if d == 1 else ((2 * cB - B[m]) if d == 2 else (2 * m + 1) * cB - 2 * cnB)
        S += A[m] * I
        if m in MS:
            part[m] = S
    return extrap(part)


samp = json.load(open('samples_dps60.json'))['values']
for d in (1, 2, 3):
    b = mp.mpf(d) / 2
    x, y = b / 4, mp.mpf(d) / 2 - b / 4
    sig, g = b / 2, (d - b) / 2
    Nb = mp.gamma(mp.mpf(d) / 2) * mp.gamma(g) / mp.gamma(sig)
    sb = mp.sin(pi * b / 2)
    k0 = Nb * mp.sin(pi * x) ** 2 * mp.gamma(x) ** 2 / mp.gamma(y) ** 2
    kh = Nb * mp.cos(pi * x) ** 2 * mp.gamma(mp.mpf(1) / 2 + x) ** 2 / mp.gamma(mp.mpf(1) / 2 + y) ** 2
    r0 = x * (1 - y) / (y * (1 - x)); rh = (1 - 2 * y) / (1 - 2 * x)
    hx, h1, hh = h_u(d, x, x, y), h_u(d, 1, x, y), h_u(d, mp.mpf(1) / 2, x, y)
    s0, sh = s_u(d, 0, x, y), s_u(d, mp.mpf(1) / 2, x, y)
    XT = (pi * sb) ** 4 * hx
    X0 = k0 ** 4 * (s0 + 2 * r0 ** 4 * h1)
    Xh = kh ** 4 * (sh + 2 * rh ** 4 * hh)
    t3 = T3(d, b)
    c = samp[str(d)]
    rel = lambda a, k: mp.nstr(abs(a - mp.mpf(k)) / abs(mp.mpf(k)), 3)
    print('d=%d  X_T %s  X_0 %s  X_1/2 %s  T3 %s   (X_T=%s)' % (d, rel(XT, c['XT']), rel(X0, c['X0']), rel(Xh, c['Xh']),
          rel(t3, c['T3'][0]), mp.nstr(XT, 20)), flush=True)
