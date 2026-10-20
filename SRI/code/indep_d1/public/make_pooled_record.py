#!/usr/bin/env python3
"""Build (or check) public/pooled_sector_record.json from the raw engine chunk outputs (new tool, 2026-10-15).

The raw outputs (engine/runs/<run>/*.cfg.json of the runs below, about 130 MB) are not shipped (DATA_indep_d1.md,
`make -f public.mk fetch-data`). For every job of these runs this tool calls the verbatim
assembly/pooled_errors.job_sector_values() twice (all coefficients; needed coefficients only) and stores, exactly,
  T_ir = sum_s x_isr            the per-replicate totals over the sectors,
  M_ij = sum_s cov_r(x_is, x_js) the sum over sectors of the sample covariance (R - 1 normalization),
from which public/pooled_shim.py reproduces pooled_errors.pooled_projection() for any gradient. Jobs with at most
SECTOR_LIMIT = 360 sectors (3 to 7 kinks, coefficients known to 1e-16..1e-10, where the double-precision projection
of the verbatim code is itself at the rounding level) also keep their per-sector replicate values, so that the verbatim
pooled_projection() runs on them unchanged. Doubles are converted
to integers (x * 2^S) so that T and M are exact before the final rounding to 25 significant digits.
--check SHIPPED compares a freshly built record with the shipped one (25-digit strings must agree to 1e-20 relative)
and checks the shim against the verbatim pooled_projection on the raw data (unit gradients on every coefficient of
every job, and three fixed pseudo-random gradients per job).

Usage (from code/indep_d1/, after fetch-data):
  python3 public/make_pooled_record.py --tree .work/raw/run --out .work/raw/pooled_sector_record.json \
      [--check public/pooled_sector_record.json]
--tree is a copy of this package whose engine/runs/<run>/ directories also hold the raw *.cfg.json files
(public/replay_indep.py --raw DIR builds it).
"""
import argparse
import importlib
import json
import math
import os
import random
import sys
import time
from fractions import Fraction

import mpmath as mp

SECTOR_LIMIT = 360       # jobs with at most this many sectors also keep their per-sector replicate values (exact path)
RUNS = ['prod_6digit', 'prod_6digit_topup1', 'poles1', 'c8tierA', 'c8tierA_topup1', 'c8tierB_s0.01_r1',
        'c8tierB_s0.01_can', 'c8tierB_s0.01_topup1', 'c8tierC_s3_r2', 'c8tierC_s3_can', 'c8tierC_s3_topup1']


def exact_stats(d):
    """d = {'R': R, 'sectors': {sid: {name: [x_r]}}} -> names, T (exact Fractions), M (exact Fractions)"""
    secs = d['sectors']
    names = []
    for vals in secs.values():
        for nm in vals:
            if nm not in names:
                names.append(nm)
    R = d['R']
    S = 0
    for vals in secs.values():
        for xs in vals.values():
            for x in xs:
                if x != 0.0:
                    S = max(S, 53 - math.frexp(x)[1])
    n = len(names)
    tot = [[0] * R for _ in range(n)]
    cov = [[0] * n for _ in range(n)]
    for vals in secs.values():
        X = []
        for nm in names:
            xs = vals.get(nm)
            if xs is None:
                raise RuntimeError(f'{nm} absent in a sector')
            row = []
            for x in xs:
                p, q = float(x).as_integer_ratio()
                row.append(p << (S - (q.bit_length() - 1)))
            X.append(row)
        sums = [sum(r) for r in X]
        for a in range(n):
            for t in range(R):
                tot[a][t] += X[a][t]
            for b in range(a, n):
                c = R * sum(X[a][t] * X[b][t] for t in range(R)) - sums[a] * sums[b]
                cov[a][b] += c
    den_t = 1 << S
    den_c = R * (R - 1) * (1 << (2 * S))
    T = [[Fraction(v, den_t) for v in row] for row in tot]
    M = [[Fraction(cov[min(a, b)][max(a, b)], den_c) for b in range(n)] for a in range(n)]
    return names, T, M


def s25(fr):
    with mp.workdps(40):
        return mp.nstr(mp.mpf(fr.numerator) / fr.denominator, 25, min_fixed=-5, max_fixed=5) if fr != 0 else '0'


def build(tree):
    sys.path.insert(0, os.path.join(tree, 'assembly'))
    PE = importlib.import_module('pooled_errors')
    out = {'about': 'Sector-pooled sufficient statistics of every engine job of the final runs (public/make_pooled_record.py; '
                    'read by public/pooled_shim.py). Per job: names = all coefficients of the job (all_coeffs=True), '
                    'need_names = the needed ones, R replicates, nsec sectors, T[i][r] = sum over sectors of the '
                    'replicate values, M[i][j] = sum over sectors of the replicate sample covariance; exact, rounded '
                    'to 25 significant digits. Built with the verbatim assembly/pooled_errors.job_sector_values().',
           'runs': {}}
    for run in RUNS:
        rd = os.path.join(tree, 'engine', 'runs', run)
        t0 = time.time()
        man = json.load(open(os.path.join(rd, 'manifest.json')))
        allj = PE.job_sector_values(rd, all_coeffs=True, allow_missing=True)
        needj = PE.job_sector_values(rd, all_coeffs=False, allow_missing=True)
        jobs, seen = [], set()
        for m in man:
            key = ('', m['moment'], m['job']['k'])
            if key in seen:
                continue
            seen.add(key)
            ent = {'moment': m['moment'], 'k': m['job']['k'], 'need': m.get('need') or []}
            if key not in allj:
                ent['missing'] = True
                jobs.append(ent)
                continue
            names, T, M = exact_stats(allj[key])
            need_names = []
            if key in needj:
                first = next(iter(needj[key]['sectors'].values()))
                need_names = [nm for nm in names if nm in first]
            ent.update({'R': allj[key]['R'], 'nsec': len(allj[key]['sectors']), 'names': names,
                        'need_names': need_names, 'T': [[s25(v) for v in row] for row in T],
                        'M': [[s25(v) for v in row] for row in M]})
            if len(allj[key]['sectors']) <= SECTOR_LIMIT:
                ent['sectors'] = [[sid, [[float(x) for x in vals[nm]] for nm in names]]
                                  for sid, vals in allj[key]['sectors'].items()]
            jobs.append(ent)
        out['runs'][run] = {'jobs': jobs}
        print(f'  {run}: {len(jobs)} jobs ({sum(1 for j in jobs if j.get("missing"))} without output) '
              f'{time.time() - t0:.1f} s', flush=True)
    return out, PE


def check(tree, built, shipped_path, PE):
    """built vs shipped record; shim vs verbatim pooled_projection on the raw data"""
    import pooled_shim as SH
    ok = True
    sh = json.load(open(shipped_path))
    worst = 0.0
    bad = []
    for run, r in built['runs'].items():
        a = r['jobs']
        b = sh['runs'].get(run, {}).get('jobs')
        if b is None or len(a) != len(b):
            bad.append(f'{run}: job list differs')
            continue
        for x, y in zip(a, b):
            for key in ('moment', 'k', 'need', 'missing', 'R', 'nsec', 'names', 'need_names', 'sectors'):
                if x.get(key) != y.get(key):
                    bad.append(f'{run}/{x["moment"]} k={x["k"]}: {key}')
            for key in ('T', 'M'):
                for u, v in zip(sum(x.get(key, []), []), sum(y.get(key, []), [])):
                    du, dv = mp.mpf(u), mp.mpf(v)
                    d = float(abs(du - dv) / max(abs(du), abs(dv), mp.mpf(10) ** -300))
                    worst = max(worst, d)
                    if d > 1e-20:
                        bad.append(f'{run}/{x["moment"]} k={x["k"]}: {key}')
    print(f'  built vs shipped record: {len(bad)} differences; largest relative difference of a 25-digit entry {worst:.1e}')
    ok &= not bad
    # shim vs verbatim projection on the raw per-sector data
    tmp = built['_path']
    orig_jsv, orig_pp = PE.job_sector_values, PE.pooled_projection
    SH.install(PE, tmp, log=lambda *a: None)
    rec_jsv, rec_pp = PE.job_sector_values, PE.pooled_projection
    PE.job_sector_values, PE.pooled_projection = orig_jsv, orig_pp
    rng = random.Random(20261015)
    w_unit = w_rand = w_rep = 0.0
    n = 0
    for run in RUNS:
        rd = os.path.join(tree, 'engine', 'runs', run)
        raw = orig_jsv(rd, all_coeffs=True, allow_missing=True)
        rec = rec_jsv(rd, all_coeffs=True, allow_missing=True)
        for key, d in raw.items():
            names = list(next(iter(d['sectors'].values())))
            grads = [{nm: 1.0} for nm in names]
            for _ in range(3):
                grads.append({nm: rng.uniform(-1, 1) * 10 ** rng.uniform(-3, 3) for nm in names})
            for gi, g in enumerate(grads):
                r0, p0, _ = orig_pp({key: d}, g)
                r1, p1, _ = rec_pp({key: rec[key]}, g)
                if p0 == 0 and p1 == 0:
                    continue
                dp = abs(p1 - p0) / max(p0, 1e-300)
                dr = abs(r1 - r0) / max(r0, 1e-300)
                if gi < len(names):
                    w_unit = max(w_unit, dp)
                else:
                    w_rand = max(w_rand, dp)
                w_rep = max(w_rep, dr)
                n += 1
    print(f'  shim vs verbatim pooled_projection on the raw data: {n} projections; largest relative difference '
          f'pool (unit gradients) {w_unit:.1e}, pool (random gradients) {w_rand:.1e}, rep {w_rep:.1e}')
    ok &= w_unit < 1e-12
    return ok, {'n_differences': len(bad), 'worst_entry': worst, 'n_projections': n, 'pool_unit': w_unit,
                'pool_random': w_rand, 'rep': w_rep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--check', default=None)
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    t0 = time.time()
    rec, PE = build(os.path.abspath(a.tree))
    json.dump(rec, open(a.out, 'w'), indent=0, separators=(',', ':'))
    print(f'wrote {a.out} ({os.path.getsize(a.out) / 1e6:.2f} MB, {time.time() - t0:.0f} s)')
    if a.check:
        rec['_path'] = a.out
        ok, summ = check(os.path.abspath(a.tree), rec, a.check, PE)
        json.dump(summ, open(a.out.replace('.json', '_check.json'), 'w'), indent=1)
        print('RECORD CHECK', 'PASSED' if ok else 'FAILED')
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
