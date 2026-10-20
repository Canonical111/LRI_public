#!/usr/bin/env python3
"""Write the run list for run_list.sbatch: the medoid-central run plus, per order k = 6, 7, 8, reruns with the delta-model
member at the 0/10/25/75/90/100 % quantiles of dC_k at the largest modelled L (nonlinear check, full reselection).
usage: make_runlist.py OUT.txt   (honours DCONN_CORRECTED / DCONN_VARIANTS)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DCONN_CENTRAL'] = 'median'
from common import *
D = load_corrected(); V = load_variants()
lines = ['run2_medoid medoid']
for k in (6, 7, 8):
    Lm = [L for L in V[k]['L'] if L in D['dC'][k] and not D['exact'][k][L]]
    if not Lm:
        continue
    i = V[k]['L'].index(max(Lm)); order = np.argsort(V[k]['pred'][:, i]); nv = len(order)
    for q in (0.0, 0.1, 0.25, 0.75, 0.9, 1.0):
        lines.append('run2_k%d_q%02d k%d:%d' % (k, int(q * 100), k, int(order[min(int(round(q * (nv - 1))), nv - 1)])))
open(sys.argv[1], 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
