#!/usr/bin/env python3
"""Pass/fail check of a full tc_cert (v2) run over the inventory, and its aggregate error bound.

  tc_cert_check.py MEMBERS.txt CERT.jsonl CERT_EXIT OUT.json [--expect 24173] [--primes 4] [--points 2]

Fails (exit 1) unless ALL of these hold:
  * tc_cert exited 0, the member list holds --expect lines, and the records are exactly the members: one record per
    (sector, L, id), none missing, none extra, none duplicated;
  * every record: no error, certified (finite second moment at both rates), no rate-table mismatch, no cancellation
    failure, no structural mismatch, no greedy failure, --primes distinct primes in [2^61, 2^62) (re-tested here with
    a deterministic Miller-Rabin) and --points points per prime;
  * every L7 and L8 record is bounded at both rates with a builder (half-integer) rate table; the legacy
    (non-half-integer) tables are exactly the free L <= 6 ones;
  * the union-bound error estimate sum over all graphs of 10^log10_err_sum is below 1e-30.
Reports: counts per (sector, L), the minimum margins of the L7/L8 records, point redraws (degenerate_retries),
trial disagreements (subsets where the K*J trials did not all find the same lowest order: an accidental zero at some
trial, harmless because the minimum is taken), the largest degree and height bounds, and the aggregate error bound."""
import argparse, json, math, sys
from collections import Counter, defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('members'); ap.add_argument('cert'); ap.add_argument('code', type=int); ap.add_argument('out')
ap.add_argument('--expect', type=int, default=24173); ap.add_argument('--primes', type=int, default=4); ap.add_argument('--points', type=int, default=2)
a = ap.parse_args()


def is_prime(n):
    if n < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % q == 0:
            return n == q
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2; r += 1
    for b in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):  # deterministic below 3.3e24
        x = pow(b, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


problems = []
mem = [tuple(l.split()[:3]) for l in open(a.members) if l.strip()]
recs = [json.loads(l) for l in open(a.cert)]
if a.code != 0:
    problems.append(f'tc_cert exit {a.code}')
if len(mem) != a.expect:
    problems.append(f'{len(mem)} members, expected {a.expect}')
keys = [(r['sector'], str(r['L']), str(r['id'])) for r in recs]
dup = [k for k, n in Counter(keys).items() if n > 1]
missing = sorted(set(mem) - set(keys)); extra = sorted(set(keys) - set(mem))
if len(recs) != len(mem) or dup or missing or extra:
    problems.append(f'records {len(recs)} vs members {len(mem)}; duplicated {dup[:5]}, missing {missing[:5]}, extra {extra[:5]}')
lo, hi = 1 << 61, 1 << 62
bad = Counter()
per = defaultdict(Counter)
lsum = -math.inf; lmax = -math.inf
mins = dict(min_bound_margin_a=9e9, min_bound_margin_b=9e9, min_second_margin_a=9e9, min_second_margin_b=9e9)
prime_tests = 0
for r in recs:
    k = (r['sector'], r['L'])
    per[k]['graphs'] += 1; per[k]['certified'] += r['certified']; per[k]['bounded'] += r['bounded']; per[k]['legacy'] += r['legacy_rates']
    for f in ('clamped', 'tight', 'higher', 'series_subsets', 'degenerate_retries', 'trial_disagreements', 'failures', 'rate_mismatch', 'structural_mismatch', 'greedy_fail', 'greedy_checked'):
        per[k][f] += r[f]
    per[k]['double_lift'] += r['clamped'] > 0 and r['max_orders_cancelled'] >= 2
    if r['error']:
        bad['error'] += 1
    if not r['certified']:
        bad['not certified'] += 1
    for f in ('rate_mismatch', 'failures', 'structural_mismatch', 'greedy_fail'):
        if r[f]:
            bad[f] += 1
    P = [int(x) for x in r['primes']]
    if len(P) != a.primes or len(set(P)) != a.primes or not all(lo <= p < hi for p in P) or r['points_per_prime'] != a.points:
        bad['primes/points'] += 1
    else:
        for p in P:
            prime_tests += 1
            if not is_prime(p):
                bad['composite prime'] += 1
    if r['L'] >= 7:
        if not r['bounded'] or r['legacy_rates']:
            bad['L7/L8 not bounded or legacy'] += 1
        for f in mins:
            mins[f] = min(mins[f], r[f])
    if r['legacy_rates'] != (r['sector'] == 'free' and r['L'] <= 6):
        bad['legacy set'] += 1
    if r['log10_err_sum'] is not None:
        x = r['log10_err_sum']; lsum = x if lsum == -math.inf else max(lsum, x) + math.log10(1 + 10 ** (-abs(lsum - x)))
        lmax = max(lmax, r['log10_err_max'])
for k, n in bad.items():
    problems.append(f'{n} records: {k}')
if not lsum < -30:
    problems.append(f'aggregate error bound 10^{lsum:.1f} is not below 1e-30')
doc = dict(passed=not problems, problems=problems, tc_cert_exit=a.code, members=len(mem), records=len(recs), primes_per_graph=a.primes, points_per_prime=a.points,
           primes_retested=prime_tests,
           per_sector_L={f'{s} L{L}': dict(v) for (s, L), v in sorted(per.items())},
           totals={f: sum(v[f] for v in per.values()) for f in ('graphs', 'certified', 'bounded', 'legacy', 'clamped', 'tight', 'higher', 'series_subsets',
                                                             'degenerate_retries', 'trial_disagreements', 'failures', 'rate_mismatch', 'structural_mismatch',
                                                             'greedy_checked', 'greedy_fail', 'double_lift')},
           min_margins_L7_L8=mins, max_degree_bound=max(r['max_degree_bound'] for r in recs), max_height_bits=max(r['max_height_bits'] or 0 for r in recs),
           log10_error_bound_per_subset_max=lmax, log10_error_bound_union=lsum,
           error_model=('P(any expanded subset gets a wrong lowest order) <= sum_S (beta_S + delta_S^J)^K: beta_S = ceil(B_S/61)/(3.8e16 - K) bounds a bad prime '
                        '(B_S a log2 height bound of the cleared coefficient polynomial), delta_S = d_S/((2^61-2)(1-gamma)) the Schwartz-Zippel bound at a '
                        'good prime (d_S a degree bound); assumes the generator draws behave as independent uniform draws'))
json.dump(doc, open(a.out, 'w'), indent=1)
for k, v in doc['per_sector_L'].items():
    print(k, v)
print('totals', doc['totals'])
print('min margins L7/L8', mins, 'max degree', doc['max_degree_bound'], 'max height bits', round(doc['max_height_bits'], 1))
print(f'error bound: per subset <= 10^{lmax:.1f}, union over all expanded subsets <= 10^{lsum:.1f}')
print('PASSED' if not problems else 'FAILED: ' + '; '.join(problems))
sys.exit(0 if not problems else 1)
