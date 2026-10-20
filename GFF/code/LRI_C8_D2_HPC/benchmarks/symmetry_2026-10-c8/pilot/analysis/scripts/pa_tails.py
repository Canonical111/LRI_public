#!/usr/bin/env python3
"""Heavy-tail context for the user's decision (docs/DESIGN.md, "After the pilot", step 2): how much of the design
weight the screened L8 graphs carry, and whether the frozen bundles give them the 32,768 points per replicate that the
confirmation needs.

  pa_tails.py --package PKG --run PILOT --tails TAILS.csv --bundles DIR [DIR ...] --out OUT.json

Reads only. Per (sector, L) and campaign, from design.graph_table (sigma_g^2 = n_g Var_rep(J8 . jet), c_g the pilot's
seconds per point) and the report's --tails-out rows (xi_hat, largest share per graph and campaign):
- L8 graph-campaigns screened by C63d's rule (xi_hat > 0.38 or largest share > 0.05; the report lists a graph when either
  campaign is screened), their share of sum_g sigma_g sqrt(c_g) (the Neyman weight, i.e. of the design's cost and
  variance at the optimum), of sum_g sigma_g^2 and of sum_g c_g;
- the xi_hat quantiles, and the Spearman rank correlation of xi_hat with sigma_g (do heavy-tailed graphs carry larger
  per-graph standard deviations?) and with the largest share;
- the same summary at L <= 7 (diagnostic, no threshold);
- per bundle: the L8 graph-campaigns at >= 32,768 points per replicate (count x s; the confirmation threshold), and how
  many of the screened graphs reach it in both campaigns."""
from __future__ import annotations
import argparse, csv, json, math, sys
from pathlib import Path
import numpy as np


def rank(v):
    o = np.argsort(v, kind='stable'); r = np.empty(len(v)); r[o] = np.arange(len(v)); return r


def spearman(x, y):
    if len(x) < 3: return None
    return float(np.corrcoef(rank(np.asarray(x)), rank(np.asarray(y)))[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, required=True); ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--tails', type=Path, required=True); ap.add_argument('--bundles', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    sys.path.insert(0, str(a.package / 'tools')); import design
    P = design.load_pilot(a.run.resolve()); T = design.graph_table(P)
    tails = {}
    for r in csv.DictReader(a.tails.open()):
        tails[(r['campaign'], r['sector'], int(r['L']), int(r['graph']))] = (float(r['xi_hat']), float(r['largest_share']))
    screened_graph = {}  # (sector, L, graph) -> screened in either campaign (the report's rule, L8 only)
    for (c, s, L, g), (xi, sh) in tails.items():
        if L == 8: screened_graph[(s, L, g)] = screened_graph.get((s, L, g), False) or xi > design.XI_SCREEN or sh > design.SMAX_SCREEN
    out = {'schema': 'c8-d2-pilot-tails-1', 'rule': __doc__, 'strata': {}, 'bundles': {}}
    for s in design.SECTORS:
        for L in design.LOOPS:
            xs, sig, sh, w, w_scr, u, u_scr, cc, cc_scr, n, n_scr = [], [], [], 0., 0., 0., 0., 0., 0., 0, 0
            for c in design.CAMPAIGNS:
                for g, x in T[(c, s, L)].items():
                    xi, share = tails[(c, s, L, g)]; xs.append(xi); sig.append(x['sigma']); sh.append(share)
                    wg = x['sigma'] * math.sqrt(x['cost']); w += wg; u += x['sigma'] ** 2; cc += x['cost']; n += 1
                    if L == 8 and screened_graph[(s, L, g)]: w_scr += wg; u_scr += x['sigma'] ** 2; cc_scr += x['cost']; n_scr += 1
            q = np.quantile(xs, [.1, .5, .9]).tolist()
            out['strata'][f'{s}_L{L}'] = dict(graph_campaigns=n, xi_q10=q[0], xi_median=q[1], xi_q90=q[2], xi_max=max(xs),
                                              frac_xi_gt_0_38=float(np.mean(np.asarray(xs) > .38)), frac_xi_ge_0_5=float(np.mean(np.asarray(xs) >= .5)),
                                              spearman_xi_sigma=spearman(xs, sig), spearman_xi_share=spearman(xs, sh),
                                              screened_graph_campaigns=n_scr if L == 8 else None,
                                              screened_share_neyman_weight=w_scr / w if L == 8 and w else None,
                                              screened_share_sigma2=u_scr / u if L == 8 and u else None,
                                              screened_share_cost=cc_scr / cc if L == 8 and cc else None)
            print(f'{s}_L{L}', json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out['strata'][f'{s}_L{L}'].items()}))
    prim = {(s, L): {r['id']: bool(r.get('primitive')) for r in P.inventory[s][str(L)]} for s in design.SECTORS for L in design.LOOPS}
    for B in a.bundles:
        B = B.resolve(); d = json.loads((B / 'design.json').read_bytes()); sv = {k: v['s'] for k, v in d['strata'].items()}
        rec = {}
        for s in design.SECTORS:
            pts = {}
            for c in design.CAMPAIGNS:
                for line in (B / 'counts' / f'{c}_{s}_L8.txt').read_text().splitlines():
                    g, n = line.split(); g = int(g); pts[(c, g)] = int(n) * sv[design.stratum_of(s, 8, prim[(s, 8)].get(g, False))]
            ge = [k for k, v in pts.items() if v >= design.CONFIRM_POINTS]
            scr = [g for (ss, L, g), f in screened_graph.items() if ss == s and f]
            both = [g for g in scr if pts[('a', g)] >= design.CONFIRM_POINTS and pts[('b', g)] >= design.CONFIRM_POINTS]
            rec[s] = dict(graph_campaigns=len(pts), at_confirm_points=len(ge), screened_graphs=len(scr), screened_at_confirm_points_both_campaigns=len(both),
                          points_per_replicate_quantiles=dict(zip(('min', 'median', 'max'), np.quantile(list(pts.values()), [0, .5, 1]).tolist())))
        out['bundles'][B.name] = rec; print(B.name, json.dumps(rec))
    a.out.write_text(json.dumps(out, indent=1) + '\n'); return 0


if __name__ == '__main__':
    sys.exit(main())
