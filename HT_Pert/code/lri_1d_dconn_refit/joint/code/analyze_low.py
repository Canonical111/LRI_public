#!/usr/bin/env python3
"""C4..C7 from the joint linked model on raw and on fully corrected (dconn) data, kind o7 (orders 4..7 on [lo, hi]).
No calibration: references are only compared. Output: out/<run>/low_summary.json + printed tables."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
from tab import *

rd = sys.argv[1] if len(sys.argv) > 1 else '../out/run1'
DS = sys.argv[2] if len(sys.argv) > 2 else 'dconn'          # refit72: corrected dataset analysed (dconn, dconn_s46, dconn_old)
SUF = ('' if DS == 'dconn' else '_' + DS) + ('' if RMSKEY == 'erms' else '_' + RMSKEY + 'crit')
T = load(rd)
print('corrected dataset', DS, 'criteria rms key', T['rmsc4'] is T['erms4'] and 'erms' or 'see tab.RMSKEY')
out = {}
o7 = sel(T, kind='o7')

# ---------------------------------------------------------------- (1) pre-registered reference fits
print('== (1) pre-registered reference fits: A/B/C, lo=16, shift 0, ext gap, fixed omegas (misses vs references)')
pre = {}
for ds in ('raw', DS):
    for b in ('A', 'B', 'C'):
        for hi in (50, 118):
            m = o7 & sel(T, ds=ds, base=b, lo=16, hi=hi, mode='fixed', sh=0., gap='ext')
            i = np.where(m)[0][0]
            pre[f'{ds}_{b}_{hi}'] = {f'C{n}': T[f'C{n}'][i] for n in range(4, 8)}
            print(f'{ds:5s} {b} 16-{hi:3d}: ' + ' '.join(f"C{n} {T[f'C{n}'][i]:.6g} ({T[f'miss{n}'][i]:+.4g})" for n in range(4, 8)))
        a, c = pre[f'{ds}_{b}_50'], pre[f'{ds}_{b}_118']
        print(f'      window drift 50->118: C4 {abs(c["C4"] - a["C4"]) / REF[4]:.2e} (crit 2e-4)  C5 {abs(c["C5"] - a["C5"]) / abs(REF[5]):.2e} (crit 5e-4)')
out['prereg'] = pre

# ---------------------------------------------------------------- (2) basis x mode table at hi=118
print('\n== (2) hi=118, shift 0, ext gap: misses C4 C5 C6 C7 per basis and mode (dconn); floor flags 4..7')
tab2 = {}
for lo in (40, 50, 60, 70):
    for mode in ('fixed', 'free', 'FL', 'FL5'):
        line = f'lo={lo} {mode:5s}'
        for b in ('A', 'B', 'C', 'Dj', 'D', 'E', 'F'):
            m = o7 & sel(T, ds=DS, base=b, lo=lo, hi=118, mode=mode, sh=0., gap='ext')
            i = np.where(m)[0][0]
            tab2[f'{lo}_{mode}_{b}'] = {f'miss{n}': T[f'miss{n}'][i] for n in range(4, 8)}
            tab2[f'{lo}_{mode}_{b}'].update(ok={n: bool(T[f'ok{n}'][i]) for n in range(4, 8)})
        print(line + ' | ' + ' | '.join(f"{b}: {tab2[f'{lo}_{mode}_{b}']['miss4']:+.4f} {tab2[f'{lo}_{mode}_{b}']['miss5']:+.2f} {tab2[f'{lo}_{mode}_{b}']['miss6']:+.1f} {tab2[f'{lo}_{mode}_{b}']['miss7']:+.0f}" for b in ('A', 'B', 'C', 'Dj', 'E', 'F')))
out['table_hi118'] = tab2

# ---------------------------------------------------------------- (3) ensembles
print('\n== (3) ensembles over lo 40..70, all shifts and gaps (hi = 92 and 118); misses vs references')
ens = {}
groups = {
    'fixed_pre': dict(mode='fixed', base=PRE),
    'fixed_all': dict(mode='fixed'),
    'free_all': dict(mode='free'),
    'FL_all': dict(mode='FL'),
    'FL5_all': dict(mode='FL5'),
}
for ds in ('raw', DS):
    for hi in (92, 118):
        for g, kw in groups.items():
            base = o7 & sel(T, ds=ds, hi=hi, lo=lambda x: (x >= 40) & (x <= 70), **kw)
            for cut, mm in (('all', base), ('floor4567', base & T['ok4567']), ('floor67', base & T['ok67'])):
                key = f'{ds}_{hi}_{g}_{cut}'
                ens[key] = {f'miss{n}': summ(T[f'miss{n}'][mm]) for n in range(4, 8)}
                ens[key]['bases'] = sorted(set(T['base'][mm]))
        for g in groups:
            for cut in ('all', 'floor4567'):
                e = ens[f'{ds}_{hi}_{g}_{cut}']
                if e['miss4']['n'] == 0:
                    print(f'{ds:5s} hi={hi} {g:10s} {cut:9s} n=0'); continue
                print(f'{ds:5s} hi={hi} {g:10s} {cut:9s} n={e["miss4"]["n"]:5d} ' + ' '.join(
                    f"C{n} {e[f'miss{n}']['median']:+.4g} [{e[f'miss{n}']['min']:+.3g},{e[f'miss{n}']['max']:+.3g}]" for n in range(4, 8)))
out['ensembles'] = ens

# ---------------------------------------------------------------- (4) paired correction shift dconn - raw
print('\n== (4) intercept shift dconn - raw, same configuration (o7 hi=118, 92 and 72, lo 40..70 (32..60 at 72), all modes)')
pair = {}
for hi in (72, 92, 118):
    lw = (lambda x: (x >= 32) & (x <= 60)) if hi == 72 else (lambda x: (x >= 40) & (x <= 70))
    mr = o7 & sel(T, ds='raw', hi=hi, lo=lw)
    md = o7 & sel(T, ds=DS, hi=hi, lo=lw)
    key = lambda m: {(T['lo'][i], T['base'][i], T['mode'][i], T['sh'][i], T['gap'][i]): i for i in np.where(m)[0]}
    kr, kd = key(mr), key(md)
    common = sorted(set(kr) & set(kd))
    for mode in ('fixed', 'free', 'FL', 'FL5', None):
        cc = [c for c in common if mode is None or c[2] == mode]
        d = {n: np.array([T[f'C{n}'][kd[c]] - T[f'C{n}'][kr[c]] for c in cc]) for n in range(4, 8)}
        pair[f'{hi}_{mode}'] = {f'dC{n}': summ(d[n]) for n in range(4, 8)}
        print(f'hi={hi} {str(mode):5s} n={len(cc)}: ' + ' '.join(f"dC{n} med {np.median(d[n]):+.4g} [16-84 {q(d[n], 16):+.4g},{q(d[n], 84):+.4g}]" for n in range(4, 8)))
out['paired_shift'] = pair

# ---------------------------------------------------------------- (5) linear relation between the misses
print('\n== (5) across floor-level fits (orders 4..7 at floor), dconn hi=118, lo 40..70: misses of C6, C7 vs miss of C5')
reg = {}
for hi in (92, 118):
    m = o7 & sel(T, ds=DS, hi=hi, lo=lambda x: (x >= 40) & (x <= 70)) & T['ok4567'] & (np.abs(T['miss5']) < 5)
    x5 = T['miss5'][m]; x4 = T['miss4'][m]
    for n in (6, 7):
        y = T[f'miss{n}'][m]
        X = np.column_stack([np.ones(len(x5)), x5])
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ b
        reg[f'{hi}_C{n}_vs_C5'] = dict(n=int(m.sum()), intercept=float(b[0]), slope=float(b[1]), resid_rms=float(np.sqrt(np.mean(r ** 2))))
        X2 = np.column_stack([np.ones(len(x5)), x5, x4])
        b2, *_ = np.linalg.lstsq(X2, y, rcond=None)
        r2 = y - X2 @ b2
        reg[f'{hi}_C{n}_vs_C5C4'] = dict(n=int(m.sum()), intercept=float(b2[0]), slopes=b2[1:].tolist(), resid_rms=float(np.sqrt(np.mean(r2 ** 2))))
        print(f'hi={hi} C{n} miss = {b[0]:+.3g} {b[1]:+.4g} * C5miss (n={m.sum()}, resid rms {np.sqrt(np.mean(r ** 2)):.3g});'
              f'  with C4 miss: intercept {b2[0]:+.3g}, slopes {b2[1]:+.4g} (C5) {b2[2]:+.4g} (C4), resid {np.sqrt(np.mean(r2 ** 2)):.3g}')
    # fits that hit C4 and C5 simultaneously
    hit = m & (np.abs(T['miss4']) <= 0.002) & (np.abs(T['miss5']) <= 0.1)
    reg[f'{hi}_hit45'] = dict(n=int(hit.sum()), C6=summ(T['miss6'][hit]), C7=summ(T['miss7'][hit]),
                             modes=sorted(set(T['mode'][hit])), bases=sorted(set(T['base'][hit])))
    print(f'hi={hi} floor fits with |C4 miss|<=0.002 and |C5 miss|<=0.1: n={hit.sum()} C6 miss {fmt(reg[f"{hi}_hit45"]["C6"], "%+.3g")}; C7 miss {fmt(reg[f"{hi}_hit45"]["C7"], "%+.4g")}; modes {reg[f"{hi}_hit45"]["modes"]}')
out['miss_relations'] = reg

# ---------------------------------------------------------------- (6) hi stability of the floor-level ensembles
print('\n== (6) floor-level (orders 4..7) dconn ensembles vs hi, lo 40..70 (or lo 32..50 for hi<=70): C6, C7 misses')
hs = {}
for mode in ('fixed', 'free', 'FL'):
    for hi in (60, 70, 72, 80, 92, 104, 118):
        lo_ok = (lambda x: (x >= 32) & (x <= 50)) if hi <= 70 else (lambda x: (x >= 40) & (x <= 70))
        m = o7 & sel(T, ds=DS, hi=hi, mode=mode, lo=lo_ok) & T['ok4567']
        hs[f'{mode}_{hi}'] = {f'miss{n}': summ(T[f'miss{n}'][m]) for n in (4, 5, 6, 7)}
        e = hs[f'{mode}_{hi}']
        print(f'{mode:5s} hi={hi:3d} n={e["miss6"].get("n", 0):4d} ' + ' '.join(f"C{n} {e[f'miss{n}'].get('median', np.nan):+.4g} [{e[f'miss{n}'].get('p16', np.nan):+.3g},{e[f'miss{n}'].get('p84', np.nan):+.3g}]" for n in (4, 5, 6, 7)))
out['hi_stability'] = hs
json.dump(out, open(f'{rd}/low_summary{SUF}.json', 'w'), indent=1, default=float)
