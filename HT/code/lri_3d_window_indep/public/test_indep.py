#!/usr/bin/env python3
"""`make -f public.mk test`: structural checks of the clean-room solver and one fixed-coupling comparison.

The checks of the session's t_basic.py (not shipped: it read a file of the perturbative package by an absolute path,
so the counts it took from there are written out below) and of t_fixed.py:
  * the Gegenbauer addition identity behind the mode weights u2(x, n, l), k <= 12;
  * the number of J = 0 bath states at L = 2, 4, 6, 8: 3, 10, 33, 110 (the perturbative package lri_3d_hpc,
    results/reference_coefficients_L14.json, scheme raw, field scalar_bath_states);
  * rotation invariance of the scalar vertices (two sphere points) and the setup checks of Model;
  * the free spectrum at r = g = 0, L = 6 (even: 0, 2x, ...; odd: x, ...);
  * one production point at fixed couplings: L = 8, x = 0.7, window scheme, K = 16, against indep_extract.json (1e-10).
Needs scipy >= 1.15 (scipy.special.sph_harm_y). About a minute on one core.
"""
import json, math, sys, time
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import numpy as np
from scipy.special import eval_gegenbauer, eval_legendre
from indep_ht3d import Model, u2

rows = []
def add(name, ok, detail): rows.append((name, 'PASS' if ok else 'FAIL', detail))

x = 0.6; err = 0.
for k in range(0, 13):
    for mu in (-0.7, 0.2, 0.9):
        rhs = sum((2 * l + 1) * u2(x, (k - l) // 2, l) * eval_legendre(l, mu) for l in range(k % 2, k + 1, 2))
        err = max(err, abs(eval_gegenbauer(k, x, mu) - rhs))
add('gegenbauer', err < 1e-12, f'max err {err:.1e}')
for L, n in ((2, 3), (4, 10), (6, 33), (8, 110)):
    m = Model(L, x); c = m.checks
    ok = c['scalar_states'] == n and c['point_dependence'] < 1e-10 and c['orth'] < 1e-12 and c['J2_null_max'] < 1e-10
    add(f'scalar states L={L}', ok, f"{c['scalar_states']} (expected {n}); point dependence {c['point_dependence']:.1e}")
m = Model(6, x); s = m.solve(0.0, 0.0, K=12, window=False, nroots=4)
ok = abs(s['even'][1] - 2 * x) < 1e-10 and abs(s['odd'][0] - x) < 1e-10
add('free spectrum L=6', ok, f"even {np.round(s['even'], 10).tolist()} odd {np.round(s['odd'], 10).tolist()}")
ext = json.load(open(PKG / 'indep_extract.json'))
e = next(e for e in ext if e['camp'] == 'grid18' and abs(e['delta'] - 0.7) < 1e-9 and e['bath_cut'] == 8 and e['window'] == 'vacuum')
t = time.time(); m = Model(8, 0.7); s = m.solve(e['r'], e['g'], K=16, window=True, nroots=3)
d = s['even'][1] - e['Delta_thermal']
add('fixed L=8 x=0.7 K=16', abs(d) < 1e-10, f'dDelta_E {d:+.1e} vs production record grid18 x0.7 window_L8 ({time.time() - t:.0f} s)')
for r in rows: print(f'{r[0]:<22} {r[1]:<5} {r[2]}')
bad = [r for r in rows if r[1] != 'PASS']
print(f'{len(rows) - len(bad)}/{len(rows)} passed')
sys.exit(1 if bad else 0)
