#!/usr/bin/env python3
"""C63d, OPE review 2026-10-16: own Borel-Pade evaluation of the four d=3 comparison points (package prescription:
a/eps^2 resummed with [3/1] and [1/3]; Delta_E through C_6 with [4/2]); inputs are this note's values.
Usage: python3 check_bp3.py OUT.json [PACKAGE_RESULTS_BOOTSTRAP_DIR]
With the package's results/bootstrap directory, the d=3 rows are compared with its historical and current runs
(relative tolerance 1e-9); the script exits 1 on a mismatch."""
import json, sys
import mpmath as mp
mp.mp.dps = 30
a = [mp.mpf(x) for x in ('-0.0254241874995485926812761737327', '-0.0667823808153468617422274311271',
                         '-0.0279145897482121975830173204363', '-0.15663777757113552989085130427',
                         '0.507382663942980837786722411903')]
C = {'historical': ['1.5', '-1/6', '0.181221785406', '-0.353581520433', '1.228063545', '-5.850351421', '33.57'],
     'current': ['1.5', '-1/6', '0.181221785406', '-0.353581520433', '1.228063545', '-5.850351421', '33.5754']}
def frac(s):
    return mp.mpf(s.split('/')[0]) / mp.mpf(s.split('/')[1]) if '/' in s else mp.mpf(s)
def borel_pade(c, L, M, eps):
    b = [ck / mp.factorial(k) for k, ck in enumerate(c)]
    p, q = mp.pade(b, L, M)
    roots = mp.polyroots(q[::-1], maxsteps=200, extraprec=60) if M > 0 else []
    pos = [r for r in roots if abs(mp.im(r)) < 1e-20 and mp.re(r) > 0]
    f = lambda t: mp.polyval(p[::-1], eps * t) / mp.polyval(q[::-1], eps * t)
    return mp.quad(lambda t: mp.exp(-t) * f(t), [0, 1, 10, mp.inf]), [mp.nstr(r, 8) for r in roots], bool(pos)
out = []
for dphi in ('0.70363', '0.65726', '0.61089', '0.56452'):
    eps = 3 - 4 * mp.mpf(dphi)
    row = {'Delta_phi': dphi, 'epsilon': mp.nstr(eps, 6)}
    for L, M in ((3, 1), (1, 3), (2, 2)):
        v, roots, pos = borel_pade(a, L, M, eps)
        row[f'a_BP{L}{M}'] = mp.nstr(eps**2 * v, 12); row[f'a_BP{L}{M}_positive_pole'] = pos
    row['a_truncated'] = [mp.nstr(sum(a[j] * eps**(j + 2) for j in range(n + 1)), 12) for n in range(5)]
    for ver, cs in C.items():
        v, roots, pos = borel_pade([frac(x) for x in cs], 4, 2, eps)
        row[f'Delta_BP42_{ver}'] = mp.nstr(v, 12); row[f'Delta_BP42_{ver}_positive_pole'] = pos
    print(row, flush=True); out.append(row)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
if len(sys.argv) > 2:
    import os
    bad = 0
    for ver in ('historical', 'current'):
        rows = [r for r in json.load(open(os.path.join(sys.argv[2], ver, 'comparison_results.json')))['rows'] if r['d'] == 3]
        for mine, theirs in zip(out, rows):
            pairs = [('a_BP31', 'a_BP31'), ('a_BP13', 'a_BP13'), (f'Delta_BP42_{ver}', 'thermal_BP42')]
            for k1, k2 in pairs:
                x, y = mp.mpf(mine[k1]), mp.mpf(theirs[k2])
                if abs(x - y) > mp.mpf('1e-9') * abs(y):
                    print('MISMATCH', ver, mine['Delta_phi'], k1, x, y); bad += 1
    print('PASS' if not bad else f'{bad} mismatches')
    sys.exit(1 if bad else 0)
