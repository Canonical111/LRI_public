#!/usr/bin/env python3
"""Regression check: the refit72 scan's raw and dconn_old rows must reproduce run1 (raw, dconn) bit for bit.
usage: regress_run1.py NEW_SCAN.jsonl.gz OLD_SCAN.jsonl.gz"""
import sys, gzip, json
new, old = sys.argv[1], sys.argv[2]
K = ('kind', 'hi', 'low', 'lo', 'base', 'mode', 'sh', 'gap')
ref = {}
for l in gzip.open(old, 'rt'):
    r = json.loads(l)
    if 'err' in r:
        continue
    ref[(r['ds'],) + tuple(r[k] for k in K)] = r
n = 0; md = 0.; mo = 0.; miss = 0; ne = {}
for l in gzip.open(new, 'rt'):
    r = json.loads(l)
    if r['ds'] not in ('raw', 'dconn_old'):
        continue
    key = ('raw' if r['ds'] == 'raw' else 'dconn',) + tuple(r[k] for k in K)
    if key not in ref:
        if 'err' not in r:
            ne[r['hi']] = ne.get(r['hi'], 0) + 1
        continue
    if 'err' in r:
        miss += 1; continue
    o = ref[key]; n += 1
    for k, v in o['lim'].items():
        md = max(md, abs(r['lim'][k] - v) / abs(v))
    for k, v in o['o'].items():
        mo = max(mo, max(abs(a - b) / max(abs(b), 1e-300) for a, b in zip(r['o'][k][:7], v) if a is not None and b is not None))
print(f'{new}: compared {n} rows (raw + dconn_old vs run1 raw + dconn); max rel dev intercepts {md:.1e}, fit stats {mo:.1e};'
      f' rows failing now but not in run1 {miss}; new rows by hi (not in run1) {ne}')
