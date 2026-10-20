#!/usr/bin/env python3
"""Tail check, part A2 (Mac, existing data only): matched campaign a/b Hill comparison and the pilot-to-production
xi-hat change of the L8 graphs, from the two committed tails.csv.gz (pilot 570669, production report 571296).

  tc_ab_hill.py OUT.json

Classes as in the production report (tools/design.tail_table): a graph is "confirmed" when both campaigns have
>= 32,768 points per replicate and the two-campaign mean xi-hat exceeds 0.44.
Tests:
 (1) a rate-driven boundary singularity at a common face predicts xi_c = 1 - m/(rho_c alpha), hence
     xi_b = 1 - (8/9)(1 - xi_a) (rates .8 / .9): b heavier by (1 - xi_a)/9. Compared on graphs whose two campaigns had
     equal points per replicate, with a/b selection removed by classifying on the OTHER campaign (cross-selection).
 (2) the pilot (4,096 points, 8 replicates) to production (n points, 128 replicates) xi-hat ratio per graph, against
     what tail models predict for the fixed-k (k = 16) Hill estimate: exact Pareto (ratio 1), slowly varying /
     exponential-type tails (ratio ~ log(N1/k)/log(N2/k)), lognormal (Mills-ratio residual), bounded peak with
     density exponent b near the maximum ((N1/N2)^(1/b)). Cross-selected again (classified on campaign a,
     measured on campaign b) to remove the selection bias of the confirmation.
"""
import csv, gzip, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[3]          # benchmarks/symmetry_2026-10-c8
PILOT = HERE / 'pilot/analysis/pa.570669.0/tails.csv.gz'
PROD = HERE / 'production/result/prres2.571296.0/tails.csv.gz'
K = 16


def load(p):
    out = {}
    with gzip.open(p, 'rt') as f:
        for r in csv.DictReader(f):
            if r['L'] != '8' or r['status'] != 'defined':
                continue
            out[(r['campaign'], r['sector'], int(r['graph']))] = (int(r['points']), float(r['xi_hat']), float(r['largest_share']))
    return out


def q(x):
    x = np.asarray(x, float)
    return dict(n=int(len(x)), q10=float(np.quantile(x, .1)), median=float(np.median(x)), q90=float(np.quantile(x, .9)), mean=float(x.mean()))


def mills_residual(z):
    from math import erfc, exp, pi, sqrt
    Q = 0.5 * erfc(z / sqrt(2)); phi = exp(-z * z / 2) / sqrt(2 * pi)
    return phi / Q - z


def zq(p):
    from statistics import NormalDist
    return NormalDist().inv_cdf(1 - p)


def main():
    pil, prod = load(PILOT), load(PROD)
    graphs = sorted({(s, g) for (c, s, g) in prod})
    res = {'sources': {'pilot': str(PILOT.relative_to(HERE)), 'production': str(PROD.relative_to(HERE))}}
    rows = []
    for s, g in graphs:
        a, b = prod.get(('a', s, g)), prod.get(('b', s, g))
        pa, pb = pil.get(('a', s, g)), pil.get(('b', s, g))
        if not (a and b and pa and pb):
            continue
        conf = min(a[0], b[0]) >= 32768 and (a[1] + b[1]) / 2 > 0.44
        rows.append(dict(s=s, g=g, na=a[0], nb=b[0], xa=a[1], xb=b[1], pxa=pa[1], pxb=pb[1], conf=conf, testable=min(a[0], b[0]) >= 32768))
    # (1) matched a/b
    ab = {}
    for s in ('free', 'power'):
        for label, sel in (('confirmed', lambda r: r['conf']), ('a-selected xi_a>0.44 (b measured)', lambda r: r['testable'] and r['xa'] > 0.44),
                           ('b-selected xi_b>0.44 (a measured)', lambda r: r['testable'] and r['xb'] > 0.44),
                           ('a-selected xi_a<=0.30 (light)', lambda r: r['testable'] and r['xa'] <= 0.30)):
            R = [r for r in rows if r['s'] == s and sel(r) and r['na'] == r['nb']]
            if len(R) < 5:
                continue
            xa = np.array([r['xa'] for r in R]); xb = np.array([r['xb'] for r in R])
            pred = 1 - (8 / 9) * (1 - xa)
            d = xb - xa
            ab[f'{s} | {label}'] = dict(graphs=len(R), xi_a=q(xa), xi_b=q(xb), diff_b_minus_a=dict(mean=float(d.mean()), se=float(d.std(ddof=1) / math.sqrt(len(d))), median=float(np.median(d))),
                                       rate_model_predicted_diff=dict(mean=float((pred - xa).mean())), corr_ab=float(np.corrcoef(xa, xb)[0, 1]),
                                       slope_b_on_a=float(np.polyfit(xa, xb, 1)[0]))
    res['ab_matched_points'] = ab
    # (2) pilot -> production, cross-selected
    N1 = 4096
    models = {}
    for N2 in (32768, 65536, 131072):
        lr = math.log(N1 / K) / math.log(N2 / K)
        ln = mills_residual(zq(K / N2)) / mills_residual(zq(K / N1))   # lognormal tail, Hill at the k/N quantile
        models[str(N2)] = dict(pareto=1.0, log_type=lr, lognormal=ln, bounded_b4=(N1 / N2) ** 0.25, bounded_b8=(N1 / N2) ** 0.125)
    res['hill_ratio_models_k16'] = models
    ch = {}
    for s in ('free', 'power'):
        for label, sel, meas in (('confirmed (both campaigns, as reported)', lambda r: r['conf'], 'mean'),
                                 ('classified on a (xi_a>0.44), measured on b', lambda r: r['testable'] and r['xa'] > 0.44, 'b'),
                                 ('classified on b (xi_b>0.44), measured on a', lambda r: r['testable'] and r['xb'] > 0.44, 'a'),
                                 ('pilot-screened on a (pilot xi_a>0.38), measured on b', lambda r: r['testable'] and r['pxa'] > 0.38, 'b'),
                                 ('pilot xi_a>0.8 on a, measured on b', lambda r: r['testable'] and r['pxa'] > 0.8, 'b')):
            for N2 in (32768, 65536, 131072):
                R = [r for r in rows if r['s'] == s and sel(r) and r['na'] == N2 and r['nb'] == N2]
                if len(R) < 10:
                    continue
                if meas == 'mean':
                    x1 = np.array([(r['pxa'] + r['pxb']) / 2 for r in R]); x2 = np.array([(r['xa'] + r['xb']) / 2 for r in R])
                else:
                    x1 = np.array([r['px' + meas] for r in R]); x2 = np.array([r['x' + meas] for r in R])
                ratio = x2 / x1
                ch[f'{s} | {label} | n2={N2}'] = dict(graphs=len(R), pilot_xi=q(x1), production_xi=q(x2), ratio=q(ratio),
                                                     ratio_of_medians=float(np.median(x2) / np.median(x1)), frac_rose=float((x2 > x1).mean()))
    res['pilot_to_production'] = ch
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1))
    for k, v in ab.items():
        print(f"AB {k}: n={v['graphs']} xi_a med {v['xi_a']['median']:.3f} xi_b med {v['xi_b']['median']:.3f} b-a {v['diff_b_minus_a']['mean']:+.4f}+-{v['diff_b_minus_a']['se']:.4f} "
              f"(rate model {v['rate_model_predicted_diff']['mean']:+.4f}) corr {v['corr_ab']:.2f} slope {v['slope_b_on_a']:.2f}")
    for k, v in models.items():
        print('models', k, {kk: round(vv, 3) for kk, vv in v.items()})
    for k, v in ch.items():
        print(f"CH {k}: n={v['graphs']} pilot med {v['pilot_xi']['median']:.3f} prod med {v['production_xi']['median']:.3f} ratio med {v['ratio']['median']:.3f} "
              f"[{v['ratio']['q10']:.3f},{v['ratio']['q90']:.3f}] rose {v['frac_rose']:.3f}")


if __name__ == '__main__':
    main()
