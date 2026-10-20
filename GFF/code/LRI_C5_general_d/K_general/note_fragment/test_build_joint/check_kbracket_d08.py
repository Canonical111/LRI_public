#!/usr/bin/env python3
"""Joint-review fix K6 ('A caution'): at d=0.8, compare the literal gs:Kseries bracket with the cancelled form
gc:Kcancelled term by term, using the unchanged summand of K_general/refcheck/routeB_residue.py, at integer (l, n)
and at non-integer or complex n (where only the analytic continuations used by the Abel-Plana tails enter)."""
import os, sys
import mpmath as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'refcheck')))
sys.argv = ['x']
import routeB_residue as B
B.init('0.8', 40)
print('integer (l, n): relative difference literal - cancelled')
for l in (0, 1, 2, 7, 30):
    for n in (0, 1, 5, 40):
        v = B.summand(mp.mpf(l), mp.mpf(n))
        print('  l=%2d n=%2d  %s' % (l, n, mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))
print('non-integer / complex n (continuations used by the n-tail):')
for l in (0, 2):
    for n in (mp.mpf('5.5'), mp.mpc(20, 1), mp.mpc(20, 3), mp.mpc(20, 6)):
        v = B.summand(mp.mpf(l), n)
        print('  l=%d n=%s  |literal|=%s |cancelled|=%s rel.diff=%s' % (l, mp.nstr(n, 4), mp.nstr(abs(v[4]), 3),
              mp.nstr(abs(v[5]), 3), mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))
print('non-integer / complex l at fixed integer n (continuations used by the spin tail):')
for n in (0, 3):
    for l in (mp.mpf('10.5'), mp.mpc(30, 1), mp.mpc(30, 3), mp.mpc(30, 6)):
        v = B.summand(l, mp.mpf(n))
        print('  n=%d l=%s  |literal|=%s |cancelled|=%s rel.diff=%s' % (n, mp.nstr(l, 4), mp.nstr(abs(v[4]), 3),
              mp.nstr(abs(v[5]), 3), mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))
