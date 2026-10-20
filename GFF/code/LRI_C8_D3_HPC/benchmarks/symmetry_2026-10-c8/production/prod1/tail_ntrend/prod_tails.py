#!/usr/bin/env python3
"""Per L8 graph and campaign: the production's replicate-mean Hill index of the merged top 16 (exactly
tools/assemble.py hill/tail_monitor: a zero tail_sum or an undefined Hill in any replicate makes the entry undefined),
with the per-replicate point counts and the replicate count. Streams each group's graph_tails.csv.

  prod_tails.py RUN OUT.csv
"""
import csv, math, sys
from pathlib import Path

TAIL_K = 16


def hill(top):
    if len(top) < TAIL_K:
        return None
    x = [float(v) for v in top]
    if x[-1] <= 0 or not all(math.isfinite(v) for v in x):
        return None
    return sum(math.log(v / x[-1]) for v in x[:-1]) / (TAIL_K - 1)


def main(run, out):
    rows = []
    for c in ('a', 'b'):
        for s in ('free', 'power'):
            p = Path(run) / 'groups' / f'{c}_{s}_L8' / 'graph_tails.csv'
            per = {}
            with p.open() as f:
                for r in csv.DictReader(f):
                    g = int(r['graph'])
                    top = [r[f'tail_top_{i+1}'] for i in range(TAIL_K) if r.get(f'tail_top_{i+1}')]
                    h = None if float(r['tail_sum']) == 0 else hill(top)
                    e = per.setdefault(g, {'h': [], 'n': []})
                    e['h'].append(h)
                    e['n'].append(int(r['points']))
            for g, e in per.items():
                xi = None if any(v is None for v in e['h']) else sum(e['h']) / len(e['h'])
                rows.append((c, s, g, '' if xi is None else repr(xi), len(e['h']), min(e['n']), max(e['n'])))
            print(f'{c}_{s}_L8: {len(per)} graphs', flush=True)
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['campaign', 'sector', 'graph', 'xi', 'replicates', 'points_min', 'points_max'])
        w.writerows(sorted(rows))
    print(f'wrote {len(rows)} rows to {out}', flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:3])
