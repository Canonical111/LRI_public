import numpy as np, itertools
from scipy.optimize import linprog
rng = np.random.default_rng(7)
def frac_dist(x):
    return abs(x - round(x))
best = []
for it in range(400000):
    d = 1.7; h = d / 2
    n1, n2, n3, a3, a4 = np.round(rng.uniform(0.05, 1.3, 5), 3)
    lam = n1 + n2 + n3 - h
    E1 = -2 + n2 + n3 + 2 * a4 - d; E2 = -2 + n1 + n3 + 2 * a3 - d; E3 = -6 - E1 - E2
    if max(E1, E2, E3) > -1.05: continue
    # genericity: pole-line constants (z1: 0, n2-lam, a3-h ; z2: 0, n1-lam, a4-h ; w: -lam, -n3, a3+a4-h) and pairwise
    consts = [0, n2 - lam, h - a3, 0, n1 - lam, h - a4, lam, n3, a3 + a4 - h]
    z1c = [0, n2 - lam, a3 - h]; z2c = [0, n1 - lam, a4 - h]; wc = [-lam, -n3, a3 + a4 - h]
    gen = min([frac_dist(x - y) for x, y in itertools.combinations(z1c, 2)] + [frac_dist(x - y) for x, y in itertools.combinations(z2c, 2)]
              + [frac_dist(x - y) for x, y in itertools.combinations(wc, 2)]
              + [frac_dist(x + y - z) for x in z1c for y in z2c for z in wc]
              + [frac_dist(a3), frac_dist(a4), frac_dist(d - a3 - a4), frac_dist(n1), frac_dist(n2), frac_dist(n3), frac_dist(d - n1 - n2 - n3)])
    if gen < 0.04: continue
    A = [[1, 0, 1], [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, 1, 1], [0, -1, 1], [-1, -1, 1], [-1, -1, 1], [1, 1, 1]]
    b = [0, n2 - lam, -(a3 - h), 0, n1 - lam, -(a4 - h), lam, n3, a3 + a4 - h]
    res = linprog([0, 0, -1], A_ub=A, b_ub=b, bounds=[(None, None), (None, None), (None, 1)])
    if res.status == 0 and -res.fun > 0.04:
        best.append((-res.fun, (n1, n2, n3, a3, a4), res.x[:2], (E1, E2, E3), gen))
best.sort(key=lambda x: -x[0])
for b_ in best[:10]:
    print('delta=%.3f nu=(%.3f,%.3f,%.3f) a=(%.3f,%.3f) c=(%.3f,%.3f) E=(%.2f,%.2f,%.2f) gen=%.3f' % (b_[0], *b_[1], *b_[2], *b_[3], b_[4]))
