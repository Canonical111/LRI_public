#!/usr/bin/env python3
"""Reconstruct the full quadratic jet (15 coefficients in p1,p2,z1,z2,de) of J - J^Gamma_jet at the B point from
[t^2] along random lines, and check it equals K z1 z2 (gs:Bjet).  Also records [t^-3..t^1] (must vanish)."""
import sys, json, time, itertools
import numpy as np, mpmath as mp
from kjet_general import gamma_side, RegMB, idx_of

dstr = sys.argv[1]; digits = int(sys.argv[2]); nlines = int(sys.argv[3]); seed = int(sys.argv[4]) if len(sys.argv) > 4 else 11
mp.mp.dps = digits + 20
d = mp.mpf(dstr); q = d / 4
rng = np.random.default_rng(seed)
M = 32
reg = None
rows = []; rhs = []; lows = []
names = ['p1', 'p2', 'z1', 'z2', 'de']
pairs = [(i, j) for i in range(5) for j in range(i, 5)]
for L in range(nlines):
    v = [mp.mpf(str(x)) for x in np.round(rng.uniform(-1, 1, 5), 3)]
    if abs(v[0]) < 0.2 or abs(v[1]) < 0.2:
        v[0] += mp.sign(v[0]) * mp.mpf('0.3'); v[1] += mp.sign(v[1]) * mp.mpf('0.3')
    vm = max(abs(x) for x in v)
    r = q / (8 * vm)
    if reg is None:
        reg = RegMB(dstr, digits, mp.nstr(-q / 3, 30), mp.nstr(-q / 3, 30), float(q / 3 - 1.2 * q / 8))
    cg = [mp.mpc(0)] * 7; cr = [mp.mpc(0)] * 4
    for k in range(M):
        t = r * mp.expj(2 * mp.pi * (k + mp.mpf(1) / 7) / M)
        pt = [t * v[0], t * v[1], t * v[2], t * v[3], d / 2 + t * v[4]]
        gs, _ = gamma_side(d, pt)
        jr = reg.value(*idx_of(d, pt))
        for j in range(-3, 4): cg[j + 3] += gs * t ** (-j) / M
        for j in range(4): cr[j] += jr * t ** (-j) / M
    tot = {j: mp.re(cg[j + 3] + (cr[j] if j >= 0 else 0)) for j in range(-3, 3)}
    lows.append(max(abs(tot[j]) for j in range(-3, 2)))
    rows.append([float(v[i] * v[j]) for (i, j) in pairs]); rhs.append(tot[2])
    print('line %2d v=%s  max|t^-3..t^1|=%s  [t^2]=%s  [t^2]/(vz1 vz2)=%s' % (L, [float(x) for x in v], mp.nstr(lows[-1], 3), mp.nstr(tot[2], 18),
          mp.nstr(tot[2] / (v[2] * v[3]), 18)), flush=True)
# exact-arithmetic least squares in mpmath
A = mp.matrix([[mp.mpf(x) for x in row] for row in rows]); b = mp.matrix(rhs)
sol = mp.lu_solve(A.T * A, A.T * b)
print('quadratic form coefficients (expect only z1*z2 = K):')
out = {}
for (i, j), c in zip(pairs, sol):
    key = names[i] + '*' + names[j] if i != j else names[i] + '^2'
    out[key] = mp.nstr(c, 18)
    print('   %-8s %s' % (key, mp.nstr(c, 18)))
resid = A * sol - b
print('max residual', mp.nstr(max(abs(x) for x in resid), 3))
json.dump(dict(d=dstr, nlines=nlines, quadratic_form=out, max_low_order=mp.nstr(max(lows), 3)), open('bjet_quadform_d%s.json' % dstr, 'w'), indent=1)
