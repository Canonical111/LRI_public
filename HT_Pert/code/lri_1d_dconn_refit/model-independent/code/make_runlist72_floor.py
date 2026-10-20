#!/usr/bin/env python3
"""refit72: nonlinear reruns restricted to FLOOR-LEVEL delta-model members (maxres <= QF=3 x best of the same training
window): per order k the floor members at the min / median / max of dC_k at the largest modelled L, other orders pinned
to the base (floor-level medoid). usage: make_runlist72_floor.py OUT.txt"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DCONN_CENTRAL'] = 'median'
from common import *
base = {6: 53, 7: 74, 8: 79}
D = load_corrected(); V = load_variants(); lines = []
for k in (6, 7, 8):
    mr = V[k]['maxres']; lo = np.array([int(s.split('lo=')[1].split('|')[0]) for s in V[k]['labels']])
    best = {l: mr[lo == l].min() for l in set(lo)}
    fl = np.where([mr[i] <= 3 * best[lo[i]] for i in range(len(mr))])[0]
    Lm = [L for L in V[k]['L'] if L in D['dC'][k] and not D['exact'][k][L]]
    i = V[k]['L'].index(max(Lm)); vals = V[k]['pred'][fl, i]; order = fl[np.argsort(vals)]
    for q, j in (('fmin', order[0]), ('fmed', order[len(order) // 2]), ('fmax', order[-1])):
        m = dict(base); m[k] = int(j)
        lines.append('run2_k%d_%s %s' % (k, q, ','.join('k%d:%d' % (kk, m[kk]) for kk in (6, 7, 8))))
open(sys.argv[1], 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
