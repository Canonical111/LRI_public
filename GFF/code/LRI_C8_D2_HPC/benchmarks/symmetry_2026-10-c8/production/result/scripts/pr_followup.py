#!/usr/bin/env python3
"""Follow-up diagnostics of the C8(2) production batch (2026-10-07), after pr_result_analysis.py found a pooled
replicate-level excess kurtosis of 4.59 in power L8 (Gaussian reference at 128 replicates: -0.09).

  pr_followup.py --package PKG --run PROD --out OUT.json

Reads only (tools/design.load_pilot: every merged table verified through merged.json). Per L8 stratum and tail class
(the production tail rule, tools/design.tail_table: confirmed, cleared at >= 32,768 points per replicate, below the
confirmation points, never screened in production): the pooled excess kurtosis of the standardized replicate values,
the per-graph-campaign excess kurtosis quantiles, and the pooled kurtosis after leaving out the k graph-campaigns of
largest kurtosis (k = 1, 5, 20). The largest single graph-campaign contributions to Var(C8_full) (0.25 Var_rep(y)/r)
overall and per stratum, with their kurtosis, points, tail statistics and largest |z|. And the variance share of the
graph-campaigns whose own excess kurtosis exceeds 3 and 10."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np


def kurt(y):
    sd = np.std(y, ddof=1)
    return None if sd <= 0 else float(np.mean(((y - y.mean()) / sd) ** 4) - 3.)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.package / 'tools'))
    import design
    t0 = time.time()
    P = design.load_pilot(a.run)
    rows, flags = design.tail_table(P)
    tp = {(x['campaign'], x['sector'], x['L'], x['graph']): x for x in rows}
    conf = {(x['sector'], x['L'], x['graph']) for x in flags['confirmed']}
    scr = {(x['sector'], x['L'], x['graph']) for x in flags['screened']}
    G8 = {}
    var_total = 0.
    for (c, s, L), G in P.groups.items():
        y = np.einsum('rgj,j->rg', G.Y, P.J8[L])
        var_total += 0.25 * float(np.var(y.sum(1), ddof=1)) / G.reps
        for i, g in enumerate(G.graphs):
            v = 0.25 * float(np.var(y[:, i], ddof=1)) / G.reps
            sd = np.std(y[:, i], ddof=1)
            G8[(c, s, L, g)] = dict(y=y[:, i], v=v, n=G.points[g], kurt=kurt(y[:, i]),
                                    max_abs_z=float(np.max(np.abs((y[:, i] - y[:, i].mean()) / sd))) if sd > 0 else None)

    def cls(c, s, L, g):
        k = (s, L, g)
        if k in conf:
            return 'confirmed'
        x = [tp[(cc, s, L, g)] for cc in design.CAMPAIGNS]
        if min(xx['points'] or 0 for xx in x) < design.CONFIRM_POINTS:
            return 'below_confirm_points'
        return 'cleared_screened' if k in scr else 'cleared_not_screened'

    out = {'schema': 'c8-d2-production-followup-1', 'run': str(a.run), 'rule': __doc__, 'var_total': var_total, 'strata': {}}
    for s in design.SECTORS:
        for L in (7, 8):
            keys = [k for k in G8 if k[1] == s and k[2] == L]
            by = {}
            for k in keys:
                by.setdefault(cls(*k) if L == 8 else 'diagnostic', []).append(k)
            st = {}
            for name, ks in sorted(by.items()):
                ku = sorted(((G8[k]['kurt'], k) for k in ks if G8[k]['kurt'] is not None), reverse=True)
                z = np.concatenate([(G8[k]['y'] - G8[k]['y'].mean()) / np.std(G8[k]['y'], ddof=1) for _, k in ku])
                pooled = float(np.mean(z ** 4) - 3.)
                drop = {}
                for kk in (1, 5, 20):
                    rest = [k for _, k in ku[kk:]]
                    if rest:
                        zz = np.concatenate([(G8[k]['y'] - G8[k]['y'].mean()) / np.std(G8[k]['y'], ddof=1) for k in rest])
                        drop[str(kk)] = float(np.mean(zz ** 4) - 3.)
                kv = np.asarray([x for x, _ in ku])
                st[name] = dict(graph_campaigns=len(ks), variance_share=sum(G8[k]['v'] for k in ks) / var_total, pooled_excess_kurtosis=pooled,
                                pooled_without_top_k=drop, per_graph_kurtosis=dict(q50=float(np.median(kv)), q90=float(np.quantile(kv, .9)),
                                                                                    q99=float(np.quantile(kv, .99)), max=float(kv.max())),
                                points_per_replicate=dict(min=min(G8[k]['n'] for k in ks), max=max(G8[k]['n'] for k in ks)),
                                variance_share_kurtosis_gt_3=sum(G8[k]['v'] for k in ks if (G8[k]['kurt'] or 0) > 3) / var_total,
                                variance_share_kurtosis_gt_10=sum(G8[k]['v'] for k in ks if (G8[k]['kurt'] or 0) > 10) / var_total,
                                top_kurtosis=[dict(campaign=k[0], graph=k[3], kurtosis=x, max_abs_z=G8[k]['max_abs_z'], points=G8[k]['n'],
                                                   share_of_C8_variance=G8[k]['v'] / var_total, xi_hat=tp[k]['xi_hat'], largest_share=tp[k]['largest_share'])
                                              for x, k in ku[:10]])
            out['strata'][f'{s}_L{L}'] = st
    top = sorted(G8, key=lambda k: -G8[k]['v'])[:25]
    out['top_variance_graph_campaigns'] = [dict(campaign=k[0], sector=k[1], L=k[2], graph=k[3], share_of_C8_variance=G8[k]['v'] / var_total,
                                                kurtosis=G8[k]['kurt'], max_abs_z=G8[k]['max_abs_z'], points=G8[k]['n'], xi_hat=tp[k]['xi_hat'],
                                                largest_share=tp[k]['largest_share'], tail_class=cls(*k) if k[2] == 8 else None) for k in top]
    allv = np.asarray(sorted((G8[k]['v'] for k in G8), reverse=True))
    out['concentration'] = dict(graph_campaigns=len(allv), top1=float(allv[:1].sum() / var_total), top10=float(allv[:10].sum() / var_total),
                                top100=float(allv[:100].sum() / var_total), top1000=float(allv[:1000].sum() / var_total))
    out['timing_s'] = time.time() - t0
    a.out.write_text(json.dumps(out, indent=1, default=float))
    print(f"var_total {var_total:.4f} (SE {math.sqrt(var_total):.4f}); concentration {out['concentration']}")
    for k, st in out['strata'].items():
        for name, x in st.items():
            print(f"{k} {name}: n {x['graph_campaigns']} share {x['variance_share']:.4f} pooled kurt {x['pooled_excess_kurtosis']:.3f} "
                  f"without top 1/5/20 {x['pooled_without_top_k']} per-graph {x['per_graph_kurtosis']} share(k>3) {x['variance_share_kurtosis_gt_3']:.4f} "
                  f"share(k>10) {x['variance_share_kurtosis_gt_10']:.4f} points {x['points_per_replicate']}")
            for t in x['top_kurtosis'][:3]:
                print(f"    top kurtosis {t}")
    for t in out['top_variance_graph_campaigns'][:10]:
        print(f"top variance {t}")
    print(f"timing {out['timing_s']:.0f} s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
