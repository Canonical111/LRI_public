#!/usr/bin/env python3
"""refit72: 256- vs 512-bit check of the weighted (dconn_w) fits: the 20 worst-conditioned members of the hi=92 prior-criterion
ensemble (stat8<=1000, lo>=24, whitened rms8<=1.125e-7, dof8>=4). usage: check_prec_w.py SCAN_O8_W.jsonl.gz"""
import sys, gzip, json
sys.dont_write_bytecode = True
import numpy as np
import fitcore as F
from data import load
from scan import spec_of
rows = []
for l in gzip.open(sys.argv[1], 'rt'):
    r = json.loads(l)
    if 'err' in r or r['ds'] != 'dconn_w' or r['hi'] != 92 or r['lo'] < 24:
        continue
    o = r['o']['8']
    if o[4] <= 1000 and o[7] <= 1.125e-7 and o[5] - o[6] >= 4:
        rows.append((o[2], r))
rows.sort(key=lambda x: -x[0])
D = load(with_perts=False); L = D['L']
mx = 0.; md8 = 0.
for cond, r in rows[:20]:
    res = {}
    for bits in (256, 512):
        F.set_prec(bits)
        res[bits] = F.fit(L, D['dconn'], r['lo'], r['hi'], spec_of(r), r['sh'], F.GAPS[r['gap']], maxorder=8,
                          free_orders=((5, 6, 7) if r['mode'] == 'free' else ()), hi_low=(118 if r['low'] == 'th118' else None), wfit=D['wrel'])['lim']
    mx = max(mx, max(abs(res[256][n] - res[512][n]) / abs(res[512][n]) for n in range(4, 9)))
    md8 = max(md8, abs(res[256][8] - res[512][8]))
    assert abs(res[256][8] - r['lim']['8']) <= 1e-9 * abs(r['lim']['8']), (res[256][8], r['lim']['8'])
print(f'weighted fits: {len(rows)} in ensemble; 20 worst-conditioned (cond8 {rows[0][0]:.1e}..{rows[19][0]:.1e}): max rel diff 256 vs 512 bits {mx:.1e}, max |dC8| {md8:.1e}; 256-bit refit reproduces the scan')
