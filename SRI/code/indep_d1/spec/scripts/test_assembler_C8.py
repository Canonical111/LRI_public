#!/usr/bin/env python3
"""Regression test of assemble_from_raw_C8.py on SYNTHETIC data (archive-free, ~20 s; exit 0 = pass).
  1. complete random data (tight + below-bound zeros + genuine extras; exact two-kink filled): --windows both passes,
     C8 = B_old + linear part equals 8 T4 (literal polynomial);
  2. the 25 old inputs and C3..C7 equal the phase-1 assembler on the same data;
  3. a missing new scalar (A9_base [eps^0 l^1]) raises MissingCoefficient naming it;
  4. a non-zero below-bound scalar makes --windows both fail;
  5. --windows tight needs no below-bound scalar;
  6. data violating the tree normalization C3_1[v0d0] = 5 are rejected.
"""
import copy, random, sys
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assemble_from_raw as A1          # noqa: E402
import assemble_from_raw_C8 as A8       # noqa: E402

mp.mp.dps = 40
random.seed(20261003)
tight, below, genuine = A8.requirements()
raw = {}
for a, p, k in tight + genuine:
    raw.setdefault(a, {}).setdefault(str(p), {})[str(k)] = repr(random.uniform(-1, 1))
for a, p, k in below:
    raw.setdefault(a, {}).setdefault(str(p), {})[str(k)] = '0'
# exact two-kink atoms overwrite the random ones
for a in list(raw):
    if a.split('_')[0] in ('Z2', 'Q2', 'EZ2', 'EQ2'):
        del raw[a]
raw['A3_base']['0']['1'] = '6'          # C3_1[v0d0] = 5: the tree normalization the invariant algebra assumes (note l.550)
A8.fill_two_kink(raw)
fails = []
res, ok = A8.run(copy.deepcopy(raw), 'both', 40)
if not ok:
    fails.append(f'1: full run failed {res["checks"]}')
if not res['checks'].get('C8_equals_8T4'):
    fails.append('1: C8 != 8 T4')
# phase-1 assembler on the same data (it needs only its own subset)
r1, ok1 = A1.run(copy.deepcopy(raw), 'both', 40)
d = max(abs(mp.mpf(r1['inputs'][k]) - mp.mpf(res['inputs'][k])) for k in r1['inputs'])
d = max(d, max(abs(mp.mpf(r1['invariants'][k]) - mp.mpf(res['invariants'][k])) for k in ('C5', 'C6', 'D4', 'C7')))
if not ok1 or d > mp.mpf(10)**-30:
    fails.append(f'2: phase-1 assembler differs by {mp.nstr(d, 3)} (ok1={ok1})')
# 3. missing scalar
r3 = copy.deepcopy(raw)
del r3['A9_base']['0']['1']
try:
    A8.run(r3, 'both', 40)
    fails.append('3: missing A9_base [eps^0 l^1] not detected')
except A8.MissingCoefficient as e:
    if 'A9_base [eps^0 l^1]' not in str(e):
        fails.append(f'3: wrong message {e}')
# 4. non-zero below-bound scalar
r4 = copy.deepcopy(raw)
a, p, k = below[0]
r4[a][str(p)][str(k)] = '0.5'
_, ok4 = A8.run(r4, 'both', 40)
if ok4:
    fails.append(f'4: non-zero below-bound {a} [eps^{p} l^{k}] not flagged')
# 5. tight mode without the below-bound scalars
r5 = copy.deepcopy(raw)
for a, p, k in below:
    if a.split('_')[0] not in ('Z2', 'Q2', 'EZ2', 'EQ2'):
        del r5[a][str(p)][str(k)]
try:
    _, ok5 = A8.run(r5, 'tight', 40)
    if not ok5:
        fails.append('5: tight run failed')
except A8.MissingCoefficient as e:
    fails.append(f'5: tight mode demanded {e}')
r6 = copy.deepcopy(raw)
r6['A3_base']['0']['1'] = '6.5'
_, ok6 = A8.run(r6, 'both', 40)
if ok6:
    fails.append('6: C3_1 != 5 not flagged')
print('tight scalars', len(tight), 'below-bound', len(below), 'genuine extras', len(genuine))
print('C8 (synthetic)', res['invariants']['C8'][:30], ' C8 - 8T4', res['invariants']['C8_minus_8T4'][:12],
      ' max |phase1 - C8 assembler|', mp.nstr(d, 3))
print('FAILURES:' if fails else 'ALL PASS', fails)
sys.exit(1 if fails else 0)
