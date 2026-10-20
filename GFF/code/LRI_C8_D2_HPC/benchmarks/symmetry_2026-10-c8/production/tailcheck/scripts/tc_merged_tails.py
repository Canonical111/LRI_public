#!/usr/bin/env python3
"""Tail check, existing data (read-only): tail growth from the pilot (4,096 points x 8 replicates) to the production
(n_g points x 128 replicates) for the same L7/L8 graphs, from the merged per-replicate tail tables
(groups/<c>_<s>_L<L>/graph_tails.csv: points, tail_sum, top_1..top_16 per graph-replicate).

  tc_merged_tails.py --pilot PILOT_RUN --prod PROD_RUN --classes PROD_TAILS_CSV --out OUT.json

The production checkpoints hold one row per graph-replicate for every L8 graph (the chunk is the whole replicate), so
nested prefixes cannot be rebuilt from them. Instead this compares quantiles at two sample sizes with independent
scrambles. Per graph-campaign (scale removed by the graph-campaign mean |t|, mbar = sum tail_sum / sum points):
  q16(N)  = mean over replicates of ln(top_16 / mbar)   (the 1 - 16/N quantile of |t|)
  qmax(N) = mean over replicates of ln(top_1 / mbar)    (the block maximum)
  hill_k  = mean over replicates of the Hill estimate from the k largest (k = 4, 8, 16)
  xi_sd   = sd over replicates of ln(top_1) * sqrt(6)/pi (exactly 1/a for a Frechet maximum)
and the growth exponents g16 = [q16(N2) - q16(N1)] / ln(N2/N1), gmax likewise. For a regularly varying tail of
index xi both equal xi (the quantile at level k/N grows like N^xi); for a bounded weight they fall to 0. Classes are
the production report's (both campaigns at >= 32,768 points and two-campaign mean Hill > 0.44: confirmed)."""
import argparse, csv, gzip, json, math
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--pilot', type=Path, required=True)
ap.add_argument('--prod', type=Path, required=True)
ap.add_argument('--classes', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()


def read_tails(path):
    out = {}
    with open(path) as f:
        r = csv.reader(f); head = next(r)
        ix = {h: i for i, h in enumerate(head)}
        for row in r:
            g = int(row[ix['graph']]); n = int(row[ix['points']]); k = int(row[ix['tail_n']])
            top = [float(row[ix[f'top_{j}']]) for j in range(1, k + 1)]
            out.setdefault(g, []).append((n, float(row[ix['tail_sum']]), top))
    return out


def stats(reps):
    n = reps[0][0]
    if any(x[0] != n for x in reps) or any(len(x[2]) < 16 for x in reps):
        return None
    mbar = sum(x[1] for x in reps) / (n * len(reps))
    T = np.array([x[2] for x in reps])  # (R, 16) descending
    if mbar <= 0 or (T <= 0).any():
        return None
    lT = np.log(T)
    hill = {k: float(np.mean(np.mean(lT[:, :k - 1] - lT[:, k - 1:k], axis=1))) for k in (4, 8, 16)}
    return dict(n=n, R=len(reps), q16=float(np.mean(lT[:, 15]) - math.log(mbar)), qmax=float(np.mean(lT[:, 0]) - math.log(mbar)),
                hill=hill, xi_sd=float(np.std(lT[:, 0], ddof=1) * math.sqrt(6) / math.pi),
                share=float(np.mean([x[2][0] / x[1] for x in reps])), mbar=mbar)


cls = {}
with gzip.open(a.classes, 'rt') as f:
    rows = list(csv.DictReader(f))
by = {}
for r in rows:
    if r['L'] != '8' or r['status'] != 'defined':
        continue
    by.setdefault((r['sector'], int(r['graph'])), {})[r['campaign']] = (int(r['points']), float(r['xi_hat']))
for k, v in by.items():
    if len(v) < 2:
        continue
    testable = min(v['a'][0], v['b'][0]) >= 32768
    m = (v['a'][1] + v['b'][1]) / 2
    cls[k] = 'confirmed' if testable and m > 0.44 else ('cleared' if testable else 'untestable')

res = {'note': __doc__, 'classes': {}}
per_graph = []
for s in ('free', 'power'):
    for L in (7, 8):
        for c in ('a', 'b'):
            name = f'{c}_{s}_L{L}'
            P = read_tails(a.pilot / 'groups' / name / 'graph_tails.csv')
            Q = read_tails(a.prod / 'groups' / name / 'graph_tails.csv')
            for g in sorted(set(P) & set(Q)):
                p, q = stats(P[g]), stats(Q[g])
                if not p or not q or q['n'] <= p['n']:
                    continue
                lr = math.log(q['n'] / p['n'])
                klass = cls.get((s, g), 'n/a') if L == 8 else 'diagnostic'
                per_graph.append(dict(c=c, s=s, L=L, g=g, klass=klass, n1=p['n'], n2=q['n'], g16=(q['q16'] - p['q16']) / lr, gmax=(q['qmax'] - p['qmax']) / lr,
                                      hill16_1=p['hill'][16], hill16_2=q['hill'][16], hill4_2=q['hill'][4], hill8_2=q['hill'][8], xi_sd_2=q['xi_sd'],
                                      share_1=p['share'], share_2=q['share'], q16_1=p['q16'], q16_2=q['q16'], qmax_1=p['qmax'], qmax_2=q['qmax']))


def summ(X):
    X = np.asarray(X, float)
    return dict(n=int(len(X)), median=float(np.median(X)), q10=float(np.quantile(X, .1)), q90=float(np.quantile(X, .9)), mean=float(X.mean()),
                se_mean=float(X.std(ddof=1) / math.sqrt(len(X))) if len(X) > 1 else None)


groups = {}
for r in per_graph:
    groups.setdefault((r['s'], r['L'], r['klass'], r['n2'] // r['n1']), []).append(r)
for (s, L, k, ratio), R in sorted(groups.items()):
    if len(R) < 10:
        continue
    res['classes'][f'{s} L{L} {k} N2/N1={ratio}'] = {f: summ([r[f] for r in R]) for f in
                                                    ('g16', 'gmax', 'hill16_1', 'hill16_2', 'hill8_2', 'hill4_2', 'xi_sd_2', 'share_1', 'share_2')}
a.out.write_text(json.dumps(res, indent=1))
with gzip.open(a.out.with_suffix('.per_graph.json.gz'), 'wt') as f:
    json.dump(per_graph, f)
for k, v in res['classes'].items():
    print(f"{k:42s} n={v['g16']['n']:5d}  g16 {v['g16']['median']:+.3f} [{v['g16']['q10']:+.3f},{v['g16']['q90']:+.3f}]  gmax {v['gmax']['median']:+.3f}  "
          f"Hill16 {v['hill16_1']['median']:.3f}->{v['hill16_2']['median']:.3f}  Hill8/4 {v['hill8_2']['median']:.3f}/{v['hill4_2']['median']:.3f}  "
          f"xi_sd {v['xi_sd_2']['median']:.3f}  share {v['share_1']['median']:.4f}->{v['share_2']['median']:.5f}")
