#!/usr/bin/env python3
"""Where does the production's campaign a/b difference (C8: a 1604.68, b 1600.53, pull +2.18) come from?

Campaigns a and b integrate the same graphs with importance rates 0.8 and 0.7. This recomputes the per-campaign C8
from the merged replicate batches (tools/assemble.py combine, the package's own assembly) and splits a - b, linearized
with the order-8 row of the Jacobian at the total means, over sectors and loops. Within the L8 groups it splits it over
graphs (graph_replicates.csv), by the production tail index (prod_tails.csv, when given) and by graph size.

  ab_split.py RESULTS_DIR [PROD_TAILS.csv] > report.txt      (run from the package root; numpy needed)
"""
import csv, json, math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, 'tools')
import assemble  # noqa: E402

R = Path(sys.argv[1])
tails = sys.argv[2] if len(sys.argv) > 2 else None
loops = range(3, 9)
ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
for p in sorted((R / 'groups').glob('*/merged.json')):
    d = json.loads(p.read_text())
    ar[d['sector']][d['campaign']][int(d['L'])] = np.asarray(d['batches'], float)
B2, _ = assemble.two_loop(8)
r = assemble.combine(ar, 8, assemble.HALF_D, 0, B2)
ref = json.loads((R / 'C8_result.json').read_text())
print(f"recomputed C8 {r['C8_full']:.10f} (stored {ref['C8_full']:.10f}); a {r['campaigns']['a']['C8']:.6f} b {r['campaigns']['b']['C8']:.6f}")
oa = assemble.vendored()
J = oa.jacobians({L: np.asarray(r['means']['free'][str(L)]) + np.asarray(r['means']['power'][str(L)]) for L in loops}, B2, 8, assemble.HALF_D)
j8 = {L: np.asarray(J[L])[8] for L in loops}
tot, tv = 0.0, 0.0
print('\nlinearized a - b by sector and loop (C8 units; se from the replicate variances):')
for s in ('free', 'power'):
    for L in loops:
        ya, yb = ar[s]['a'][L] @ j8[L], ar[s]['b'][L] @ j8[L]
        d = ya.mean() - yb.mean(); v = ya.var(ddof=1) / len(ya) + yb.var(ddof=1) / len(yb)
        tot += d; tv += v
        print(f'  {s:5s} L{L}: {d:+9.4f} +- {math.sqrt(v):7.4f}  (pull {d/math.sqrt(v) if v > 0 else 0:+.2f})')
print(f'  total linearized: {tot:+.4f} +- {math.sqrt(tv):.4f} (exact a - b {r["campaigns"]["a"]["C8"] - r["campaigns"]["b"]["C8"]:+.4f})')

xi = {}
if tails:
    for row in csv.DictReader(open(tails)):
        if row['xi']:
            xi[(row['campaign'], row['sector'], int(row['graph']))] = float(row['xi'])
print('\nL8 a - b over graphs (per-graph replicate means of j8 . jets; the batches are checked to be the graph sums):')
for s in ('free', 'power'):
    per = {}
    for t in 'ab':
        rows = {}
        with open(R / 'groups' / f'{t}_{s}_L8' / 'graph_replicates.csv') as f:
            for row in csv.DictReader(f):
                k = int(row['graph']); rep = int(row['replicate'])
                rows.setdefault(k, {})[rep] = float(np.dot(j8[8], [float(row['jet_0']), float(row['jet_1'])]))
        reps = ar[s][t][8].shape[0]
        y = np.array([[rows[g].get(i, 0.0) for i in range(reps)] for g in sorted(rows)])
        batch = ar[s][t][8] @ j8[8]
        print(f'  {t}_{s}_L8: {len(rows)} graphs; max |sum over graphs - batch| / max|batch| = {np.max(np.abs(y.sum(0) - batch)) / np.max(np.abs(batch)):.2e}')
        for gi, g in enumerate(sorted(rows)):
            per.setdefault(g, {})[t] = (y[gi].mean(), y[gi].var(ddof=1) / reps)
    gs = [g for g in per if 'a' in per[g] and 'b' in per[g]]
    d = {g: per[g]['a'][0] - per[g]['b'][0] for g in gs}; v = {g: per[g]['a'][1] + per[g]['b'][1] for g in gs}
    D, V = sum(d.values()), sum(v.values())
    print(f'  {s}: sum over {len(gs)} graphs {D:+.4f} +- {math.sqrt(V):.4f}')
    top = sorted(gs, key=lambda g: -abs(d[g]))[:10]
    print('    largest |a - b| graphs: ' + '; '.join(f'{g}: {d[g]:+.3f} +- {math.sqrt(v[g]):.3f}' + (f' xi {(xi.get(("a", s, g), float("nan")) + xi.get(("b", s, g), float("nan"))) / 2:.2f}' if xi else '') for g in top))
    # concentration: share of the total a - b carried by the k largest |d| graphs, and the chi-square of the per-graph pulls
    chi2 = sum(d[g] ** 2 / v[g] for g in gs if v[g] > 0); nz = sum(1 for g in gs if v[g] > 0)
    print(f'    per-graph pulls: chi2 {chi2:.1f} over {nz} graphs (ratio {chi2/nz:.3f}); top-10 sum {sum(d[g] for g in top):+.4f}, top-100 sum {sum(d[g] for g in sorted(gs, key=lambda g: -abs(d[g]))[:100]):+.4f}')
    if xi:
        bins = [(-9, 0.3), (0.3, 0.44), (0.44, 0.6), (0.6, 0.8), (0.8, 99)]
        for lo, hi in bins:
            sel = [g for g in gs if (('a', s, g) in xi and ('b', s, g) in xi and lo < (xi[('a', s, g)] + xi[('b', s, g)]) / 2 <= hi)]
            if sel:
                Ds, Vs = sum(d[g] for g in sel), sum(v[g] for g in sel)
                print(f'    xi_mean in ({lo}, {hi}]: {len(sel):5d} graphs, a - b {Ds:+8.4f} +- {math.sqrt(Vs):.4f} (pull {Ds/math.sqrt(Vs) if Vs > 0 else 0:+.2f})')
