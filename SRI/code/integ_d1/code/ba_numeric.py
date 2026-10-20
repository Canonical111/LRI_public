"""Bethe-ansatz magnetization-scheme flow: numeric bivariate series in (X, w) with mpmath, then fit F = z + sum f_mn u^m z^n."""
import mpmath as mp, numpy as np, itertools
mp.mp.dps = 60
NX, NW = 5, 10
def taylor_w(fun, order):
    return mp.taylor(fun, 0, order)
def c_n(n):
    def g(w):
        eps = n * w
        inv_gamma = mp.fprod([(eps - j) for j in range(0, n)]) / mp.gamma(1 + eps)
        return (-1)**(n + 1) * mp.gamma(mp.mpf(1)/2 + eps) / (mp.sqrt(mp.pi) * mp.factorial(n)) * inv_gamma
    return taylor_w(g, NW)
Z0 = lambda: np.array([[mp.mpf(0)] * (NW + 1) for _ in range(NX + 1)], dtype=object)  # [i][j]: X^i w^j
def mul(A, B):
    C = Z0()
    for i in range(NX + 1):
        for j in range(NW + 1):
            if A[i][j] == 0: continue
            for k in range(NX + 1 - i):
                for l in range(NW + 1 - j):
                    C[i + k][j + l] += A[i][j] * B[k][l]
    return C
one = Z0(); one[0][0] = mp.mpf(1)
W = Z0(); W[0][1] = mp.mpf(1)
M = Z0(); M[0][0] = mp.mpf(1)
for n in range(1, NX + 1):
    cn = c_n(n)
    for j in range(NW + 1): M[n][j] -= cn[j]
d = M - one; logM = Z0(); term = one.copy()
for k in range(1, NX + 1):
    term = mul(term, d); logM = logM + term * (mp.mpf((-1)**(k + 1)) / k)
def XdX(A):
    B = Z0()
    for i in range(NX + 1):
        for j in range(NW + 1): B[i][j] = A[i][j] * i
    return B
zM = mul(one - W, mul(M, M)) - one
uM = -mul(W, XdX(logM))
bu = -2 * mul(W, XdX(uM))
# monomial basis u^m z^n for F, fit 2 u F = bu
mons = [(m, n) for m in range(1, 5) for n in range(0, 5) if 2*m + n <= 5]
upow = {0: one}; zpow = {0: one}
for k in range(1, 6): upow[k] = mul(upow[k - 1], uM); zpow[k] = mul(zpow[k - 1], zM)
rhs = bu - 2 * mul(uM, zM)           # remove the exact z term of F
cols = [2 * mul(upow[m + 1], zpow[n]) for (m, n) in mons]
rows = [(i, j) for i in range(NX + 1) for j in range(NW + 1) if j <= 7]
A = mp.matrix([[cols[c][i][j] for c in range(len(mons))] for (i, j) in rows])
b = mp.matrix([rhs[i][j] for (i, j) in rows])
# least squares via normal equations restricted to rows that matter
for c in range(len(mons)):
    nz = [(rows[r], mp.nstr(A[r, c], 5)) for r in range(len(rows)) if A[r, c] != 0][:3]
    print('col', mons[c], 'first nonzero rows', nz)
keep = [r for r in range(len(rows)) if any(A[r, c] != 0 for c in range(len(mons)))]
A2 = mp.matrix([[A[r, c] for c in range(len(mons))] for r in keep]); b2 = mp.matrix([b[r] for r in keep])
AtA = A2.T * A2; Atb = A2.T * b2
sol = mp.lu_solve(AtA, Atb); res = mp.norm(A2 * sol - b2)
f = {mons[c]: sol[c] for c in range(len(mons))}
for mo in mons: print(mo, mp.nstr(f[mo], 50))
print('residual norm', mp.nstr(res, 5))
print('F10 =', mp.nstr(f[(1, 0)], 25))
print('I2 = F20 - F11/2 - F12 =', mp.nstr(f[(2, 0)] - f[(1, 1)] / 2 - f[(1, 2)], 25))
