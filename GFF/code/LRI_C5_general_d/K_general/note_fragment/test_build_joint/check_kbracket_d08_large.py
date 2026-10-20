#!/usr/bin/env python3
"""Companion of check_kbracket_d08.py: literal gs:Kseries bracket vs gc:Kcancelled at large indices (as sampled by
the Abel-Plana tails of refcheck/routeB_residue.py, through its g_at, i.e. with its own working precision), d=0.8
and, for comparison, d=1.25."""
import os, sys
import mpmath as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'refcheck')))
sys.argv = ['x']
import routeB_residue as B
for d in ('0.8', '1.25'):
    B.init(d, 40)
    print('d =', d)
    for l, n in ((10 ** 3, 0), (10 ** 6, 0), (10 ** 10, 0), (10 ** 20, 0), (0, 10 ** 3), (0, 10 ** 6), (0, 10 ** 10),
                 (10 ** 6, 10 ** 6), (mp.mpc(10 ** 6, 10), 0)):
        v = B.g_at(mp.mpf(l) if not isinstance(l, mp.mpc) else l, mp.mpf(n))
        print('  l=%-12s n=%-8s literal=%s cancelled=%s rel.diff=%s' % (mp.nstr(l, 3), mp.nstr(n, 3), mp.nstr(v[4], 8),
              mp.nstr(v[5], 8), mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))
