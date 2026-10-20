import numpy as np
from scipy.optimize import linprog
rng = np.random.default_rng(1)
best = []
for it in range(200000):
    d = 1.7
    h = d / 2
    n1, n2, n3, a3, a4 = rng.uniform(0.15, 1.2, 5)
    lam = n1 + n2 + n3 - h
    E1 = -2 + n2 + n3 + 2 * a4 - d; E2 = -2 + n1 + n3 + 2 * a3 - d; E3 = -6 - E1 - E2
    if max(E1, E2, E3) > -1.6: continue
    # variables c1, c2, delta ; maximize delta
    # constraints: c1 + delta <= 0 ; c1 + delta <= n2-lam ; -c1 + delta <= -(a3-h) ; same for c2 ; -(c1+c2) + delta <= lam ; -(c1+c2)+delta <= n3 ; (c1+c2) + delta <= a3+a4-h
    A = [[1, 0, 1], [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, 1, 1], [0, -1, 1], [-1, -1, 1], [-1, -1, 1], [1, 1, 1]]
    b = [0, n2 - lam, -(a3 - h), 0, n1 - lam, -(a4 - h), lam, n3, a3 + a4 - h]
    res = linprog([0, 0, -1], A_ub=A, b_ub=b, bounds=[(None, None), (None, None), (None, 1)])
    if res.status == 0 and -res.fun > 0.12:
        best.append((-res.fun, (n1, n2, n3, a3, a4), res.x[:2], (E1, E2, E3)))
best.sort(key=lambda x: -x[0])
for b_ in best[:8]:
    print('delta=%.3f nu=(%.3f,%.3f,%.3f) a=(%.3f,%.3f) c=(%.3f,%.3f) E=(%.2f,%.2f,%.2f)' % (b_[0], *b_[1], *b_[2], *b_[3]))
