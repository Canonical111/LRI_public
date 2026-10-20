#!/usr/bin/env python3
"""Tail check: the shape of the final graph sum at the replicate level (read-only), the check the pooled
per-graph-standardized kurtosis does not make.

  tc_replicate_c8.py --package PKG --run PROD --classes PROD_TAILS.csv.gz --out OUT.json

With tools/design.load_pilot, per group (campaign, sector, L) the C8-projected replicate values y_r = sum_g J8 . Y_rg
(the linearization the assembly's variance uses). Replicate r of campaign c: z_c,r = sum over the c groups; the final
z_r = (z_a,r + z_b,r)/2 over the 128 independent replicate indices (each group's replicates are independent
scrambles, so the index-wise sum is a replicate of the total). Reports per campaign and for z: the mean, sd/sqrt(R)
(the analytic SE scale), skewness, excess kurtosis (Gaussian reference at R = 128 about -0.09), the largest |z-score|,
a Shapiro-Wilk p-value, the jackknife SE, and median-of-means over B = 8 blocks of 16 (and its spread). The same for the
partial sums over the confirmed free L8 graphs, the power L8 graphs below 32,768 points, and the rest."""
import argparse, csv, gzip, json, math, sys
from pathlib import Path
import numpy as np
from scipy import stats as st

ap = argparse.ArgumentParser()
ap.add_argument('--package', type=Path, required=True)
ap.add_argument('--run', type=Path, required=True)
ap.add_argument('--classes', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.package / 'tools'))
import design
P = design.load_pilot(a.run)
by = {}
with gzip.open(a.classes, 'rt') as f:
    for r in csv.DictReader(f):
        if r['L'] == '8' and r['status'] == 'defined':
            by.setdefault((r['sector'], int(r['graph'])), {})[r['campaign']] = (int(r['points']), float(r['xi_hat']))
cls = {}
for k, v in by.items():
    t = min(v['a'][0], v['b'][0]) >= 32768; m = (v['a'][1] + v['b'][1]) / 2
    cls[k] = 'confirmed' if t and m > 0.44 else ('cleared' if t else 'untestable')
parts = {}
reps = set()
for (c, s, L), G in P.groups.items():
    if not len(G.graphs):
        continue
    y = np.einsum('rgj,j->rg', G.Y, P.J8[L])
    reps.add(G.reps)
    lab = np.array([('conf_free_L8' if (L == 8 and s == 'free' and cls.get((s, g)) == 'confirmed') else
                     'untest_power_L8' if (L == 8 and s == 'power' and cls.get((s, g)) == 'untestable') else
                     'conf_power_L8' if (L == 8 and s == 'power' and cls.get((s, g)) == 'confirmed') else 'rest') for g in G.graphs])
    for name in ('conf_free_L8', 'untest_power_L8', 'conf_power_L8', 'rest'):
        m = lab == name
        if m.any():
            parts.setdefault((c, name), np.zeros(G.reps))
            parts[(c, name)] = parts[(c, name)] + y[:, m].sum(1)
assert len(reps) == 1, reps
R = reps.pop()


def describe(z):
    z = np.asarray(z, float); n = len(z); m = z.mean(); sd = z.std(ddof=1)
    jk = np.array([(z.sum() - z[i]) / (n - 1) for i in range(n)]); jse = math.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum())
    B = 8; blocks = z[: n - n % B].reshape(B, -1).mean(1)
    return dict(mean=float(m), se=float(sd / math.sqrt(n)), jackknife_se=float(jse), skew=float(st.skew(z)), excess_kurtosis=float(st.kurtosis(z)),
                max_abs_z=float(np.max(np.abs(z - m)) / sd), shapiro_p=float(st.shapiro(z).pvalue),
                median_of_means=float(np.median(blocks)), mom_block_sd_over_sqrtB=float(blocks.std(ddof=1) / math.sqrt(B)),
                mom_minus_mean_in_se=float((np.median(blocks) - m) / (sd / math.sqrt(n))))


out = {'replicates': R, 'note': __doc__}
tot = {c: sum(v for (cc, _), v in parts.items() if cc == c) for c in ('a', 'b')}
for c in ('a', 'b'):
    out[f'campaign_{c}'] = describe(tot[c])
out['final_z=(a+b)/2'] = describe((tot['a'] + tot['b']) / 2)
for name in ('conf_free_L8', 'untest_power_L8', 'conf_power_L8', 'rest'):
    out[f'part {name}'] = describe((parts[('a', name)] + parts[('b', name)]) / 2)
# Gaussian reference for the kurtosis and max|z| at this R
g = np.random.default_rng(1).standard_normal((20000, R))
out['gaussian_reference'] = dict(excess_kurtosis_median=float(np.median(st.kurtosis(g, axis=1))), excess_kurtosis_q95=float(np.quantile(st.kurtosis(g, axis=1), .95)),
                                 max_abs_z_q95=float(np.quantile(np.max(np.abs(g - g.mean(1, keepdims=True)) / g.std(1, ddof=1, keepdims=True), axis=1), .95)))
# where the largest replicate deviations come from: per campaign, the 3 replicates of largest |z|, with each part's and
# each (sector, L) stratum's deviation from its mean in units of the campaign total's sd
strata = {}
for (c, s, L), G in P.groups.items():
    if len(G.graphs):
        strata[(c, f'{s}_L{L}')] = np.einsum('rgj,j->rg', G.Y, P.J8[L]).sum(1)
for c in ('a', 'b'):
    z = tot[c]; sd = z.std(ddof=1); idx = np.argsort(-np.abs(z - z.mean()))[:3]
    out[f'outliers_{c}'] = [dict(replicate=int(i), z=float((z[i] - z.mean()) / sd),
                                 parts={n: float((parts[(c, n)][i] - parts[(c, n)].mean()) / sd) for n in ('conf_free_L8', 'untest_power_L8', 'conf_power_L8', 'rest')},
                                 strata_top=dict([(k[1], float((v[i] - v.mean()) / sd)) for k, v in sorted(strata.items(), key=lambda kv: -abs(kv[1][i] - kv[1].mean())) if k[0] == c][:4]))
                            for i in idx]
    for n in ('conf_free_L8', 'untest_power_L8', 'conf_power_L8', 'rest'):
        out[f'part {n} campaign {c}'] = describe(parts[(c, n)])
    for k, v in strata.items():
        if k[0] == c and k[1] in ('free_L8', 'free_L7', 'power_L8', 'power_L7'):
            out[f'stratum {k[1]} campaign {c}'] = describe(v)
    zz = z.copy(); i0 = idx[0]; zz = np.delete(zz, i0)
    out[f'campaign_{c}_without_largest'] = describe(zz)
a.out.write_text(json.dumps(out, indent=1))
for k, v in out.items():
    if isinstance(v, dict):
        print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
