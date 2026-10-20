#!/usr/bin/env python3
"""Tail check part B: per-class nested-N summaries with the power L8 graphs split by the certificate's double-lift
flag (a clamped subset needing two orders of cancellation, raw valuation <= -2), and the ratio of each graph's
per-point variance at 2^17 to that at its production point count (the production's own N), weighted by its
production share of Var(C8).

  tc_nested_split.py NESTED.json CERT.jsonl.gz SELECT_DATA.csv.gz OUT.json"""
import csv, gzip, json, math, sys
import numpy as np

nest = json.load(open(sys.argv[1]))
cert = {(r['sector'], r['id']): r for r in map(json.loads, gzip.open(sys.argv[2], 'rt')) if r['L'] == 8}
sel = {}
for r in csv.DictReader(gzip.open(sys.argv[3], 'rt')):
    if r['L'] == '8':
        sel[(r['campaign'], r['sector'], int(r['graph']))] = r


def group(p):
    k = p['klass']
    if k.startswith('control'):
        return 'controls (cleared, never screened, primitives)'
    if p['sector'] == 'power':
        dl = cert[('power', p['graph'])]['max_orders_cancelled'] >= 2
        return f"{k}, {'double-lift' if dl else 'no double-lift'}"
    return k


out = {}
G = {}
for key, p in nest['per_graph'].items():
    G.setdefault(group(p), []).append(p)
for name, P in sorted(G.items()):
    s = np.array([p['slope_sigma2'] for p in P]); q = np.array([p['slope_q16'] for p in P])
    se = s.std(ddof=1) / math.sqrt(len(s)); seq = q.std(ddof=1) / math.sqrt(len(q))
    lv = sorted(set.intersection(*[set(p['levels']) for p in P]))
    rel = [float(np.exp(np.mean([math.log(p['sigma2'][p['levels'].index(N)] / p['sigma2'][p['levels'].index(lv[0])]) for p in P]))) for N in lv]
    hill = [float(np.median([p['hill16'][p['levels'].index(N)] for p in P])) for N in lv]
    share = [float(np.median([p['share'][p['levels'].index(N)] for p in P])) for N in lv]
    hexp = float(np.polyfit(np.log(lv), np.log(hill), 1)[0])
    F = []; W = []
    for p in P:
        r = sel[(p['campaign'], p['sector'], p['graph'])]; n = int(r['points'])
        if n in p['levels'] and 131072 in p['levels']:
            F.append(p['sigma2'][p['levels'].index(131072)] / p['sigma2'][p['levels'].index(n)]); W.append(float(r['share']))
    F = np.array(F); W = np.array(W)
    out[name] = dict(graph_campaigns=len(P), graphs=len({p['graph'] for p in P}),
                     slope_sigma2=dict(mean=float(s.mean()), ci95=[float(s.mean() - 1.96 * se), float(s.mean() + 1.96 * se)], min=float(s.min()), max=float(s.max())),
                     slope_q16=dict(mean=float(q.mean()), ci95=[float(q.mean() - 1.96 * seq), float(q.mean() + 1.96 * seq)]),
                     levels=lv, sigma2_rel_geomean=rel, hill16_median=hill, hill_exponent=hexp, share_median=share,
                     variance_ratio_2p17_over_production_N=dict(n=int(len(F)), share_weighted=float((W * F).sum() / W.sum()) if len(F) else None,
                                                                geomean=float(np.exp(np.mean(np.log(F)))) if len(F) else None,
                                                                mean=float(F.mean()) if len(F) else None, max=float(F.max()) if len(F) else None),
                     production_share_of_var_C8=float(sum(float(sel[(p['campaign'], p['sector'], p['graph'])]['share']) for p in P)))
json.dump(out, open(sys.argv[4], 'w'), indent=1)
for k, v in out.items():
    print(f"{k:48s} n={v['graph_campaigns']:2d} slope {v['slope_sigma2']['mean']:+.3f} [{v['slope_sigma2']['ci95'][0]:+.3f},{v['slope_sigma2']['ci95'][1]:+.3f}] "
          f"q16 {v['slope_q16']['mean']:+.3f}  hill {v['hill16_median'][0]:.2f}->{v['hill16_median'][-1]:.2f} (N^{v['hill_exponent']:+.2f})  "
          f"share {v['share_median'][0]:.3f}->{v['share_median'][-1]:.4f}  F {v['variance_ratio_2p17_over_production_N']}")
