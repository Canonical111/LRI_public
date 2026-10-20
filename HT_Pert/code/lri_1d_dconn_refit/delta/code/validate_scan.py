"""Validation scan: train on L<=44 (lo..44), predict beyond, for sequences whose large-L values are known exactly.
V1: complete Dconn dC4, dC5 (exact to 152).   V2: isolated g2D shifts k=4..8 (exact to 90/92/118).
V3: remainders R_k = Dconn - g2D for k=4,5 (exact to 118)."""
import sys, json, time
sys.path.insert(0, '<TMP>/scratchpad/dconn_fit/delta/code')
from load import *
from fitlib import *

t0 = time.time()
rc = load_recon(); g = load_g2d()
seqs = {}
seqs['Dconn4'] = {L: rc[L][4] for L in rc}
seqs['Dconn5'] = {L: rc[L][5] for L in rc}
for k in range(4, 9):
    seqs['g2D%d' % k] = dict(g[k])
for k in (4, 5):
    seqs['R%d' % k] = {L: rc[L][k] - g[k][L] for L in rc if L in g[k]}

HI = 44
TEST = [60, 92, 118, 152]
results = []
models = all_models()
for name, s in seqs.items():
    Ltr_all = sorted(L for L in s if L <= HI)
    tests = [L for L in TEST if L in s]
    for lo in (8, 12, 16):
        Ltr = [L for L in Ltr_all if L >= lo]
        if name == 'g2D8':
            Ltr = [L for L in Ltr if L % 4 == 0]
        for mname, terms in models:
            if len(terms) > len(Ltr) - 2:
                continue
            f = fit(Ltr, [s[L] for L in Ltr], terms)
            preds = {L: f['predict'](L) for L in tests}
            results.append(dict(seq=name, lo=lo, model=mname, npar=len(terms), n=len(Ltr), maxres=f['maxres'],
                                cond=f['cond'], err={L: preds[L] - s[L] for L in tests},
                                change={L: s[L] - s[HI] for L in tests}))
json.dump(results, open('../out/validate_scan.json', 'w'), indent=0)
print('fits', len(results), 'time', time.time() - t0)
