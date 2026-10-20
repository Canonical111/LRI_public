#!/usr/bin/env python3
"""C8 from the joint linked model (kind o8: order 8 on [lo, hi<=92], omega6 free), raw vs fully corrected data.
Uncalibrated ensembles (noise-floor criteria only), calibrated estimators on C6/C7 (post hoc, as in the 2026-10-04
linked-joint lens: selection on |C6 rel|<=1e-4 and |C7-ref|<=82, selection on C7 only, regression C8 = a + b d7 (+ c d6)),
and the first-order delta-model propagation stored with every corrected fit (edges; per-fit variant spreads).
Output: out/<run>/c8_summary.json + printed tables."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
from tab import *

rd = sys.argv[1] if len(sys.argv) > 1 else '../out/run1'
DS = sys.argv[2] if len(sys.argv) > 2 else 'dconn'          # refit72: corrected dataset analysed (dconn, dconn_s46, dconn_old)
SUF = '' if DS == 'dconn' else '_' + DS
T = load(rd)
print('corrected dataset', DS)
o8 = sel(T, kind='o8')
PRIOR_B = ('A', 'B', 'C', 'D', 'E', 'F', 'BD', 'S', 'Bp', 'A+tower1', 'B+tower1', 'A+tower15', 'A+L075', 'B+L075', 'D+L075')
out = {}


def ensembles(ds, hi, low=None):
    b = o8 & sel(T, ds=ds, hi=hi) & (T['stat8'] <= 1000)
    if low:
        b &= sel(T, low=low)
    lo24 = T['lo'] >= 24
    E = {
        # the 2026-10-04 lens criterion (rms8 <= 1.5 * 7.5e-8, stat8 <= 1000, dof8 >= 4, lo >= 24), its grid
        'prior_crit_prior_grid': b & lo24 & (T['lo'] <= 60) & sel(T, mode='fixed', gap=('orig', 'ext'), base=PRIOR_B) & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4),
        # same criterion, full grid (all modes, bases, gaps)
        'prior_crit_full_grid': b & lo24 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4),
        'prior_crit_fixed': b & lo24 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4) & sel(T, mode='fixed'),
        'prior_crit_free': b & lo24 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4) & sel(T, mode='free'),
        'prior_crit_FL': b & lo24 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4) & sel(T, mode=('FL', 'FL5')),
        # near floor: sigma_hat8 <= 3 * 1.5e-8 (stat8 <= 1000)
        'near3_8': b & lo24 & (T['fl8'] <= 3) & (T['dof8'] >= 4),
        'near3_8_fixed': b & lo24 & (T['fl8'] <= 3) & (T['dof8'] >= 4) & sel(T, mode='fixed'),
        'near3_8_free': b & lo24 & (T['fl8'] <= 3) & (T['dof8'] >= 4) & sel(T, mode='free'),
        'near3_8_FL': b & lo24 & (T['fl8'] <= 3) & (T['dof8'] >= 4) & sel(T, mode=('FL', 'FL5')),
        # near floor at every order (orders 4..7 within 3x their floor too)
        'near3_all': b & lo24 & (T['dof8'] >= 4) & np.all([T[f'fl{n}'] <= 3 for n in range(4, 9)], axis=0),
        # strict: order 8 at the measured floor (sigma_hat8 <= 1.5 * 1.5e-8), NO stat8 cut (noise-limited, lo >= 50 only)
        'strict8_nostat': o8 & sel(T, ds=ds, hi=hi) & (low is None or sel(T, low=low)) & lo24 & T['ok8'],
        'strict_all_nostat': o8 & sel(T, ds=ds, hi=hi) & lo24 & T['ok8all'],
    }
    return E


def describe(m, tag):
    d = dict(n=int(m.sum()), C8=summ(T['C8'][m]), C7=summ(T['C7'][m]), C6=summ(T['C6'][m]), C5=summ(T['C5'][m]), C4=summ(T['C4'][m]),
             om6=summ(T['om6'][m]), bases=sorted(set(T['base'][m])), modes=sorted(set(T['mode'][m])), lows=sorted(set(T['low'][m])))
    return d


def calibrated(m, c7ref=REF[7]):
    r = {}
    d6 = T['C6'] / REF[6] - 1; d7 = T['C7'] / c7ref - 1
    s1 = m & (np.abs(d6) <= 1e-4) & (np.abs(T['C7'] - c7ref) <= 82)
    s2 = m & (np.abs(T['C7'] - c7ref) <= 82)
    r['sel67'] = dict(n=int(s1.sum()), C8=summ(T['C8'][s1]))
    r['sel7'] = dict(n=int(s2.sum()), C8=summ(T['C8'][s2]))
    for name, cols in (('reg_d7', [d7]), ('reg_d6d7', [d6, d7])):
        y = T['C8'][m]
        X = np.column_stack([np.ones(m.sum())] + [c[m] for c in cols])
        if m.sum() < X.shape[1] + 3:
            r[name] = None; continue
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ b
        dof = len(y) - X.shape[1]
        cov = (res @ res / dof) * np.linalg.inv(X.T @ X)
        r[name] = dict(n=int(m.sum()), a=float(b[0]), se=float(np.sqrt(cov[0, 0])), slopes=b[1:].tolist(), resid_rms=float(np.sqrt(res @ res / dof)))
    return r


for ds in ('raw', DS):
    for hi in (50, 60, 70, 72, 80, 92):
        E = ensembles(ds, hi)
        for k, m in E.items():
            key = f'{ds}_{hi}_{k}'
            out[key] = describe(m, key)
            out[key]['cal'] = calibrated(m)
            out[key]['cal_alt7'] = calibrated(m, F.C7_ALT)

print('== C8 ensembles (o8), uncalibrated: median [16-84] {min-max} | C6, C7 medians; calibrated estimators (C6 exact, C7 -322550)')
KEYS = ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'prior_crit_free', 'prior_crit_FL', 'near3_8', 'near3_8_fixed',
        'near3_8_free', 'near3_8_FL', 'near3_all', 'strict8_nostat', 'strict_all_nostat')
for k in KEYS:
    for ds in ('raw', DS):
        for hi in (70, 72, 80, 92):
            e = out[f'{ds}_{hi}_{k}']
            if e['n'] == 0:
                print(f'{k:22s} {ds:5s} hi={hi} n=0'); continue
            c = e['cal']
            sel67 = c['sel67']['C8']; sel7 = c['sel7']['C8']
            rg = c['reg_d7']; rg2 = c['reg_d6d7']
            print(f"{k:22s} {ds:5s} hi={hi} n={e['n']:4d} C8 {e['C8']['median']:.0f} [{e['C8']['p16']:.0f}..{e['C8']['p84']:.0f}] {{{e['C8']['min']:.0f}..{e['C8']['max']:.0f}}}"
                  f" | C6 {e['C6']['median']:.2f} C7 {e['C7']['median']:.0f} om6 {e['om6']['median']:.3g}"
                  f" | sel67 n={c['sel67']['n']} {sel67.get('median', float('nan')):.0f} sel7 n={c['sel7']['n']} {sel7.get('median', float('nan')):.0f}"
                  f" | reg d7 {rg['a'] if rg else float('nan'):.0f}+-{rg['se'] if rg else float('nan'):.0f} d6d7 {rg2['a'] if rg2 else float('nan'):.0f}+-{rg2['se'] if rg2 else float('nan'):.0f}"
                  f" | stat8 med {np.median(T['stat8'][ensembles(ds, hi)[k]]):.3g}")

# ---------------------------------------------------------------- paired dconn - raw shift of C8 (same config)
for HP in (92, 72):
  print(f'\n== paired C8 shift {DS} - raw (same configuration), o8 hi={HP}')
  mr = o8 & sel(T, ds='raw', hi=HP); md = o8 & sel(T, ds=DS, hi=HP)
  key = lambda m: {(T['lo'][i], T['base'][i], T['mode'][i], T['sh'][i], T['gap'][i], T['low'][i]): i for i in np.where(m)[0]}
  kr, kd = key(mr), key(md)
  common = [c for c in kr if c in kd]
  pair = {}
  for name, filt in (('all', lambda c, i: True), ('near3_8 (dconn)', lambda c, i: T['fl8'][i] <= 3 and T['dof8'][i] >= 4 and T['lo'][i] >= 24 and T['stat8'][i] <= 1000),
                     ('prior crit (dconn)', lambda c, i: T['rmsc8'][i] <= 1.125e-7 and T['dof8'][i] >= 4 and T['lo'][i] >= 24 and T['stat8'][i] <= 1000)):
      cc = [c for c in common if filt(c, kd[c])]
      d = {n: np.array([T[f'C{n}'][kd[c]] - T[f'C{n}'][kr[c]] for c in cc]) for n in (6, 7, 8)}
      pair[name] = {f'dC{n}': summ(d[n]) for n in (6, 7, 8)}
      print(f'{name:20s} n={len(cc)}: ' + ' '.join(f"dC{n} med {np.median(d[n]):+.4g} [16-84 {q(d[n], 16):+.4g},{q(d[n], 84):+.4g}]" for n in (6, 7, 8)))
  out[f'paired_shift_hi{HP}'] = pair

# ---------------------------------------------------------------- delta-model propagation (stored first-order responses)
print('\n== delta-model propagation for the corrected ensembles at hi=92 (per-fit first-order responses)')
prop = {}
for k in (KEYS if DS in ('dconn', 'dconn_w') else ()):
    m = ensembles(DS, 92)[k]
    if m.sum() == 0:
        continue
    P = {}
    for n in (6, 7, 8):
        cols = [f'e_unc{kk}_{n}' for kk in (6, 7, 8) if kk <= n]
        tcols = [f'e_typ{kk}_{n}' for kk in (6, 7, 8) if kk <= n]
        env_abs = np.sum([np.abs(T[c][m]) for c in cols], axis=0)      # |sum over k of |edge response||
        coh = np.sum([T[c][m] for c in cols], axis=0)                    # all three edges +1 together
        typ_abs = np.sum([np.abs(T[c][m]) for c in tcols], axis=0)
        vstd = {fam: np.sqrt(np.sum([T[f'v_{fam}{kk}_{n}_std'][m] ** 2 for kk in (6, 7, 8) if kk <= n], axis=0)) for fam in ('spl', 'splF', 'evw', 'evwF')}
        P[n] = dict(env_abs=summ(env_abs), coherent_plus=summ(coh), typ_abs=summ(typ_abs), **{f'var_{f}_std': summ(v) for f, v in vstd.items()},
                    P_med=summ(T[f'P_dconn_med_{n}'][m]), P_mean=summ(T[f'P_dconn_mean_{n}'][m]), P_model=summ(T[f'P_dconn_model_{n}'][m]))
        # ensemble-level: median of the shifted intercepts (all fits shifted coherently by the +edge / -edge)
        if n == 8:
            base = np.median(T['C8'][m])
            P['ens_median_shift_edges'] = dict(plus=float(np.median(T['C8'][m] + coh) - base), minus=float(np.median(T['C8'][m] - coh) - base),
                                               **{f'unc{kk}_plus': float(np.median(T['C8'][m] + T[f'e_unc{kk}_8'][m]) - base) for kk in (6, 7, 8)},
                                               typ_plus=float(np.median(T['C8'][m] + np.sum([T[f'e_typ{kk}_8'][m] for kk in (6, 7, 8)], axis=0)) - base),
                                               P_med=float(np.median(T['C8'][m] + T['P_dconn_med_8'][m]) - base),
                                               P_mean=float(np.median(T['C8'][m] + T['P_dconn_mean_8'][m]) - base),
                                               P_model=float(np.median(T['C8'][m] + T['P_dconn_model_8'][m]) - base))
    prop[k] = P
    print(f'{k:20s} n={m.sum()}: C8 per-fit |edge| sum med {P[8]["env_abs"]["median"]:.0f} [{P[8]["env_abs"]["p16"]:.0f}..{P[8]["env_abs"]["p84"]:.0f}], typ {P[8]["typ_abs"]["median"]:.0f};'
          f' variant std (spl/splF/evw) {P[8]["var_spl_std"]["median"]:.0f}/{P[8]["var_splF_std"]["median"]:.0f}/{P[8]["var_evw_std"]["median"]:.0f};'
          f' ensemble-median shift +edge {P["ens_median_shift_edges"]["plus"]:+.0f} -edge {P["ens_median_shift_edges"]["minus"]:+.0f};'
          f' prescriptions med/mean/model {P["ens_median_shift_edges"]["P_med"]:+.0f}/{P["ens_median_shift_edges"]["P_mean"]:+.0f}/{P["ens_median_shift_edges"]["P_model"]:+.0f}')
    print(f'{"":20s} C6: |edge| {P[6]["env_abs"]["median"]:.3g}, var std spl {P[6]["var_spl_std"]["median"]:.3g}; C7: |edge| {P[7]["env_abs"]["median"]:.3g}, var std spl {P[7]["var_spl_std"]["median"]:.3g} splF {P[7]["var_splF_std"]["median"]:.3g}')
out['propagation_hi92'] = prop
json.dump(out, open(f'{rd}/c8_summary{SUF}.json', 'w'), indent=1, default=float)
