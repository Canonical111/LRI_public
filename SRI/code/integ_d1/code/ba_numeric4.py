"""Bethe-ansatz (delta = 0) magnetization-scheme flow to total degree 4: F = z + sum_{m>=1, m+n<=4} f_mn u^m z^n.
Same construction as ba_numeric.py (bivariate series in X and w = 1-K, mpmath), with u = O(w^2 X) and z = O(w), so 2u u^m z^n = O(w^{2m+n+2});
the fit uses all monomials with 2m+n <= 8 (this covers m+n <= 4) and the rows X^i w^j, j <= 10, which no other
monomial reaches.
Output lines '(m, n) value' (f_m_n_0), residual of the overdetermined fit, F10 and I2."""
import mpmath as mp, sys
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 60
NX, NW, JFIT = 9, 10, 10


def c_n(n):
    def g(w):
        eps = n * w
        inv_gamma = mp.fprod([(eps - j) for j in range(0, n)]) / mp.gamma(1 + eps)
        return (-1) ** (n + 1) * mp.gamma(mp.mpf(1) / 2 + eps) / (mp.sqrt(mp.pi) * mp.factorial(n)) * inv_gamma
    return mp.taylor(g, 0, NW)


def Z0(): return [[mp.mpf(0)] * (NW + 1) for _ in range(NX + 1)]


def mul(A, B):
    C = Z0()
    for i in range(NX + 1):
        for j in range(NW + 1):
            if A[i][j] == 0: continue
            for k in range(NX + 1 - i):
                for l in range(NW + 1 - j):
                    C[i + k][j + l] += A[i][j] * B[k][l]
    return C


def add(A, B, s=1): return [[A[i][j] + s * B[i][j] for j in range(NW + 1)] for i in range(NX + 1)]
def scal(A, s): return [[A[i][j] * s for j in range(NW + 1)] for i in range(NX + 1)]
def XdX(A): return [[A[i][j] * i for j in range(NW + 1)] for i in range(NX + 1)]


one = Z0(); one[0][0] = mp.mpf(1)
W = Z0(); W[0][1] = mp.mpf(1)
M = Z0(); M[0][0] = mp.mpf(1)
for n in range(1, NX + 1):
    cn = c_n(n)
    for j in range(NW + 1): M[n][j] -= cn[j]
d = add(M, one, -1); logM = Z0(); term = [row[:] for row in one]
for k in range(1, NX + 1):
    term = mul(term, d); logM = add(logM, scal(term, mp.mpf((-1) ** (k + 1)) / k))
zM = add(mul(add(one, W, -1), mul(M, M)), one, -1)
uM = scal(mul(W, XdX(logM)), -1)
bu = scal(mul(W, XdX(uM)), -2)
mons = [(m, n) for m in range(1, 5) for n in range(0, 9) if 2 * m + n <= 8]
upow = {0: one}; zpow = {0: one}
for k in range(1, 9):
    upow[k] = mul(upow[k - 1], uM); zpow[k] = mul(zpow[k - 1], zM)
rhs = add(bu, scal(mul(uM, zM), 2), -1)
cols = [scal(mul(upow[m + 1], zpow[n]), 2) for (m, n) in mons]
rows = [(i, j) for i in range(NX + 1) for j in range(JFIT + 1)]
keep = [r for r in rows if any(cols[c][r[0]][r[1]] != 0 for c in range(len(mons)))]
A = mp.matrix([[cols[c][i][j] for c in range(len(mons))] for (i, j) in keep])
b = mp.matrix([rhs[i][j] for (i, j) in keep])
sol = mp.lu_solve(A.T * A, A.T * b)
res = mp.norm(A * sol - b)
f = {mons[c]: sol[c] for c in range(len(mons))}
for mo in mons: print(mo, mp.nstr(f[mo], mp.mp.dps - 8))
print('rows', len(keep), 'unknowns', len(mons), 'residual norm', mp.nstr(res, 5))
print('F10 =', mp.nstr(f[(1, 0)], 25))
print('I2 = F20 - F11/2 - F12 =', mp.nstr(f[(2, 0)] - f[(1, 1)] / 2 - f[(1, 2)], 25))
