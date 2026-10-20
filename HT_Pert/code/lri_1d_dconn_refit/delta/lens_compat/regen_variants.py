#!/usr/bin/env python3
"""Regenerate every kept delta-v1 fit as a curve on ALL even L = 2..118 (the published delta_v1_variants.json holds them
only at the modelled L >= 46), using the previous stage's own code (delta/code: load.load_s10, ensemble.ensemble, RULE)
read-only. Checks that the regenerated kept set and predictions at L >= 46 reproduce the published file, then reports the
misfit of each kept curve at the exact cutoffs, i.e. the size of the step ('seam') that the published prescription
(exact dC at L <= 44, modelled beyond) puts between L = 44 and 46.

Output: out/variants_full.json  {dCk: {L, labels, maxres, pred (all L), exact (L<=hi_exact)}}
Usage: regen_variants.py [--extra-dconn CSV] [--published delta_v1_variants.json] [--out PATH]"""
import sys, os, json, argparse
sys.dont_write_bytecode = True
DELTA_CODE = '<TMP>/scratchpad/dconn_refit72/delta/code'
sys.path.insert(0, DELTA_CODE)
import numpy as np
from load import load_s10
from ensemble import ensemble, RULE

ap = argparse.ArgumentParser()
ap.add_argument('--extra-dconn', default=None)
ap.add_argument('--published', default=os.path.join(DELTA_CODE, '..', 'out', 'delta_v1_variants.json'))
ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'variants_full.json'))
a = ap.parse_args()
s10 = load_s10(a.extra_dconn)
pub = json.load(open(a.published))
Lall = list(range(2, 119, 2))
out = {}
for k in (6, 7, 8):
    seq = {L: ent[k] for L, ent in s10.items() if k in ent}
    hi = max(seq)
    e = ensemble(seq, hi, Lall, rule=RULE)
    labels = ['%s|lo=%d|s=%d|np=%d' % (m, lo, s, n) for (m, lo, s, n, _) in e['kept']]
    P = e['preds']
    p = pub['dC%d' % k]
    assert labels == p['labels'], ('kept set differs', k)
    Lp = p['L']; ip = [Lall.index(L) for L in Lp]
    dev = np.abs(P[:, ip] - np.array(p['pred'])).max()
    ex = np.array([seq[L] for L in Lall if L <= hi])
    mis = P[:, :len(ex)] - ex[None, :]
    i44 = Lall.index(hi)
    # seam diagnostics: misfit at the last exact point and rms over the last 5 exact points
    print(f'dC{k}: kept {len(labels)}, max |regen - published| at L>={Lp[0]}: {dev:.1e}; misfit at L={hi}: '
          f'mean-curve {P.mean(0)[i44] - seq[hi]:+.2e}, median-curve {np.median(P, 0)[i44] - seq[hi]:+.2e}, '
          f'per-fit |.| median {np.median(np.abs(mis[:, i44])):.1e} max {np.abs(mis[:, i44]).max():.1e}; '
          f'maxres min/median/max {min(p["maxres"]):.1e}/{np.median(p["maxres"]):.1e}/{max(p["maxres"]):.1e}')
    out['dC%d' % k] = dict(L=Lall, hi_exact=hi, labels=labels, maxres=p['maxres'], pred=P.tolist(),
                           exact={str(L): seq[L] for L in seq})
json.dump(out, open(a.out, 'w'))
print('wrote', a.out)
