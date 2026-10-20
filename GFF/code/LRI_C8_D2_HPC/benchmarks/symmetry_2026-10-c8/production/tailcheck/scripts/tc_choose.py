#!/usr/bin/env python3
"""Tail check part B: the graph sample of the fresh nested-N runs (deterministic; Mac).

  tc_choose.py SELECT_DATA.csv.gz PROD_TAILS.csv.gz INVENTORY.json OUT_GRAPHS OUT_CLASSES [--reps 32] [--budget 100]

Classes (production report's rule): confirmed (both campaigns >= 32,768 points, two-campaign mean Hill > 0.44),
cleared, untestable (power L8 below 32,768 points). Sample (Codex review's staged design, 48 graphs):
  conf_free 16: the 8 largest variance contributors (both campaigns summed) and 8 spanning the Hill quantiles;
  conf_power 8: the 4 largest variance contributors and the 4 largest Hill values;
  untest_power 16: the 8 largest variance contributors, 6 stratified by Hill tercile (rng 20261007), G12233 and G12210;
  control 8: 4 cleared free (2 never screened, 2 screened: largest variance), 2 cleared power, 2 free primitives.
nmax = 2^17 for all; 2^19 for 8 (the 3 largest conf_free contributors, the conf_free graph of largest Hill among the
16, the 2 largest conf_power contributors, the largest untestable power contributor and G12233). Cost from the
production's measured seconds per point (dd+mp256, EPYC 7543)."""
import argparse, csv, gzip, json, math
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('data'); ap.add_argument('tails'); ap.add_argument('inventory'); ap.add_argument('out_graphs'); ap.add_argument('out_classes')
ap.add_argument('--reps', type=int, default=32)
a = ap.parse_args()
G = {}
with gzip.open(a.data, 'rt') as f:
    for r in csv.DictReader(f):
        if r['L'] != '8':
            continue
        k = (r['sector'], int(r['graph']))
        d = G.setdefault(k, dict(share=0., kurt=[], xi={}, spp=[], pts={}))
        d['share'] += float(r['share']); d['kurt'].append(float(r['kurtosis'])); d['spp'].append(float(r['sec_per_point']))
        d['xi'][r['campaign']] = float(r['xi_hat']); d['pts'][r['campaign']] = int(r['points'])
inv = json.load(open(a.inventory))
prim = {(s, x['id']) for s in ('free', 'power') for x in inv[s]['8'] if x.get('primitive')}
pilot_screen = {}
for k, d in G.items():
    testable = min(d['pts'].values()) >= 32768
    m = (d['xi']['a'] + d['xi']['b']) / 2
    d['xim'] = m; d['cls'] = 'confirmed' if testable and m > 0.44 else ('cleared' if testable else 'untestable')
rng = np.random.default_rng(20261007)
pick = {}


def take(name, keys):
    for k in keys:
        if k not in pick:
            pick[k] = name


def top(pred, key, n, rev=True):
    ks = sorted([k for k, d in G.items() if pred(k, d) and k not in pick], key=lambda k: key(G[k]), reverse=rev)
    return ks[:n]


cf = lambda k, d: k[0] == 'free' and d['cls'] == 'confirmed'
take('conf_free', top(cf, lambda d: d['share'], 8))
rest = sorted([k for k, d in G.items() if cf(k, d) and k not in pick], key=lambda k: G[k]['xim'])
for q in (0.02, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0):
    take('conf_free', [rest[min(len(rest) - 1, int(q * (len(rest) - 1)))]])
cp = lambda k, d: k[0] == 'power' and d['cls'] == 'confirmed'
take('conf_power', top(cp, lambda d: d['share'], 4)); take('conf_power', top(cp, lambda d: d['xim'], 4))
up = lambda k, d: k[0] == 'power' and d['cls'] == 'untestable'
take('untest_power', top(up, lambda d: d['share'], 8))
pool = sorted([k for k, d in G.items() if up(k, d) and k not in pick and k[1] not in (12233, 12210)], key=lambda k: G[k]['xim'])
for t in range(3):
    part = pool[t * len(pool) // 3:(t + 1) * len(pool) // 3]
    take('untest_power', [part[i] for i in rng.choice(len(part), 2, replace=False)])
take('untest_power', [('power', 12233), ('power', 12210)])
take('control_free_never', top(lambda k, d: k[0] == 'free' and d['cls'] == 'cleared' and max(d['xi'].values()) < 0.3 and k not in prim, lambda d: d['share'], 2))
take('control_free_cleared', top(lambda k, d: k[0] == 'free' and d['cls'] == 'cleared' and max(d['xi'].values()) > 0.38, lambda d: d['share'], 2))
take('control_power_cleared', top(lambda k, d: k[0] == 'power' and d['cls'] == 'cleared', lambda d: d['share'], 2))
take('control_free_primitive', top(lambda k, d: k[0] == 'free' and k in prim, lambda d: d['share'], 2))
big = set()
big |= set(sorted([k for k in pick if pick[k] == 'conf_free'], key=lambda k: -G[k]['share'])[:3])
big |= set(sorted([k for k in pick if pick[k] == 'conf_free' and k not in big], key=lambda k: -G[k]['xim'])[:1])
big |= set(sorted([k for k in pick if pick[k] == 'conf_power'], key=lambda k: -G[k]['share'])[:2])
big |= set(sorted([k for k in pick if pick[k] == 'untest_power'], key=lambda k: -G[k]['share'])[:1])
big.add(('power', 12233))
tot = 0.
with open(a.out_graphs, 'w') as fg, open(a.out_classes, 'w') as fc:
    fg.write('# sector L graph nmax   (tc_choose.py)\n'); fc.write('# sector graph class share xi_mean kurt_max sec_per_point nmax core_h(both rates)\n')
    for k in sorted(pick, key=lambda k: (pick[k], k)):
        d = G[k]; n = 2 ** 19 if k in big else 2 ** 17
        ch = n * a.reps * 2 * float(np.mean(d['spp'])) / 3600; tot += ch
        fg.write(f'{k[0]} 8 {k[1]} {n}\n')
        fc.write(f'{k[0]} {k[1]} {pick[k]} {d["share"]:.3e} {d["xim"]:.3f} {max(d["kurt"]):.2f} {np.mean(d["spp"]):.3e} {n} {ch:.2f}\n')
        print(f'{pick[k]:24s} {k[0]:5s} G{k[1]:<6d} share {d["share"]:.2e} xi {d["xim"]:.3f} kurt {max(d["kurt"]):6.2f} s/pt {np.mean(d["spp"]):.2e} nmax 2^{int(math.log2(n))} core-h {ch:.2f}')
print(f'{len(pick)} graphs; busy core-h at {a.reps} replicates per rate: {tot:.1f}')
