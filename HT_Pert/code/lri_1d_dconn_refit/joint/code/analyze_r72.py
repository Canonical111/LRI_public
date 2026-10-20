#!/usr/bin/env python3
"""refit72 comparison tables for the joint-model lens (reads out/<run>/scan.pkl; no fitting).

Datasets: raw; dconn (primary: exact dC to 72 incl. the noisy S10 cluster rows 46..72, floor-mean delta-v1 hi=72 curve
beyond); dconn_s46 (smooth sensitivity: exact to 44, floor-mean curve from 46); dconn_old (run1 primary, delta-v1 hi=44).
Criteria as in run1 (tab.py), with the whitened residual rms for dconn (identical to the plain rms elsewhere).
Sections: A noise floors re-derived per dataset; B C4/C5 identity; C C4..C7 at hi=118 and 92; D paired new-old shifts;
E C8 at hi=92 (uncalibrated families + calibrated estimators); F hi=72 delta-free windows; G S10-noise propagation;
H family spread. Output: out/<run>/r72_summary.json + printed tables."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
from tab import *

rd = sys.argv[1] if len(sys.argv) > 1 else '../out/r72'
T = load(rd)
N = len(T['kind'])
DSS = ('raw', 'dconn', 'dconn_w', 'dconn_s46', 'dconn_old')
PRIOR_B = ('A', 'B', 'C', 'D', 'E', 'F', 'BD', 'S', 'Bp', 'A+tower1', 'B+tower1', 'A+tower15', 'A+L075', 'B+L075', 'D+L075')
STAT = {4: 1e-3, 5: 0.03, 6: 1.0, 7: 30.}
MODES_ALL = ('fixed', 'free', 'FL', 'FL5')
O = {}


def S_(x):
    return summ(x)


def f4(s, f='%+.4g'):
    if not s or s.get('n', 0) == 0:
        return 'n=0'
    return f"n={s['n']} med {f % s['median']} [{f % s['p16']},{f % s['p84']}] {{{f % s['min']}..{f % s['max']}}}"


o7 = T['kind'] == 'o7'
o8 = T['kind'] == 'o8'
lo4070 = lambda x: (x >= 40) & (x <= 70)

# ---------------------------------------------------------------- A noise floors
print('== A. noise floor re-derived per dataset: min (p05) of sigma_hat_n = rms_n sqrt(npts/dof) over fits with dof>=6, lo 24..60')
A = {}
for ds in DSS:
    for n in range(4, 9):
        kindm = o8 if n == 8 else o7
        for cls, hm in (('le92', (T['hi'] <= 92) & (T['low'] == 'same')), ('104_118', T['hi'] >= 104), ('hi72', (T['hi'] == 72) & (T['low'] == 'same'))):
            m = kindm & (T['ds'] == ds) & hm & (T[f'dof{n}'] >= 6) & (T['lo'] >= 24) & (T['lo'] <= 60)
            if not m.any():
                continue
            dof = T[f'dof{n}'][m]; npt = T[f'npts{n}'][m]
            sp = T[f'rms{n}'][m] * np.sqrt(npt / dof); sw = T[f'erms{n}'][m] * np.sqrt(npt / dof)
            A[f'{ds}_{n}_{cls}'] = dict(n=int(m.sum()), min_plain=float(sp.min()), p05_plain=float(np.percentile(sp, 5)),
                                        min_w=float(sw.min()), p05_w=float(np.percentile(sw, 5)))
    print(f'{ds:10s} ' + '  '.join(f"Y{n}:" + '/'.join(f"{A[f'{ds}_{n}_{c}']['min_plain']:.1e}" + (f"(w {A[f'{ds}_{n}_{c}']['min_w']:.1e})" if ds in ('dconn', 'dconn_w') else '')
                                                       for c in ('le92', '104_118', 'hi72') if f'{ds}_{n}_{c}' in A) for n in range(4, 9)))
print('   run1 constants SIG92', SIG92, 'SIG118', SIG118, '(classes: hi<=92 / hi 104..118 / hi=72 only)')
O['A_noise'] = A

# ---------------------------------------------------------------- B C4/C5 identity across corrected datasets
key = lambda m: {(T['kind'][i], T['hi'][i], T['low'][i], T['lo'][i], T['base'][i], T['mode'][i], T['sh'][i], T['gap'][i]): i for i in np.where(m)[0]}
K = {ds: key(T['ds'] == ds) for ds in DSS}
B = {}
for a, b in (('dconn', 'dconn_old'), ('dconn_s46', 'dconn_old'), ('dconn', 'dconn_s46'), ('dconn_w', 'dconn')):
    cc = [c for c in K[a] if c in K[b]]
    ia = np.array([K[a][c] for c in cc], dtype=int); ib = np.array([K[b][c] for c in cc], dtype=int)
    B[f'{a}-{b}'] = {f'C{n}': float(np.nanmax(np.abs(T[f'C{n}'][ia] - T[f'C{n}'][ib]))) for n in (4, 5)}
print('\n== B. max |C4|, |C5| difference between corrected datasets (same config):', B)
O['B_C45_identity'] = B

# ---------------------------------------------------------------- C low orders
print('\n== C. C4..C7 (o7), lo 40..70, all shifts and gaps: misses vs references')
C = {}
for hi in (118, 92):
    for ds in DSS:
        base = o7 & (T['ds'] == ds) & (T['hi'] == hi) & lo4070(T['lo'])
        r = {}
        fx = base & sel(T, mode='fixed', base=PRE)
        r['fixed_AF'] = {f'miss{n}': S_(T[f'miss{n}'][fx]) for n in range(4, 8)}
        for kk in (4, 5, 6, 7):
            ok = np.all([T[f'ok{n}'] for n in range(4, kk + 1)], axis=0)
            st = np.all([T[f'stat{n}'] <= STAT[n] for n in range(4, kk + 1)], axis=0)
            r[f'floor_C{kk}'] = dict(miss=S_(T[f'miss{kk}'][base & ok]), C=S_(T[f'C{kk}'][base & ok]))
            r[f'floorstat_C{kk}'] = dict(miss=S_(T[f'miss{kk}'][base & ok & st]), C=S_(T[f'C{kk}'][base & ok & st]),
                                         modes={md: int((base & ok & st & (T['mode'] == md)).sum()) for md in MODES_ALL})
        for b in ('E', 'Dj', 'B', 'D'):
            for mode in ('fixed', 'FL'):
                m = base & sel(T, base=b, mode=mode, lo=60, sh=0., gap='ext')
                if m.any():
                    i = np.where(m)[0][0]
                    r[f'key_{b}_{mode}_lo60'] = {f'miss{n}': float(T[f'miss{n}'][i]) for n in range(4, 8)} | {f'fl{n}': round(float(T[f'fl{n}'][i]), 2) for n in range(4, 8)}
        hit = base & (np.abs(T['miss4']) <= 0.005) & (np.abs(T['miss5']) <= 0.2) & (np.abs(T['miss6']) <= 1.5) & (np.abs(T['miss7']) <= 82)
        nf = hit & np.all([T[f'fl{n}'] <= 3 for n in range(4, 8)], axis=0)
        r['hit_all'] = dict(n=int(hit.sum()), n_ext=int((hit & (T['gap'] == 'ext')).sum()), n_nearfloor=int(nf.sum()),
                            nearfloor=[dict(base=T['base'][i], mode=T['mode'][i], lo=float(T['lo'][i]), sh=float(T['sh'][i]), gap=T['gap'][i],
                                            miss=[round(float(T[f'miss{n}'][i]), 4) for n in range(4, 8)], fl=[round(float(T[f'fl{n}'][i]), 2) for n in range(4, 8)])
                                       for i in np.where(nf)[0][:12]])
        h45 = base & T['ok4567'] & (np.abs(T['miss4']) <= 0.002) & (np.abs(T['miss5']) <= 0.1)
        r['floor_hit45'] = dict(n=int(h45.sum()), miss6=S_(T['miss6'][h45]), miss7=S_(T['miss7'][h45]), modes=sorted(set(T['mode'][h45])))
        C[f'{ds}_hi{hi}'] = r
for hi in (118, 92):
    print(f'-- hi={hi}')
    for ds in DSS:
        r = C[f'{ds}_hi{hi}']
        print(f"{ds:10s} fixed A-F: C4 {r['fixed_AF']['miss4'].get('median', np.nan):+.4f} C5 {r['fixed_AF']['miss5'].get('median', np.nan):+.3f} C6 {f4(r['fixed_AF']['miss6'], '%+.2f')} C7 {f4(r['fixed_AF']['miss7'], '%+.0f')}")
        print(f"{'':10s} floor+stat: C4 {f4(r['floorstat_C4']['miss'], '%+.4f')} | C5 {f4(r['floorstat_C5']['miss'], '%+.3f')}")
        print(f"{'':10s}             C6 {f4(r['floorstat_C6']['miss'], '%+.2f')} {r['floorstat_C6']['modes']} | C7 {f4(r['floorstat_C7']['miss'], '%+.0f')} {r['floorstat_C7']['modes']}")
        print(f"{'':10s} floor only: C6 {f4(r['floor_C6']['miss'], '%+.2f')} | C7 {f4(r['floor_C7']['miss'], '%+.0f')}")
        print(f"{'':10s} key lo60 ext sh0: " + ' '.join(f"{k[4:]}: C6 {v['miss6']:+.2f} C7 {v['miss7']:+.0f} fl {v['fl6']}/{v['fl7']}" for k, v in r.items() if k.startswith('key_')))
        print(f"{'':10s} hit C4..C7 (0.005/0.2/1.5/82): n={r['hit_all']['n']} (ext {r['hit_all']['n_ext']}), near floor (fl<=3 at 4..7) {r['hit_all']['n_nearfloor']};"
              f" floor & hit C4,C5 (0.002/0.1): n={r['floor_hit45']['n']} C6 {f4(r['floor_hit45']['miss6'], '%+.2f')} C7 {f4(r['floor_hit45']['miss7'], '%+.0f')}")
        for x in r['hit_all']['nearfloor'][:6]:
            print(f"{'':14s} {x['base']:8s} {x['mode']:5s} lo={x['lo']:.0f} sh={x['sh']:+.0f} {x['gap']:4s} miss {x['miss']} fl {x['fl']}")
O['C_low'] = C

# ---------------------------------------------------------------- D paired shifts new - old
print('\n== D. paired intercept shifts between datasets (same configuration), by mode: median [16-84]')
D_ = {}
for a, b in (('dconn', 'dconn_old'), ('dconn_w', 'dconn_old'), ('dconn_s46', 'dconn_old'), ('dconn', 'dconn_s46'), ('dconn_w', 'dconn_s46'), ('dconn_w', 'raw'), ('dconn', 'raw')):
    for kind, hi, low in (('o7', 118, 'same'), ('o7', 92, 'same'), ('o8', 92, 'same'), ('o8', 92, 'th118'), ('o7', 72, 'same'), ('o8', 72, 'same')):
        lw = (lambda x: (x >= 32) & (x <= 60)) if hi == 72 else ((lambda x: (x >= 24) & (x <= 70)) if kind == 'o8' else lo4070)
        cc = [c for c in K[a] if c in K[b] and c[0] == kind and c[1] == hi and c[2] == low and lw(np.array([c[3]]))[0]]
        for mode in ('fixed', 'free', 'FL', 'FL5', None):
            c2 = [c for c in cc if mode is None or c[5] == mode]
            ia = np.array([K[a][c] for c in c2], dtype=int); ib = np.array([K[b][c] for c in c2], dtype=int)
            ns = (6, 7, 8) if kind == 'o8' else (6, 7)
            D_[f'{a}-{b}_{kind}_{hi}_{low}_{mode}'] = {f'dC{n}': S_(T[f'C{n}'][ia] - T[f'C{n}'][ib]) for n in ns}
        e = D_[f'{a}-{b}_{kind}_{hi}_{low}_None']
        print(f'{a}-{b:9s} {kind} hi={hi} {low:5s}: ' + ' | '.join(
            f"{('all' if md is None else md)}: " + ' '.join(f"{D_[f'{a}-{b}_{kind}_{hi}_{low}_{md}'][f'dC{n}'].get('median', np.nan):+.3g}" for n in ((6, 7, 8) if kind == 'o8' else (6, 7)))
            for md in ('fixed', 'free', 'FL', None)) + '   [all 16-84: ' + ' '.join(f"{e[f'dC{n}'].get('p16', np.nan):+.3g}..{e[f'dC{n}'].get('p84', np.nan):+.3g}" for n in ((6, 7, 8) if kind == 'o8' else (6, 7))) + ']')
O['D_paired'] = D_


# ---------------------------------------------------------------- E/F C8
def ens8(ds, hi, low=None, rmsc='rmsc8', flk='fl'):
    b = o8 & (T['ds'] == ds) & (T['hi'] == hi) & (T['stat8'] <= 1000)
    if low:
        b &= (T['low'] == low)
    lo24 = T['lo'] >= 24
    pc = b & lo24 & (T[rmsc] <= 1.125e-7) & (T['dof8'] >= 4)
    nr = b & lo24 & (T[f'{flk}8'] <= 3) & (T['dof8'] >= 4)
    return {
        'prior_crit_prior_grid': pc & (T['lo'] <= 60) & sel(T, mode='fixed', gap=('orig', 'ext'), base=PRIOR_B),
        'prior_crit_full_grid': pc, 'prior_crit_fixed': pc & (T['mode'] == 'fixed'), 'prior_crit_free': pc & (T['mode'] == 'free'),
        'prior_crit_FL': pc & sel(T, mode=('FL', 'FL5')),
        'near3_8': nr, 'near3_8_fixed': nr & (T['mode'] == 'fixed'), 'near3_8_free': nr & (T['mode'] == 'free'), 'near3_8_FL': nr & sel(T, mode=('FL', 'FL5')),
        'near3_all': b & lo24 & (T['dof8'] >= 4) & np.all([T[f'{flk}{n}'] <= 3 for n in range(4, 9)], axis=0),
        'all_lo24': b & lo24 & (T['dof8'] >= 4),
    }


def calib(m, c7ref=REF[7]):
    r = {}
    d6 = T['C6'] / REF[6] - 1; d7 = T['C7'] / c7ref - 1
    s1 = m & (np.abs(d6) <= 1e-4) & (np.abs(T['C7'] - c7ref) <= 82)
    s2 = m & (np.abs(T['C7'] - c7ref) <= 82)
    r['sel67'] = dict(n=int(s1.sum()), C8=float(np.median(T['C8'][s1])) if s1.any() else np.nan)
    r['sel7'] = dict(n=int(s2.sum()), C8=float(np.median(T['C8'][s2])) if s2.any() else np.nan)
    for name, cols in (('reg7', [d7]), ('reg67', [d6, d7])):
        y = T['C8'][m]
        X = np.column_stack([np.ones(m.sum())] + [c[m] for c in cols])
        if m.sum() < X.shape[1] + 3:
            r[name] = dict(n=int(m.sum()), C8=np.nan); continue
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ b; dof = len(y) - X.shape[1]
        cov = (res @ res / dof) * np.linalg.inv(X.T @ X)
        r[name] = dict(n=int(m.sum()), C8=float(b[0]), se=float(np.sqrt(cov[0, 0])), slopes=b[1:].tolist())
    return r


def c8block(ds, hi, low=None, rmsc='rmsc8', flk='fl'):
    E = ens8(ds, hi, low, rmsc, flk)
    out = {}
    for k, m in E.items():
        out[k] = dict(n=int(m.sum()), C8=S_(T['C8'][m]), C7=S_(T['C7'][m]), C6=S_(T['C6'][m]), om6=S_(T['om6'][m]),
                      statx8=S_(T['statx8'][m]) if ds in ('dconn', 'dconn_w') else None, cal=calib(m), cal_alt7=calib(m, C7_ALT))
    est = []
    for e in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'near3_8'):
        for k in ('sel67', 'sel7', 'reg7', 'reg67'):
            c = out[e]['cal'][k]
            if np.isfinite(c['C8']) and not (k.startswith('sel') and c['n'] < 5):
                est.append((f'{e}:{k}', c['C8'], c['n']))
    vals = [v for _, v, _ in est]
    out['estimators'] = {k: dict(C8=v, n=n) for k, v, n in est}
    # selection-choice sensitivity (verify stage): anchoring on all of C4..C7, per tail family, tighter order-8 criterion
    hit4 = (np.abs(T['miss4']) <= 0.005) & (np.abs(T['miss5']) <= 0.2) & (np.abs(T['C6'] / REF[6] - 1) <= 1e-4) & (np.abs(T['C7'] - REF[7]) <= 82)
    nf = np.all([T[f'{flk}{n}'] <= 3 for n in range(4, 9)], axis=0)
    out['sel4567'] = {k: dict(n=int((E[k] & hit4).sum()), C8=S_(T['C8'][E[k] & hit4])) for k in ('prior_crit_full_grid', 'near3_8', 'all_lo24')}
    out['sel4567']['all_lo24_nearfloor'] = dict(n=int((E['all_lo24'] & hit4 & nf).sum()), C8=S_(T['C8'][E['all_lo24'] & hit4 & nf]))
    out['est_summary'] = dict(n=len(vals), median=float(np.median(vals)) if vals else np.nan, min=float(min(vals)) if vals else np.nan,
                              max=float(max(vals)) if vals else np.nan)
    return out


def pr8(tag, b):
    for k in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'prior_crit_free', 'prior_crit_FL', 'near3_8', 'near3_8_fixed', 'near3_8_free', 'near3_8_FL', 'near3_all'):
        e = b[k]; c = e['cal']
        if e['n'] == 0:
            print(f'   {k:22s} n=0'); continue
        print(f"   {k:22s} n={e['n']:4d} C8 {e['C8']['median']:.0f} [{e['C8']['p16']:.0f}..{e['C8']['p84']:.0f}] | C6 {e['C6']['median']:.2f} C7 {e['C7']['median']:.0f}"
              f" | sel67 {c['sel67']['C8']:.0f} (n={c['sel67']['n']}) sel7 {c['sel7']['C8']:.0f} (n={c['sel7']['n']}) reg7 {c['reg7']['C8']:.0f} reg67 {c['reg67']['C8']:.0f}"
              + (f" | statx8 med {e['statx8']['median']:.0f}" if e.get('statx8') and e['statx8'].get('n') else ''))
    s = b['est_summary']
    print(f"   {tag}: calibrated estimators (n={s['n']}) median {s['median']:.0f} range {s['min']:.0f}..{s['max']:.0f}")
    print('   anchored on C4..C7 (0.005/0.2/1e-4/82): ' + ' | '.join(f"{k}: n={v['n']} C8 {v['C8'].get('median', np.nan):.0f}" for k, v in b['sel4567'].items()))


print('\n== E. C8, o8 hi=92 (both lower-order windows), per dataset')
E8 = {}
for ds in DSS:
    E8[f'{ds}_92'] = c8block(ds, 92)
    print(f'-- {ds} hi=92'); pr8(ds, E8[f'{ds}_92'])
E8['dconn_92_plain'] = c8block('dconn', 92, rmsc='rms8', flk='flp')
E8['dconn_w_92_plain'] = c8block('dconn_w', 92, rmsc='rms8', flk='flp')
print('-- dconn hi=92, PLAIN (unweighted) criteria'); pr8('dconn plain', E8['dconn_92_plain'])
for hi in (70, 80):
    for ds in ('dconn', 'dconn_w', 'dconn_s46', 'dconn_old'):
        E8[f'{ds}_{hi}'] = c8block(ds, hi)
print('   hi convergence (prior grid sel67 / full-grid sel67 / est median): ' + '; '.join(
    f"{ds}: " + ' '.join(f"{hi}:{E8[f'{ds}_{hi}']['prior_crit_prior_grid']['cal']['sel67']['C8']:.0f}/{E8[f'{ds}_{hi}']['prior_crit_full_grid']['cal']['sel67']['C8']:.0f}/{E8[f'{ds}_{hi}']['est_summary']['median']:.0f}" for hi in (70, 80, 92))
    for ds in ('dconn', 'dconn_w', 'dconn_s46', 'dconn_old')))

print('\n== F. delta-free windows: o8 hi=72 with every order on [lo, 72] (low=same)')
for ds in DSS:
    E8[f'{ds}_72same'] = c8block(ds, 72, 'same')
    print(f'-- {ds} hi=72 same'); pr8(ds + ' hi72', E8[f'{ds}_72same'])
E8['dconn_72same_plain'] = c8block('dconn', 72, 'same', rmsc='rms8', flk='flp')
print('-- dconn hi=72 same, PLAIN criteria'); pr8('dconn hi72 plain', E8['dconn_72same_plain'])
for ds in ('dconn', 'dconn_w', 'dconn_s46'):
    E8[f'{ds}_92same'] = c8block(ds, 92, 'same')
    print(f'-- {ds} hi=92 same-window only (for comparison with hi=72 same)'); pr8(ds + ' hi92same', E8[f'{ds}_92same'])
# delta-model responses must vanish on [lo, 72]
m72 = o8 & np.isin(T['ds'], ['dconn', 'dconn_w']) & (T['hi'] == 72) & (T['low'] == 'same')
dz = max(float(np.nanmax(np.abs(T[f'e_{p}{k}_{n}'][m72]))) for p in ('unc', 'typ') for k in (6, 7, 8) for n in range(k, 9))
vz = max(float(np.nanmax(np.abs(T[f'v_{f}{k}_{n}_std'][m72]))) for f in ('spl', 'splF') for k in (6, 7, 8) for n in range(k, 9))
print(f'   delta-model response on hi=72 same windows: max |edge response| {dz:.1e}, max spliced-variant std {vz:.1e} (must be 0;'
      f' the evw variants replace the exact dC at L <= 72 too and are not delta-free)')
O['F_delta_free_check'] = dict(max_edge_response=dz, max_variant_std=vz)
# low orders at hi=72 (o7)
F7 = {}
for ds in DSS:
    base = o7 & (T['ds'] == ds) & (T['hi'] == 72) & (T['lo'] >= 24) & (T['lo'] <= 50)
    fx = base & sel(T, mode='fixed', base=PRE) & (T['dof7'] >= 2)
    r = dict(fixed_AF={f'miss{n}': S_(T[f'miss{n}'][fx]) for n in (6, 7)})
    for kk in (6, 7):
        ok = np.all([T[f'ok{n}'] for n in range(4, kk + 1)], axis=0)
        st = np.all([T[f'stat{n}'] <= STAT[n] for n in range(4, kk + 1)], axis=0)
        r[f'floor_C{kk}'] = S_(T[f'miss{kk}'][base & ok]); r[f'floorstat_C{kk}'] = S_(T[f'miss{kk}'][base & ok & st])
        r[f'floorstat_C{kk}_modes'] = {md: int((base & ok & st & (T['mode'] == md)).sum()) for md in MODES_ALL}
    hit = base & (np.abs(T['miss4']) <= 0.005) & (np.abs(T['miss5']) <= 0.2) & (np.abs(T['miss6']) <= 1.5) & (np.abs(T['miss7']) <= 82)
    r['hit_all'] = int(hit.sum())
    F7[ds] = r
    print(f"{ds:10s} o7 hi=72 lo 24..50: fixed A-F C6 {f4(r['fixed_AF']['miss6'], '%+.2f')} C7 {f4(r['fixed_AF']['miss7'], '%+.0f')}")
    print(f"{'':10s} floor+stat C6 {f4(r['floorstat_C6'], '%+.2f')} {r['floorstat_C6_modes']} | C7 {f4(r['floorstat_C7'], '%+.0f')} {r['floorstat_C7_modes']} | hit C4..C7 n={r['hit_all']}")
O['F_low72'] = F7
O['E_F_C8'] = E8

# ---------------------------------------------------------------- G S10-noise propagation per fit (dconn)
print('\n== G. S10 cluster noise (L=46..72) propagated into the intercepts, per fit (1 sigma, dconn):')
G = {}
for tag, m in [(f'{dsx}:' + t, mm) for dsx in ('dconn', 'dconn_w') for t, mm in (
               ('o7_hi118_lo40-70', o7 & (T['ds'] == dsx) & (T['hi'] == 118) & lo4070(T['lo'])),
               ('o8_hi92_priorcrit_full', ens8(dsx, 92)['prior_crit_full_grid']), ('o8_hi92_near3', ens8(dsx, 92)['near3_8']),
               ('o8_hi72same_priorcrit_full', ens8(dsx, 72, 'same')['prior_crit_full_grid']), ('o8_hi72same_all', ens8(dsx, 72, 'same')['all_lo24']))]:
    G[tag] = {f'statx{n}': S_(T[f'statx{n}'][m]) for n in (6, 7, 8) if not ('o7_' in tag and n == 8)}
    print(f'   {tag:36s} ' + ' '.join(f"{k}: med {v.get('median', np.nan):.3g} [{v.get('p16', np.nan):.3g},{v.get('p84', np.nan):.3g}]" for k, v in G[tag].items()))
O['G_s10_noise'] = G

# ---------------------------------------------------------------- H family spread summary
print('\n== H. family spread (C8 uncalibrated medians, prior criterion, hi=92 / hi=72 same; C6/C7 floor+stat at hi=118)')
H = {}
for ds in DSS:
    H[ds] = {fam: dict(hi92=E8[f'{ds}_92'][f'prior_crit_{fam}']['C8'].get('median'), hi72=E8[f'{ds}_72same'][f'prior_crit_{fam}']['C8'].get('median'),
                       n92=E8[f'{ds}_92'][f'prior_crit_{fam}']['n'], n72=E8[f'{ds}_72same'][f'prior_crit_{fam}']['n'])
             for fam in ('fixed', 'free', 'FL')}
    print(f'{ds:10s} ' + ' | '.join(f"{fam}: {v['hi92'] if v['hi92'] is None else round(v['hi92'])} (n={v['n92']}) / {v['hi72'] if v['hi72'] is None else round(v['hi72'])} (n={v['n72']})" for fam, v in H[ds].items()))
O['H_family'] = H
json.dump(O, open(f'{rd}/r72_summary.json', 'w'), indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
print('wrote', f'{rd}/r72_summary.json')
