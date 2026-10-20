#!/usr/bin/env python3
"""Compare the finite-sample formula (regularized Horn blocks) with the spectral <t^2 R_tau>_d at real tau."""
import sys, time, json
import mpmath as mp
import rblocks as rb
from spec_R import tR_spec

mp.mp.dps = 30
cases = [('1.5', '0.2'), ('2.5', '0.1'), ('2.5', '0.4'), ('2.75', '0.6'), ('2.75', '0.2'), ('3', '0.3'), ('1.25', '0.15'), ('0.8', '0.15'), ('1', '0.3'), ('2', '0.3')]
if len(sys.argv) > 1:
    cases = [tuple(c.split(',')) for c in sys.argv[1:]]
out = []
for ds, ts in cases:
    d = mp.mpf(ds); tau = mp.mpf(ts); q = d / 4
    st = time.time()
    vb = rb.tR(q, tau, 14, 160)
    vb2 = rb.tR(q, tau, 12, 120)
    t1 = time.time()
    with mp.workdps(25):
        vs = tR_spec(d, tau, 24, 30)
    t2 = time.time()
    rec = dict(d=ds, tau=ts, blocks=mp.nstr(mp.re(vb), 28), blocks_lo=mp.nstr(mp.re(vb2), 28), spectral=mp.nstr(mp.re(vs), 24),
               diff=mp.nstr(abs(vb - vs), 3), conv=mp.nstr(abs(vb - vb2), 3), J=mp.nstr(mp.re(rb.Cfac(q, tau) * vb), 24),
               sec=[round(t1 - st, 1), round(t2 - t1, 1)])
    print(json.dumps(rec), flush=True)
    out.append(rec)
json.dump(out, open('compare_strip.json', 'w'), indent=1)
