#!/usr/bin/env python3
"""refit72 version of make_runlist.py (the archived file is unchanged next to it).

Differences: (1) the primary central is an explicit member set BASE (default: the delta stage's floor-level medoid
k6:53,k7:74,k8:79), because the lens's own 'medoid' rule now picks poorly fitting dC7/dC8 members (seam ~10x the noise);
(2) every quantile rerun pins the OTHER orders to BASE (the archived list left them on the 'medoid' rule, which would
now mix in the poor members); (3) two files are written: OUT_main (primary + comparison runs) and OUT_q (quantile reruns).
Line format for run_list72.sbatch: TAG CENTRAL [CORR|-] [VARS|-] [RAWC07|-]
usage: make_runlist72.py OUT_main.txt OUT_q.txt   (honours DCONN_CORRECTED / DCONN_VARIANTS / MI_BASE_CENTRAL)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DCONN_CENTRAL'] = 'median'
from common import *
BASE = os.environ.get('MI_BASE_CENTRAL', 'k6:53,k7:74,k8:79')
base = {int(p.split(':')[0][1:]): int(p.split(':')[1]) for p in BASE.split(',')}
D = load_corrected(); V = load_variants()


def spec(over):
    m = dict(base); m.update(over)
    return ','.join('k%d:%d' % (k, m[k]) for k in sorted(m))


main = ['run2_fmedoid %s' % spec({})]
q = []
for k in (6, 7, 8):
    Lm = [L for L in V[k]['L'] if L in D['dC'][k] and not D['exact'][k][L]]
    if not Lm:
        continue
    i = V[k]['L'].index(max(Lm)); order = np.argsort(V[k]['pred'][:, i]); nv = len(order)
    for qq in (0.0, 0.1, 0.25, 0.75, 0.9, 1.0):
        q.append('run2_k%d_q%02d %s' % (k, int(qq * 100), spec({k: int(order[min(int(round(qq * (nv - 1))), nv - 1)])})))
open(sys.argv[1], 'w').write('\n'.join(main) + '\n')
open(sys.argv[2], 'w').write('\n'.join(q) + '\n')
print('\n'.join(main + q))
