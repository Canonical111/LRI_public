#!/usr/bin/env python3
"""Nested-N statistics with joint replicate resampling (tail check, 2026-10-08; replaces the class intervals of
tc_nested_analyze.py / tc_nested_split.py, which were mean +- 1.96 x the between-graph-campaign SE over mixed windows).

  tc_nested_joint.py EXTRACT.json.gz CLASSES.txt CERT.jsonl(.gz) OUT.json [--boot 2000] [--seed 20261008]

Definitions (everything conditional on the SELECTED PANEL of graphs; these are not population intervals):
  * sigma2_gc(N) = N * Var_r(y_gc,r(N)) for graph g, campaign c, prefix N, over its R replicates (ddof 1), with
    y = J8 . (m0, m1) the C8 projection of the prefix-mean jets ("C8", primary) or y = m0 + m1 ("sum", the earlier
    analysis's quantity).
  * Common window W0 = {2^12, ..., 2^17} for every graph; extension window W1 = {2^12, ..., 2^19} and the extension
    segment {2^17, 2^18, 2^19} only for the graphs run to 2^19. A slope is the OLS slope of ln sigma2 on ln N.
  * The unit is the GRAPH: b_g = mean of its two campaigns' slopes. A class statistic is the mean of b_g over the
    class's graphs (each graph weight 1).
  * Hill: h_gc(N) = mean over replicates of the k = 16 Hill estimate; h_g = two-campaign mean; the class curve is the
    median over graphs of h_g(N), and its exponent the OLS slope of ln(curve) on ln N over W0.
  * F_gc = sigma2_gc(2^17) / sigma2_gc(N_prod): two prefix sizes of the SAME fresh run (N_prod = the graph-campaign's
    production point count); a within-run stability ratio, not a statement about the production estimate.
  * Phi_gc = sigma2_gc(N_prod) / sigma2_prod,gc(N_prod): the fresh run's per-point variance at the production's own
    point count over the production's (128 replicates), both in the C8 projection; the class value is weighted by
    the graph-campaign's production share of Var(C8).
Uncertainty: B bootstrap draws; in each, one vector of R replicate indices per net (run, campaign, sector) is drawn
and applied to EVERY graph and EVERY prefix of that net (the nets' scrambles are shared by all graphs of the net and
the prefixes are nested), and one vector of 128 indices per production group (campaign, sector, L) likewise. The
95% intervals are percentile intervals of the class statistic over the draws (scramble-sampling uncertainty given the
panel)."""
import argparse, gzip, json, math
from collections import defaultdict
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('extract'); ap.add_argument('classes'); ap.add_argument('cert'); ap.add_argument('out')
ap.add_argument('--boot', type=int, default=2000); ap.add_argument('--seed', type=int, default=20261008)
a = ap.parse_args()
X = json.load(gzip.open(a.extract, 'rt'))
J8 = np.asarray(X['J8'])
op = gzip.open if a.cert.endswith('.gz') else open
cert = {}
with op(a.cert, 'rt') as f:
    for l in f:
        r = json.loads(l)
        if r['L'] == 8 and not r.get('label'):
            cert[(r['sector'], r['id'])] = r
klass = {}
for line in open(a.classes):
    if line.strip() and not line.startswith('#'):
        s, g, k = line.split()[:3]; klass[(s, int(g))] = k
W0 = [4096 << j for j in range(6)]
W1 = [4096 << j for j in range(8)]
WE = [131072, 262144, 524288]


def group(run, s, g):
    if run == 'dl':
        return 'double-lift power L8, targeted (16 largest variance shares)'
    k = klass[(s, g)]
    if k.startswith('control'):
        return 'controls (cleared, never screened, primitives)'
    if k == 'conf_free':
        return 'confirmed free L8'
    if k == 'conf_power':
        return 'confirmed power L8'
    dl = cert[(s, g)]['max_orders_cancelled'] >= 2
    return 'untestable power L8, double-lift (earlier sample)' if dl else 'untestable power L8, no double-lift'


GC = []
for key, d in X['graphs'].items():
    lv = d['levels']
    m0 = np.asarray(d['m0']); m1 = np.asarray(d['m1'])
    pk = f"{d['campaign']}_{d['sector']}_L{d['L']}_G{d['graph']}"
    P = X['production'][pk]
    GC.append(dict(key=key, run=d['run'], c=d['campaign'], s=d['sector'], L=d['L'], g=d['graph'], levels=lv, net=(d['run'], d['campaign'], d['sector']),
                   yC=m0 * J8[0] + m1 * J8[1], yS=m0 + m1, hill=np.asarray(d['hill']), share=np.asarray(d['share']),
                   group=group(d['run'], d['sector'], d['graph']), prod=P, pgroup=(d['campaign'], d['sector'], d['L']),
                   prodC=np.asarray(P['Y0']) * J8[0] + np.asarray(P['Y1']) * J8[1]))
nets = sorted({x['net'] for x in GC}); pgroups = sorted({x['pgroup'] for x in GC})
R = {n: next(len(x['yC']) for x in GC if x['net'] == n) for n in nets}
RP = {p: next(len(x['prodC']) for x in GC if x['pgroup'] == p) for p in pgroups}


def slope(N, s2):
    x = np.log(np.asarray(N, float)); y = np.log(np.asarray(s2, float)); xm = x.mean()
    return float(((x - xm) * (y - y.mean())).sum() / ((x - xm) ** 2).sum())


def stats(idx, pidx):
    """Every per-graph-campaign quantity for replicate index vectors idx[net], pidx[production group]."""
    out = {}
    for x in GC:
        i = idx[x['net']]; lv = x['levels']
        s2C = {N: N * np.var(x['yC'][i, j], ddof=1) for j, N in enumerate(lv)}
        s2S = {N: N * np.var(x['yS'][i, j], ddof=1) for j, N in enumerate(lv)}
        h = {N: float(np.mean(x['hill'][i, j])) for j, N in enumerate(lv)}
        r = dict(s2C=s2C, s2S=s2S, hill=h,
                 bC0=slope(W0, [s2C[N] for N in W0]), bS0=slope(W0, [s2S[N] for N in W0]))
        if 524288 in s2C:
            r['bC1'] = slope(W1, [s2C[N] for N in W1]); r['bCE'] = slope(WE, [s2C[N] for N in WE]); r['bS1'] = slope(W1, [s2S[N] for N in W1])
        n = x['prod']['points']
        if n in s2C:
            pi = pidx[x['pgroup']]
            sp = n * np.var(x['prodC'][pi], ddof=1)
            r['F'] = s2C[131072] / s2C[n]; r['Phi'] = s2C[n] / sp
        out[x['key']] = r
    return out


def classes(st):
    """Class statistics (graph = unit) from per-graph-campaign stats."""
    byg = defaultdict(list)
    for x in GC:
        byg[(x['group'], x['run'], x['s'], x['g'])].append(x)
    res = defaultdict(dict)
    G = defaultdict(list)
    for (grp, run, s, g), xs in byg.items():
        G[grp].append(xs)
    for grp, graphs in G.items():
        rr = res[grp]
        rr['bC0'] = float(np.mean([np.mean([st[x['key']]['bC0'] for x in xs]) for xs in graphs]))
        rr['bS0'] = float(np.mean([np.mean([st[x['key']]['bS0'] for x in xs]) for xs in graphs]))
        curve = [float(np.median([np.mean([st[x['key']]['hill'][N] for x in xs]) for xs in graphs])) for N in W0]
        rr['hill_curve'] = curve; rr['hill_exponent'] = slope(W0, curve)
        # share-weighted F and Phi over graph-campaigns that have N_prod among the levels
        for f in ('F', 'Phi'):
            w = [(x['prod']['share'], st[x['key']][f]) for xs in graphs for x in xs if f in st[x['key']]]
            rr[f] = float(sum(a * b for a, b in w) / sum(a for a, _ in w)) if w else None
        rel = [float(np.exp(np.mean([np.log(np.mean([st[x['key']]['s2C'][N] / st[x['key']]['s2C'][4096] for x in xs])) for xs in graphs]))) for N in W0]
        rr['sigma2C_rel_geomean'] = rel
    return res


base_idx = {n: np.arange(R[n]) for n in nets}; base_pidx = {p: np.arange(RP[p]) for p in pgroups}
st0 = stats(base_idx, base_pidx); cl0 = classes(st0)
rng = np.random.default_rng(a.seed)
boot_cl = []; boot_st = []
for b in range(a.boot):
    idx = {n: rng.integers(0, R[n], R[n]) for n in nets}; pidx = {p: rng.integers(0, RP[p], RP[p]) for p in pgroups}
    st = stats(idx, pidx); boot_st.append(st); boot_cl.append(classes(st))


def ci(vals):
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    return [float(np.quantile(v, .025)), float(np.quantile(v, .975))] if len(v) else None


out = dict(definitions=__doc__, boot=a.boot, seed=a.seed, J8=J8.tolist(), nets=[list(n) for n in nets], replicates={'/'.join(n): R[n] for n in nets},
           production_groups={'/'.join(map(str, p)): RP[p] for p in pgroups}, classes={}, graphs={})
for grp in sorted(cl0):
    gs = sorted({(x['run'], x['s'], x['g']) for x in GC if x['group'] == grp})
    c = cl0[grp]
    out['classes'][grp] = dict(
        graphs=len(gs), graph_campaigns=sum(1 for x in GC if x['group'] == grp),
        production_share_of_var_C8=float(sum(x['prod']['share'] for x in GC if x['group'] == grp)),
        slope_C8_W0=dict(value=c['bC0'], ci95=ci([bc[grp]['bC0'] for bc in boot_cl])),
        slope_sum_W0=dict(value=c['bS0'], ci95=ci([bc[grp]['bS0'] for bc in boot_cl])),
        hill_curve_W0=c['hill_curve'], hill_exponent_W0=dict(value=c['hill_exponent'], ci95=ci([bc[grp]['hill_exponent'] for bc in boot_cl])),
        sigma2C_rel_geomean_W0=c['sigma2C_rel_geomean'],
        F_within_run_2p17_over_Nprod_share_weighted=dict(value=c['F'], ci95=ci([bc[grp]['F'] for bc in boot_cl])),
        Phi_fresh_over_production_at_Nprod_share_weighted=dict(value=c['Phi'], ci95=ci([bc[grp]['Phi'] for bc in boot_cl])),
        per_graph_slope_C8_W0=dict(min=float(min(np.mean([st0[x['key']]['bC0'] for x in GC if (x['run'], x['s'], x['g']) == k]) for k in gs)),
                                   median=float(np.median([np.mean([st0[x['key']]['bC0'] for x in GC if (x['run'], x['s'], x['g']) == k]) for k in gs])),
                                   max=float(max(np.mean([st0[x['key']]['bC0'] for x in GC if (x['run'], x['s'], x['g']) == k]) for k in gs))))
for x in GC:
    r = st0[x['key']]; k = x['key']
    d = dict(group=x['group'], campaign=x['c'], sector=x['s'], graph=x['g'], levels=x['levels'],
             sigma2C=[float(r['s2C'][N]) for N in x['levels']], sigma2S=[float(r['s2S'][N]) for N in x['levels']],
             hill=[r['hill'][N] for N in x['levels']], share_mean=[float(np.mean(x['share'][:, j])) for j in range(len(x['levels']))],
             share_max=[float(np.max(x['share'][:, j])) for j in range(len(x['levels']))],
             slope_C8_W0=dict(value=r['bC0'], ci95=ci([bs[k]['bC0'] for bs in boot_st])),
             slope_sum_W0=dict(value=r['bS0'], ci95=ci([bs[k]['bS0'] for bs in boot_st])),
             production=dict(points=x['prod']['points'], share=x['prod']['share'], kurtosis=x['prod']['kurtosis'], xi_hat=x['prod']['xi_hat']))
    if 'bC1' in r:
        d['slope_C8_W1'] = dict(value=r['bC1'], ci95=ci([bs[k]['bC1'] for bs in boot_st]))
        d['slope_C8_extension_2p17_2p19'] = dict(value=r['bCE'], ci95=ci([bs[k]['bCE'] for bs in boot_st]))
        d['slope_sum_W1'] = dict(value=r['bS1'], ci95=ci([bs[k]['bS1'] for bs in boot_st]))
    if 'F' in r:
        d['F'] = dict(value=r['F'], ci95=ci([bs[k].get('F') for bs in boot_st]))
        d['Phi'] = dict(value=r['Phi'], ci95=ci([bs[k].get('Phi') for bs in boot_st]))
    out['graphs'][k] = d
# extended graphs: per graph (two-campaign mean) W1 and extension-segment slopes
ext = defaultdict(list)
for x in GC:
    if 'bC1' in st0[x['key']]:
        ext[(x['group'], x['run'], x['s'], x['g'])].append(x)
out['extensions_2p19'] = {}
for (grp, run, s, g), xs in sorted(ext.items()):
    keys = [x['key'] for x in xs]
    val = lambda st, f: float(np.mean([st[k][f] for k in keys]))
    out['extensions_2p19'][f'{run}:{s} G{g}'] = dict(group=grp, campaigns=len(xs),
                                                     slope_C8_W0=dict(value=val(st0, 'bC0'), ci95=ci([val(bs, 'bC0') for bs in boot_st])),
                                                     slope_C8_W1=dict(value=val(st0, 'bC1'), ci95=ci([val(bs, 'bC1') for bs in boot_st])),
                                                     slope_C8_extension=dict(value=val(st0, 'bCE'), ci95=ci([val(bs, 'bCE') for bs in boot_st])),
                                                     hill_2p12_2p19=[float(np.mean([st0[k]['hill'][N] for k in keys])) for N in (4096, 131072, 524288)])
json.dump(out, open(a.out, 'w'), indent=1)
for grp, c in out['classes'].items():
    print(f"{grp:58s} graphs {c['graphs']:2d}  slope(C8,W0) {c['slope_C8_W0']['value']:+.3f} [{c['slope_C8_W0']['ci95'][0]:+.3f},{c['slope_C8_W0']['ci95'][1]:+.3f}]  "
          f"slope(sum,W0) {c['slope_sum_W0']['value']:+.3f} [{c['slope_sum_W0']['ci95'][0]:+.3f},{c['slope_sum_W0']['ci95'][1]:+.3f}]  "
          f"Hill exp {c['hill_exponent_W0']['value']:+.3f} [{c['hill_exponent_W0']['ci95'][0]:+.3f},{c['hill_exponent_W0']['ci95'][1]:+.3f}]  "
          f"F {c['F_within_run_2p17_over_Nprod_share_weighted']['value']}  Phi {c['Phi_fresh_over_production_at_Nprod_share_weighted']['value']}", flush=True)
for k, e in out['extensions_2p19'].items():
    print(f"EXT {k:22s} {e['group'][:30]:30s} W0 {e['slope_C8_W0']['value']:+.3f} W1 {e['slope_C8_W1']['value']:+.3f} [{e['slope_C8_W1']['ci95'][0]:+.3f},{e['slope_C8_W1']['ci95'][1]:+.3f}] "
          f"ext {e['slope_C8_extension']['value']:+.3f} [{e['slope_C8_extension']['ci95'][0]:+.3f},{e['slope_C8_extension']['ci95'][1]:+.3f}] hill {e['hill_2p12_2p19']}")
