#!/usr/bin/env python3
"""Tail check: per-graph data for choosing the fresh nested-N sample (read-only).

  tc_select_data.py --package PKG --run PROD --out OUT.csv

For every L7/L8 graph-campaign of the production batch (tools/design.load_pilot, as pr_followup.py): points per
replicate, the C8-projected replicate variance contribution v = 0.25 Var_rep(y) / r and its share of Var(C8_full),
the replicate excess kurtosis, the Hill xi-hat (design.tail_table) and the measured seconds per point
(graph_costs.csv: row_seconds / points)."""
import argparse, csv, math, sys
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--package', type=Path, required=True)
ap.add_argument('--run', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.package / 'tools'))
import design
P = design.load_pilot(a.run)
rows, flags = design.tail_table(P)
tp = {(x['campaign'], x['sector'], x['L'], x['graph']): x for x in rows}
var_total = 0.
recs = []
for (c, s, L), G in P.groups.items():
    y = np.einsum('rgj,j->rg', G.Y, P.J8[L])
    var_total += 0.25 * float(np.var(y.sum(1), ddof=1)) / G.reps
    if L < 7:
        continue
    cost = {}
    with open(a.run / 'groups' / f'{c}_{s}_L{L}' / 'graph_costs.csv') as f:
        for r in csv.DictReader(f):
            cost[int(r['graph'])] = float(r['row_seconds']) / int(r['points'])
    for i, g in enumerate(G.graphs):
        yi = y[:, i]; sd = np.std(yi, ddof=1)
        k = float(np.mean(((yi - yi.mean()) / sd) ** 4) - 3) if sd > 0 else float('nan')
        t = tp.get((c, s, L, g), {})
        recs.append(dict(campaign=c, sector=s, L=L, graph=g, points=G.points[g], reps=G.reps, v=0.25 * float(np.var(yi, ddof=1)) / G.reps,
                         kurtosis=k, xi_hat=t.get('xi_hat'), largest_share=t.get('largest_share'), sec_per_point=cost.get(g)))
with a.out.open('w') as f:
    w = csv.DictWriter(f, fieldnames=list(recs[0]) + ['share'])
    w.writeheader()
    for r in recs:
        r['share'] = r['v'] / var_total
        w.writerow(r)
print(f'{len(recs)} graph-campaigns; Var(C8) {var_total:.4f}')
