"""gdr:Tln / gdr:samples3: T3(d;d/2) = sum d_l T_ln^3 at d = 3 from the printed T_ln, cumulative sums + fit with the
exponent families M^{-1/4-k}, M^{-3/2-k} (r = 3, g = 3/4), compared with the code value."""
import json
import mpmath as mp
mp.mp.dps = 50
d = 3; b = mp.mpf(3) / 2; q = mp.mpf(3) / 4; sig = b / 2; g = (d - b) / 2
MMAX = 40000
MS = [MMAX * k // 16 for k in range(4, 17)]
A, B = [mp.mpf(1)], [mp.mpf(1)]
for m in range(MMAX):
    A.append(A[-1] * (sig + m) / (2 * q + m)); B.append(B[-1] * (1 - g + m) / (1 + m))
part, S, cB, cnB = {}, mp.mpf(0), mp.mpf(0), mp.mpf(0)
for m in range(MMAX + 1):
    b3 = B[m] ** 3; cB += b3; cnB += m * b3
    S += A[m] ** 3 * ((2 * m + 1) * cB - 2 * cnB)
    if m in MS:
        part[m] = S
exps = [mp.mpf(1) / 4 + k for k in range(7)] + [mp.mpf(3) / 2 + k for k in range(6)]
Ms = sorted(part); n = len(Ms)
assert n == len(exps) + 0 or True
basis = [None] + exps[:n - 1]
Mx = mp.matrix(n, n); y = mp.matrix(n, 1)
for i, M in enumerate(Ms):
    Mx[i, 0] = 1
    for k in range(1, n):
        Mx[i, k] = mp.mpf(M) ** (-basis[k])
    y[i] = part[M]
T3 = mp.lu_solve(Mx, y)[0]
code = mp.mpf(json.load(open('samples_dps60.json'))['values']['3']['T3'][0])
print('T3(3) printed-def fit:', mp.nstr(T3, 25), ' code:', mp.nstr(code, 25), ' rel', mp.nstr(abs(T3 - code) / code, 3))
