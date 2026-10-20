#!/usr/bin/env python3
"""Tail check, part B analysis: nested-N statistics of the fresh runs written by tc_nested.py.

  tc_nested_analyze.py RUNDIR CLASSES OUT.json [--boot 2000]

CLASSES lines: "<sector> <graph> <class>" (the selection's labels). Per graph and campaign, for every prefix N = chunk 2^j:
  sigma2(N) = N * Var_rep(prefix mean)  (ddof 1; the replicate means of the same R scrambles, nested)
  hill16(N) = mean over replicates of the Hill estimate from the 16 largest |t| of the prefix (exact: union of rows' tops)
  share(N)  = mean over replicates of max|t| / sum|t| in the prefix
  q16(N), qmax(N) = mean over replicates of ln(16th largest / mbar), ln(largest / mbar), mbar the mean |t| at nmax
and the log-log slopes of sigma2(N) (finite variance: <= 0 under RQMC, 0 under MC; infinite variance with tail xi:
2 xi - 1 > 0) and of exp(q16) (a regularly varying tail of index xi: xi; a bounded weight: falls to 0), each with a
bootstrap over replicates (95% percentile interval). Per class: the mean over graphs of each slope with the 95%
interval of the mean (graph-to-graph spread)."""
import argparse, json, math
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('rundir', type=Path)
ap.add_argument('classes', type=Path)
ap.add_argument('out', type=Path)
ap.add_argument('--boot', type=int, default=2000)
ap.add_argument('--nmin', type=int, default=4096)
a = ap.parse_args()
setup = json.loads((a.rundir / 'setup.json').read_text())
chunk = setup['chunk']; R = setup['reps']
klass = {}
for line in a.classes.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        s, g, k = line.split()[:3]; klass[(s, int(g))] = k
rng = np.random.default_rng(20261007)


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm = x.mean(); return float(((x - xm) * (y - y.mean())).sum() / ((x - xm) ** 2).sum())


def analyse(path):
    doc = json.loads(path.read_text())
    rows = doc['rows']
    nmax = rows[0]['total']; K = nmax // chunk
    val = np.zeros((R, K)); tsum = np.zeros((R, K)); tops = [[None] * K for _ in range(R)]
    for r in rows:
        k = r['begin'] // chunk; rep = r['rep']
        val[rep, k] = float(r['values'][0]) + float(r['values'][1])
        tsum[rep, k] = float(r['tail_sum']); tops[rep][k] = np.array([float(x) for x in r['tail_top']])
    levels = [chunk << j for j in range(int(math.log2(K)) + 1) if (chunk << j) >= a.nmin]
    cs = np.cumsum(val, axis=1)  # prefix sums of sum v / nmax
    means = {N: cs[:, N // chunk - 1] * (nmax / N) for N in levels}
    mbar = tsum.sum() / (R * nmax)
    hill, share, q16, qmax = {}, {}, {}, {}
    for N in levels:
        k = N // chunk; H = []; S = []; Q16 = []; QM = []
        for rep in range(R):
            t = np.sort(np.concatenate(tops[rep][:k]))[::-1][:16]
            lt = np.log(t); H.append(float(np.mean(lt[:15] - lt[15]))); S.append(float(t[0] / tsum[rep, :k].sum()))
            Q16.append(lt[15] - math.log(mbar)); QM.append(lt[0] - math.log(mbar))
        hill[N] = H; share[N] = S; q16[N] = Q16; qmax[N] = QM
    X = np.log(levels)

    def stats(idx):
        s2 = [N * np.var(means[N][idx], ddof=1) for N in levels]
        return (slope(X, np.log(s2)), slope(X, [np.mean(np.asarray(q16[N])[idx]) for N in levels]),
                slope(X, [np.mean(np.asarray(hill[N])[idx]) for N in levels]), s2)
    base = stats(np.arange(R))
    B = np.array([stats(rng.integers(0, R, R))[:3] for _ in range(a.boot)])
    ci = lambda j: [float(np.quantile(B[:, j], .025)), float(np.quantile(B[:, j], .975))]
    s2 = base[3]
    return dict(nmax=nmax, levels=levels, sigma2=[float(x) for x in s2], sigma2_rel=[float(x / s2[0]) for x in s2],
                slope_sigma2=base[0], slope_sigma2_ci=ci(0), slope_q16=base[1], slope_q16_ci=ci(1), slope_hill=base[2], slope_hill_ci=ci(2),
                hill16=[float(np.mean(hill[N])) for N in levels], share=[float(np.mean(share[N])) for N in levels],
                share_max=[float(np.max(share[N])) for N in levels], q16=[float(np.mean(q16[N])) for N in levels],
                qmax=[float(np.mean(qmax[N])) for N in levels], mean=[float(np.mean(means[N])) for N in levels],
                local_slopes=[float(math.log(s2[i + 1] / s2[i]) / math.log(2)) for i in range(len(s2) - 1)])


per = {}
for f in sorted((a.rundir / 'out').glob('*.json')):
    c, s, L, G = f.stem.split('_'); g = int(G[1:])
    per[f.stem] = dict(campaign=c, sector=s, L=int(L[1:]), graph=g, klass=klass.get((s, g), 'n/a')) | analyse(f)
    p = per[f.stem]
    print(f"{f.stem:22s} {p['klass']:22s} slope s2 {p['slope_sigma2']:+.3f} [{p['slope_sigma2_ci'][0]:+.3f},{p['slope_sigma2_ci'][1]:+.3f}]  "
          f"q16 {p['slope_q16']:+.3f}  hill {p['hill16'][0]:.3f}->{p['hill16'][-1]:.3f}  share {p['share'][0]:.4f}->{p['share'][-1]:.5f}", flush=True)
cls = {}
for k in sorted({(p['klass'], p['campaign']) for p in per.values()} | {(p['klass'], 'ab') for p in per.values()}):
    P = [p for p in per.values() if p['klass'] == k[0] and (k[1] == 'ab' or p['campaign'] == k[1])]
    if not P:
        continue
    out = dict(graph_campaigns=len(P))
    for f in ('slope_sigma2', 'slope_q16', 'slope_hill'):
        v = np.array([p[f] for p in P]); m = float(v.mean()); se = float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else float('nan')
        out[f] = dict(mean=m, ci95=[m - 1.96 * se, m + 1.96 * se], median=float(np.median(v)), min=float(v.min()), max=float(v.max()))
    # common prefix levels (2^12 .. 2^17) for the class curves
    lv = sorted(set.intersection(*[set(p['levels']) for p in P]))
    out['levels'] = lv
    out['log_sigma2_rel_mean'] = [float(np.mean([math.log(p['sigma2'][p['levels'].index(N)] / p['sigma2'][p['levels'].index(lv[0])]) for p in P])) for N in lv]
    out['hill16_median'] = [float(np.median([p['hill16'][p['levels'].index(N)] for p in P])) for N in lv]
    out['share_median'] = [float(np.median([p['share'][p['levels'].index(N)] for p in P])) for N in lv]
    out['q16_mean'] = [float(np.mean([p['q16'][p['levels'].index(N)] - p['q16'][p['levels'].index(lv[0])] for p in P])) for N in lv]
    cls[f'{k[0]} | {k[1]}'] = out
    print(f"CLASS {k[0]:22s} {k[1]:2s} n={len(P):3d}  slope s2 {out['slope_sigma2']['mean']:+.3f} [{out['slope_sigma2']['ci95'][0]:+.3f},{out['slope_sigma2']['ci95'][1]:+.3f}]  "
          f"q16 {out['slope_q16']['mean']:+.3f} [{out['slope_q16']['ci95'][0]:+.3f},{out['slope_q16']['ci95'][1]:+.3f}]  "
          f"hill {out['hill16_median'][0]:.3f}->{out['hill16_median'][-1]:.3f}  share {out['share_median'][0]:.4f}->{out['share_median'][-1]:.5f}", flush=True)
a.out.write_text(json.dumps(dict(setup={k: setup[k] for k in ('seed', 'reps', 'chunk', 'executable_sha256', 'rates')}, per_graph=per, classes=cls), indent=1))
