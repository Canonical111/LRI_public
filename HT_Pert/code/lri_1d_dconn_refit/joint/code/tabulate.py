#!/usr/bin/env python3
"""Flatten scan_*.jsonl.gz into a column table (dict of numpy arrays, pickled) for analysis. Usage: tabulate.py RUNDIR"""
import sys, gzip, json, pickle
import numpy as np
rd = sys.argv[1]
rows = []
import glob
files = [f for kind in ('o8', 'o7') for f in [f'{rd}/scan_{kind}.jsonl.gz'] + sorted(glob.glob(f'{rd}/scan_{kind}_*.jsonl.gz'))]
print('files', files)
for fn in files:
    for line in gzip.open(fn, 'rt'):
        r = json.loads(line)
        if 'err' in r:
            continue
        f = {k: r[k] for k in ('kind', 'ds', 'hi', 'low', 'lo', 'base', 'mode', 'sh', 'gap')}
        for n, v in r['lim'].items():
            f[f'C{n}'] = v
        for k, v in r['om'].items():
            f[f'om{k}'] = v
        for n, v in r['o'].items():
            rms, mx, cond, gain, stat, npts, ncol = v[:7]
            erms, emax, statx = v[7:10] if len(v) >= 10 else (rms, mx, None)
            f.update({f'rms{n}': rms, f'max{n}': mx, f'cond{n}': cond, f'gain{n}': gain, f'stat{n}': stat, f'npts{n}': npts, f'ncol{n}': ncol,
                      f'erms{n}': erms, f'emax{n}': emax, f'statx{n}': statx})
        for k, v in r.get('e', {}).items():
            f['e_' + k] = v
        for k, v in r.get('P', {}).items():
            f['P_' + k] = v
        for k, v in r.get('v', {}).items():
            for s, x in zip(('min', 'p16', 'p50', 'p84', 'max', 'std'), v):
                f[f'v_{k}_{s}'] = x
        rows.append(f)
keys = sorted({k for r in rows for k in r})
T = {}
for k in keys:
    vals = [r.get(k) for r in rows]
    if all(isinstance(v, str) for v in vals):
        T[k] = np.array(vals, dtype=object)
    else:
        T[k] = np.array([np.nan if v is None else v for v in vals], dtype=float)
pickle.dump(T, open(f'{rd}/scan.pkl', 'wb'))
print(len(rows), 'rows', len(keys), 'cols')
