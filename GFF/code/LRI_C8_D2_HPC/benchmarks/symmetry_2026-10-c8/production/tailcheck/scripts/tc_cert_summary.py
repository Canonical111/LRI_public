#!/usr/bin/env python3
"""Summary of the multi-prime randomized cancellation verification (tc_cert.cpp v2 output; v1 records are read too)
per (sector, L) and per production tail class of the L8 graphs, with the union-bound error estimate.

  tc_cert_summary.py CERT.jsonl.gz PROD_TAILS.csv.gz OUT.json"""
import csv, gzip, json, math, sys
from collections import defaultdict
import numpy as np

R = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]


def lsum(v):
    if not v:
        return None
    m = max(v)
    return m + math.log10(sum(10 ** (x - m) for x in v))


by = {}
with gzip.open(sys.argv[2], 'rt') as f:
    for r in csv.DictReader(f):
        if r['L'] == '8' and r['status'] == 'defined':
            by.setdefault((r['sector'], int(r['graph'])), {})[r['campaign']] = (int(r['points']), float(r['xi_hat']))
cls = {}
for k, v in by.items():
    t = min(v['a'][0], v['b'][0]) >= 32768; m = (v['a'][1] + v['b'][1]) / 2
    cls[k] = ('confirmed' if t and m > 0.44 else ('cleared' if t else 'untestable'), m)
out = {'per_sector_L': {}, 'L8_by_tail_class': {}}
g = defaultdict(list)
for r in R:
    g[(r['sector'], r['L'])].append(r)
for (s, L), X in sorted(g.items()):
    out['per_sector_L'][f'{s} L{L}'] = dict(
        graphs=len(X), certified_finite_second_moment=sum(r['certified'] for r in X), bounded_both_rates=sum(r['bounded'] for r in X),
        legacy_rate_tables=sum(r['legacy_rates'] for r in X), rate_table_mismatches=sum(r['rate_mismatch'] for r in X),
        clamped_subsets=sum(r['clamped'] for r in X), clamped_tight=sum(r['tight'] for r in X), clamped_higher=sum(r['higher'] for r in X),
        cancellation_failures=sum(r['failures'] for r in X), structural_mismatches=sum(r['structural_mismatch'] for r in X),
        greedy_checks=sum(r['greedy_checked'] for r in X), greedy_failures=sum(r['greedy_fail'] for r in X),
        graphs_with_double_lift=sum(1 for r in X if r['clamped'] and r['max_orders_cancelled'] >= 2), raw_min=min(r['raw_min'] for r in X),
        min_bound_margin=[min(r['min_bound_margin_a'] for r in X), min(r['min_bound_margin_b'] for r in X)],
        min_second_margin=[min(r['min_second_margin_a'] for r in X), min(r['min_second_margin_b'] for r in X)],
        xi_bound_max=[max(r['xi_bound_a'] for r in X), max(r['xi_bound_b'] for r in X)], errors=sum(1 for r in X if r['error']),
        seconds=sum(r['seconds'] for r in X), series_subsets=sum(r['series_subsets'] for r in X),
        degenerate_retries=sum(r.get('degenerate_retries', 0) for r in X), trial_disagreements=sum(r.get('trial_disagreements', 0) for r in X),
        primes_per_graph=sorted({len(r.get('primes', [])) for r in X}), points_per_prime=sorted({r.get('points_per_prime', 1) for r in X}),
        max_degree_bound=max(r.get('max_degree_bound', 0) for r in X), max_height_bits=max(r.get('max_height_bits') or 0 for r in X),
        log10_err_max=max((r['log10_err_max'] for r in X if r.get('log10_err_max') is not None), default=None),
        log10_err_sum=lsum([r['log10_err_sum'] for r in X if r.get('log10_err_sum') is not None]))
cg = defaultdict(list)
for r in R:
    if r['L'] == 8:
        c = cls.get((r['sector'], r['id']))
        cg[(r['sector'], c[0] if c else 'not in production')].append((r, c[1] if c else None))
for (s, c), X in sorted(cg.items()):
    rr = [x[0] for x in X]
    out['L8_by_tail_class'][f'{s} {c}'] = dict(
        graphs=len(rr), certified=sum(r['certified'] for r in rr), bounded=sum(r['bounded'] for r in rr),
        clamped_median=float(np.median([r['clamped'] for r in rr])), tight_median=float(np.median([r['tight'] for r in rr])),
        double_lift_fraction=float(np.mean([r['max_orders_cancelled'] >= 2 for r in rr])), terms_median=float(np.median([r['terms'] for r in rr])))
# association of the production Hill index with the certificate's structure (L8)
for s in ('free', 'power'):
    X = [(r, cls[(s, r['id'])][1]) for r in R if r['L'] == 8 and r['sector'] == s and (s, r['id']) in cls]
    xi = np.array([x[1] for x in X])
    from scipy.stats import spearmanr
    out[f'spearman_xi_vs_structure_{s}'] = {f: float(spearmanr(xi, [x[0][f] for x in X]).correlation) for f in ('clamped', 'tight', 'higher', 'terms', 'monomials', 'basis_entries')}
out['union_error_bound_log10'] = lsum([r['log10_err_sum'] for r in R if r.get('log10_err_sum') is not None])
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print('union error bound over all expanded subsets: 10^%.1f' % out['union_error_bound_log10'] if out['union_error_bound_log10'] is not None else 'no error bound (v1 records)')
for k, v in out['per_sector_L'].items():
    print(k, v)
for k, v in out['L8_by_tail_class'].items():
    print(k, v)
for s in ('free', 'power'):
    print(s, out[f'spearman_xi_vs_structure_{s}'])
