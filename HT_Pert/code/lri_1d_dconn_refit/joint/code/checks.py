#!/usr/bin/env python3
"""Side checks for the joint-model lens.
(a) exact44: fits with hi <= 44 only, where every dC (k = 4..8) is exact (S10 / reconciled), so no delta-model value
    enters; paired intercept shifts dconn - raw at hi = 40, 44 compared with the shifts at hi = 92 (modelled dC beyond 44).
(b) precision: the 40 worst-conditioned members of the corrected hi=92 prior-criterion ensemble re-fitted at 512 bits.
(c) fixed omega6: C8 with omega6 fixed at -1.10, -1.15, -1.20, -1.25e7 instead of fitted, for the floor-level-ish
    fixed-omega bases (dconn, hi 92, th118 and same windows).
Output: out/<run>/checks.json"""
import sys, json, itertools, time
sys.dont_write_bytecode = True
import numpy as np
import fitcore as F
from data import load as dload
from tab import load as tload, sel, REF, summ
from scan import spec_of, BASES, MODES, SHIFTS, GAPS

rd = sys.argv[1] if len(sys.argv) > 1 else '../out/run1'
D = dload(with_perts=False)
L = D['L']
out = {}
t0 = time.time()
# ---------------------------------------------------------------- (a) exact44
rows = []
for ds, hi, lo, b, mode, sh, gap in itertools.product(('raw', 'dconn'), (40, 44), (12, 16, 20, 24), BASES, MODES, SHIFTS, GAPS):
    c = dict(base=b, mode=mode)
    try:
        r = F.fit(L, D[ds], lo, hi, spec_of(c), sh, F.GAPS[gap], maxorder=8, free_orders=((5, 6, 7) if mode == 'free' else ()))
    except (ValueError, ZeroDivisionError):
        continue
    o = r['orders']
    rows.append(dict(ds=ds, hi=hi, lo=lo, base=b, mode=mode, sh=sh, gap=gap, **{f'C{n}': o[n]['lim'] for n in range(4, 9)},
                     rms8=o[8]['rms'], dof8=o[8]['npts'] - o[8]['ncol'], cond8=o[8]['cond']))
print(f'exact44 fits: {len(rows)} ({time.time() - t0:.0f}s)', flush=True)
key = lambda r: (r['hi'], r['lo'], r['base'], r['mode'], r['sh'], r['gap'])
R = {key(r): r for r in rows if r['ds'] == 'raw'}
P = [(R[key(r)], r) for r in rows if r['ds'] == 'dconn' and key(r) in R]
ex = {}
for hi in (40, 44):
    for mode in ('fixed', 'free', 'FL', 'FL5', None):
        pp = [(a, b) for a, b in P if a['hi'] == hi and (mode is None or a['mode'] == mode) and b['dof8'] >= 2]
        ex[f'{hi}_{mode}'] = {f'dC{n}': summ([b[f'C{n}'] - a[f'C{n}'] for a, b in pp]) for n in range(4, 9)}
        e = ex[f'{hi}_{mode}']
        print(f'hi={hi} {str(mode):5s} n={len(pp)} paired dconn-raw: ' + ' '.join(f"dC{n} {e[f'dC{n}']['median']:+.4g} [{e[f'dC{n}']['p16']:+.3g},{e[f'dC{n}']['p84']:+.3g}]" for n in range(4, 9)))
    dc = [r for r in rows if r['ds'] == 'dconn' and r['hi'] == hi and r['dof8'] >= 2]
    ex[f'{hi}_dconn_C'] = {f'C{n}': summ([r[f'C{n}'] for r in dc]) for n in range(4, 9)}
    print(f'hi={hi} dconn intercepts (all fits, dof8>=2): ' + ' '.join(f"C{n} med {ex[f'{hi}_dconn_C'][f'C{n}']['median']:.6g}" for n in range(4, 9)))
# compare with hi=92 paired shifts from the scan
T = tload(rd)
mr = sel(T, kind='o8', ds='raw', hi=92, low='same'); md = sel(T, kind='o8', ds='dconn', hi=92, low='same')
kf = lambda m: {(T['lo'][i], T['base'][i], T['mode'][i], T['sh'][i], T['gap'][i]): i for i in np.where(m)[0]}
kr, kd = kf(mr), kf(md)
cc = [c for c in kr if c in kd and c[0] <= 24]
ex['92_same_lo<=24'] = {f'dC{n}': summ([T[f'C{n}'][kd[c]] - T[f'C{n}'][kr[c]] for c in cc]) for n in range(4, 9)}
e = ex['92_same_lo<=24']
print(f'hi=92 same-window lo<=24 n={len(cc)} paired: ' + ' '.join(f"dC{n} {e[f'dC{n}']['median']:+.4g} [{e[f'dC{n}']['p16']:+.3g},{e[f'dC{n}']['p84']:+.3g}]" for n in range(4, 9)))
out['exact44'] = ex

# ---------------------------------------------------------------- (b) precision
m = sel(T, kind='o8', ds='dconn', hi=92) & (T['stat8'] <= 1000) & (T['lo'] >= 24) & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4)
ii = np.where(m)[0]
worst = ii[np.argsort(-np.nan_to_num(T['cond8'][ii]))[:40]]
prec = []
for i in worst:
    c = {k: T[k][i] for k in ('lo', 'hi', 'base', 'mode', 'sh', 'gap', 'low')}
    kw = dict(maxorder=8, free_orders=((5, 6, 7) if c['mode'] == 'free' else ()), hi_low=(118 if c['low'] == 'th118' else None))
    res = {}
    for bits in (256, 512):
        F.set_prec(bits)
        res[bits] = F.fit(L, D['dconn'], int(c['lo']), int(c['hi']), spec_of(c), float(c['sh']), F.GAPS[c['gap']], **kw)['lim']
    prec.append(dict(cond8=float(T['cond8'][i]), maxreldiff=max(abs(res[256][n] - res[512][n]) / abs(res[512][n]) for n in range(4, 9)),
                     dC8=res[256][8] - res[512][8]))
F.set_prec(256)
out['precision'] = dict(n=len(prec), max_cond8=max(p['cond8'] for p in prec), max_reldiff=max(p['maxreldiff'] for p in prec),
                        max_abs_dC8=max(abs(p['dC8']) for p in prec))
print('precision 256 vs 512 bits on the 40 worst-conditioned ensemble members:', out['precision'], flush=True)

# ---------------------------------------------------------------- (c) fixed omega6
fw = []
W6 = (-1.10e7, -1.15e7, -1.20e7, -1.25e7)
for low, lo, b, mode in itertools.product(('same', 'th118'), (32, 40, 50), ('B', 'D', 'Dj', 'E', 'F', 'S', 'E+L075', 'D+L075'), ('fixed', 'FL')):
    c = dict(base=b, mode=mode)
    kw = dict(maxorder=8, hi_low=(118 if low == 'th118' else None))
    r0 = F.fit(L, D['dconn'], lo, 92, spec_of(c), 0., F.OMEGA_EXT, **kw)
    row = dict(low=low, lo=lo, base=b, mode=mode, C8free=r0['lim'][8], om6=r0['omega'][6], rms8free=r0['orders'][8]['rms'])
    for w6 in W6:
        r = F.fit(L, D['dconn'], lo, 92, spec_of(c), 0., F.OMEGA_EXT, fixed_omega6=w6, **kw)
        row[f'C8_{w6:.3g}'] = r['lim'][8]; row[f'rms8_{w6:.3g}'] = r['orders'][8]['rms']
    row['slope_per_1e5'] = float(np.polyfit(W6, [row[f'C8_{w:.3g}'] for w in W6], 1)[0] * 1e5)
    fw.append(row)
out['fixed_omega6'] = fw
sl = np.array([r['slope_per_1e5'] for r in fw]); om = np.array([r['om6'] for r in fw])
print(f'fixed omega6: dC8/domega6 per 1e5 median {np.median(sl):.0f} [{np.percentile(sl, 16):.0f},{np.percentile(sl, 84):.0f}]; fitted omega6 median {np.median(om):.4g} [{np.percentile(om, 16):.4g},{np.percentile(om, 84):.4g}]')
json.dump(out, open(f'{rd}/checks.json', 'w'), indent=1, default=float)
print(f'done {time.time() - t0:.0f}s')
