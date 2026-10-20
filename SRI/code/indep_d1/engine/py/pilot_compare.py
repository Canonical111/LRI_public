#!/usr/bin/env python3
"""Compare per-sector Laurent coefficients of the same sectors between pilot runs with different N.
usage: pilot_compare.py 'glob1' 'glob2' [channel]"""
import json, glob, math, sys
def persec(pattern):
    d = {}
    for f in glob.glob(pattern):
        r = json.load(open(f))
        lo = r['lo']
        for c, ch in r['channels'].items():
            for s in ch['per_sector']:
                for o, (v, e) in enumerate(s['value']):
                    d[(c, s['id'], lo + o)] = (v, e)
    return d
a, b = persec(sys.argv[1]), persec(sys.argv[2])
chans = sorted({k[0] for k in b})
for c in chans:
    secs = sorted({k[1] for k in b if k[0] == c} & {k[1] for k in a if k[0] == c})
    orders = sorted({k[2] for k in b if k[0] == c})
    print(f'channel {c}: {len(secs)} common sectors')
    for o in orders:
        ka = [(c, s, o) for s in secs if (c, s, o) in a]
        kb = [(c, s, o) for s in secs if (c, s, o) in b]
        va = sum(a[k][0] for k in ka); ea = math.sqrt(sum(a[k][1] ** 2 for k in ka))
        vb = sum(b[k][0] for k in kb); eb = math.sqrt(sum(b[k][1] ** 2 for k in kb))
        print(f'  e^{o:<3d} run1 {va: .12g} +- {ea:.1e}   run2 {vb: .12g} +- {eb:.1e}   diff {va - vb: .1e}')
