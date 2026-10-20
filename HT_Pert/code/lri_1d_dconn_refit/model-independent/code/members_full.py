#!/usr/bin/env python3
"""Re-evaluate every kept delta-model fit (rule delta-v1, the delta stage's own ensemble code, imported read-only) at
ALL even L (2..118), so that member deviations can be propagated either
  'seam'   : dC_k = exact (L <= hi_exact) + member (modelled L)      [what the variants file implies], or
  'smooth' : dC_k = central + (member - medoid) at every L            [smooth perturbation; no seam kink].
Checks that the reproduced kept list and predictions match the variants file.
usage: members_full.py OUT.json [DELTA_CODE_DIR]
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import load_corrected, load_variants
import numpy as np
DELTA_CODE = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(os.path.join(HERE, '..', '..', 'delta', 'code'))
sys.path.insert(0, DELTA_CODE)
from ensemble import ensemble, RULE

os.environ['DCONN_CENTRAL'] = 'median'
D = load_corrected()
V = load_variants()
out = {}
for k in (6, 7, 8):
    exact = {L: D['dC'][k][L] for L in D['dC'][k] if D['exact'][k][L]}
    hi = max(exact)
    Lall = sorted(D['dC'][k])
    Lfull = sorted(set(Lall) | set(V[k]['L']))
    e = ensemble(exact, hi, Lfull, rule=RULE)
    labels = ['%s|lo=%d|s=%d|np=%d' % (m, lo, s, n) for (m, lo, s, n, _) in e['kept']]
    assert labels == V[k]['labels'], 'kept list differs from the variants file'
    P = np.array(e['preds'])
    idx = [Lfull.index(L) for L in V[k]['L']]
    dev = float(np.max(np.abs(P[:, idx] - V[k]['pred'])))
    res_ex = np.array([[P[i, Lfull.index(L)] - exact[L] for L in sorted(exact)] for i in range(len(P))])
    out[k] = dict(L=Lfull, labels=labels, pred=P.tolist(), hi_exact=hi, check_maxdev_vs_variants=dev,
                  seam_residual_at_hi=[float(r[-1]) for r in res_ex],
                  maxres_exact_window=[float(np.max(np.abs(r[[i for i, L in enumerate(sorted(exact)) if L >= 10]]))) for r in res_ex])
    print('k', k, 'members', len(P), 'max |pred - variants file| %.1e' % dev, 'seam residual at L=%d: median %.1e max %.1e' % (
        hi, np.median(np.abs(out[k]['seam_residual_at_hi'])), np.max(np.abs(out[k]['seam_residual_at_hi']))), flush=True)
json.dump(out, open(sys.argv[1], 'w'))
