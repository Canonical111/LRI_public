#!/usr/bin/env python3
"""
Closed forms at order eps^2 (derived in README.md, section 6), independent of the Fock-space codes:

  E_v^(2)(L) = -(L+2)(L+4)/864                                   (vacuum, any scheme)
  C_2(L)     = s_2 - s_1 - s_3/3,  s_p = S_p - S_0,
  S_p = -(1/1296) sum_{m=0}^{4} C(4,m)^2 sum_q Z_{m,q}(p) sum_{N<=L} F_m(N) / (N + (q - p + m)/2),

where m = number of non-zero-mode quanta created by V acting on |p>, q = final zero-mode number,
Z_{m,q}(p) = |<q| :phi_0^{4-m}: |p>|^2 (zero-mode matrix elements, phi_0 = A_00 + A_00^dag) and
F_m(N) = m! [u^{N/2} v^{N/2}] ( (1-u)^{-1/2} (1-v)^{-1/2} - 1 )^m   (theta-averaged m-quantum norm at level N).
"""
from fractions import Fraction as Fr
from math import comb, factorial
import sys


def series_coeffs(alpha, nmax):
    """[u^n] (1-u)^{-alpha} = (alpha)_n / n!, n = 0..nmax (alpha rational)."""
    c = [Fr(1)]
    for n in range(1, nmax + 1):
        c.append(c[-1] * (alpha + n - 1) / n)
    return c


def F_table(L):
    """F[m][N] for m = 0..4, N = 0..L (even N only nonzero)."""
    n = L // 2
    # h(u)^k coefficients: (1-u)^{-k/2}
    hk = {k: series_coeffs(Fr(k, 2), n) for k in range(0, 5)}
    F = {}
    for m in range(5):
        F[m] = {}
        for N in range(0, L + 1, 2):
            a = N // 2
            # (h(u)h(v) - 1)^m = sum_k C(m,k) (-1)^{m-k} h(u)^k h(v)^k ; J=0 level-N part = coefficient u^a v^a
            val = sum(comb(m, k) * (-1) ** (m - k) * hk[k][a] ** 2 for k in range(m + 1))
            F[m][N] = factorial(m) * val
    return F


def Zsq(k, p, q):
    """|<q| :phi_0^k: |p>|^2 with :phi_0^k: = sum_j C(k,j) A^dag^j A^{k-j} (orthonormal zero-mode states)."""
    # q = p + 2j - k
    if (q - p + k) % 2:
        return 0
    j = (q - p + k) // 2
    if j < 0 or j > k or p - k + j < 0 or q < 0:
        return 0
    mid = p - k + j
    return Fr(comb(k, j) ** 2 * factorial(p) * factorial(q), factorial(mid) ** 2)


def S(p, L, F):
    tot = Fr(0)
    for m in range(5):
        k = 4 - m
        for q in range(max(0, p - k), p + k + 1):
            if m == 0 and q == p:
                continue
            z = Zsq(k, p, q)
            if not z:
                continue
            shift = Fr(q - p + m, 2)
            s = Fr(0)
            for N in range(0, L + 1, 2):
                f = F[m][N]
                if f:
                    s += f / (N + shift)
            tot += comb(4, m) ** 2 * z * s
    return -tot / 1296


def C2(L):
    F = F_table(L)
    Sp = [S(p, L, F) for p in range(4)]
    s = [x - Sp[0] for x in Sp]
    return s[2] - s[1] - s[3] / 3, Sp


def Ev2(L):
    return Fr(-(L + 2) * (L + 4), 864)


if __name__ == "__main__":
    Lmax = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    for L in range(0, Lmax + 1, 2):
        c2, Sp = C2(L)
        assert Sp[0] == Ev2(L)
        print(L, c2, float(c2), "E_v^(2) =", Ev2(L), "S_p =", [str(x) for x in Sp])


def C2_float(L, dps=30):
    """Same closed form evaluated in mpmath floating point (for large L)."""
    import mpmath as mp
    mp.mp.dps = dps
    n = L // 2
    hk = {}
    for k in range(5):
        c = [mp.mpf(1)]
        for i in range(1, n + 1):
            c.append(c[-1] * (mp.mpf(k) / 2 + i - 1) / i)
        hk[k] = c
    F = {m: {N: mp.factorial(m) * sum(comb(m, k) * (-1) ** (m - k) * hk[k][N // 2] ** 2 for k in range(m + 1))
             for N in range(0, L + 1, 2)} for m in range(5)}
    Sp = []
    for p in range(4):
        tot = mp.mpf(0)
        for m in range(5):
            k = 4 - m
            for q in range(max(0, p - k), p + k + 1):
                if m == 0 and q == p:
                    continue
                z = Zsq(k, p, q)
                if not z:
                    continue
                shift = mp.mpf(q - p + m) / 2
                s = mp.fsum(F[m][N] / (N + shift) for N in range(0, L + 1, 2) if F[m][N] != 0)
                tot += comb(4, m) ** 2 * mp.mpf(z.numerator) / z.denominator * s
        Sp.append(-tot / 1296)
    s = [x - Sp[0] for x in Sp]
    return s[2] - s[1] - s[3] / 3
