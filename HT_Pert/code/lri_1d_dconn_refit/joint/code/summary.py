#!/usr/bin/env python3
"""Collect the lens decision numbers into out/<run>/summary.json (reads scan.pkl, low/c8 summaries, propagation, checks)."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
from tab import *
rd = sys.argv[1] if len(sys.argv) > 1 else '../out/run1'
import os
PRIM = os.environ.get('JOINT_PRIMARY', 'dconn')      # refit72: dconn or dconn_w
SUF = '' if PRIM == 'dconn' else '_' + PRIM
T = load(rd)
low = json.load(open(f'{rd}/low_summary{SUF}.json')); c8 = json.load(open(f'{rd}/c8_summary{SUF}.json'))
prop = json.load(open(f'{rd}/propagation{SUF}.json')); chk = json.load(open(f'{rd}/checks.json'))
S = {}
STAT = {4: 1e-3, 5: 0.03, 6: 1.0, 7: 30.}
# ---- C4..C7: noise-floor (orders <= k at floor, dof>=4) and well-determined (stat_n <= STAT[n], n<=k) ensembles, lo 40..70
for ds in (PRIM, 'raw'):
    for hi in (72, 92, 118):
        base = sel(T, kind='o7', ds=ds, hi=hi, lo=lambda x: (x >= 40) & (x <= 70))
        for k in (4, 5, 6, 7):
            ok = np.all([T[f'ok{n}'] for n in range(4, k + 1)], axis=0)
            st = np.all([T[f'stat{n}'] <= STAT[n] for n in range(4, k + 1)], axis=0)
            for tag, m in (('floor', base & ok), ('floor_stat', base & ok & st)):
                d = dict(C=summ(T[f'C{k}'][m]), miss=summ(T[f'miss{k}'][m]),
                         modes={md: int((m & (T['mode'] == md)).sum()) for md in ('fixed', 'free', 'FL', 'FL5')})
                if ds == PRIM and k >= 6:
                    env = np.sum([np.abs(T[f'e_unc{kk}_{k}'][m]) for kk in (6, 7) if kk <= k], axis=0)
                    vF = np.sqrt(np.sum([T[f'v_splF{kk}_{k}_std'][m] ** 2 for kk in (6, 7) if kk <= k], axis=0))
                    d['delta_edge_abs_per_fit'] = summ(env); d['delta_varF_std_per_fit'] = summ(vF)
                    d['ens_median_shift_edge'] = [float(np.median(T[f'C{k}'][m] + s * np.sum([T[f'e_unc{kk}_{k}'][m] for kk in (6, 7) if kk <= k], axis=0)) - np.median(T[f'C{k}'][m])) for s in (1, -1)] if m.any() else None
                    d['ens_median_shift_typ'] = [float(np.median(T[f'C{k}'][m] + s * np.sum([T[f'e_typ{kk}_{k}'][m] for kk in (6, 7) if kk <= k], axis=0)) - np.median(T[f'C{k}'][m])) for s in (1, -1)] if m.any() else None
                S[f'{ds}_hi{hi}_C{k}_{tag}'] = d
# ---- named key fits (hi=118, ext, shift 0), with delta-model edges at C6, C7
key = {}
for lo in (16, 40, 60, 70):
    for mode in ('fixed', 'free', 'FL'):
        for b in ('A', 'B', 'C', 'Dj', 'D', 'E', 'F'):
            m = sel(T, kind='o7', ds=PRIM, hi=118, lo=lo, base=b, mode=mode, sh=0., gap='ext')
            i = np.where(m)[0][0]
            key[f'{b}_{mode}_lo{lo}'] = dict(**{f'C{n}': T[f'C{n}'][i] for n in range(4, 8)}, **{f'miss{n}': T[f'miss{n}'][i] for n in range(4, 8)},
                                           floor={n: round(float(T[f'fl{n}'][i]), 2) for n in range(4, 8)},
                                           delta_edge_C6=float(abs(T['e_unc6_6'][i])), delta_edge_C7=float(abs(T['e_unc6_7'][i]) + abs(T['e_unc7_7'][i])))
S['key_fits_hi118'] = key
# ---- C8: estimators and their delta-model edges (from propagation.json)
est = {}
lo_, hi_ = [], []
for e in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'near3_8'):
    P = prop[e]
    for k in ('sel67', 'sel7', 'reg7', 'reg67'):
        b = P['base'][k]
        if not np.isfinite(b) or (k.startswith('sel') and P['base']['n' + k[3:]] < 5):
            continue
        sh = [P[x][k] - b for x in ('edge_all_plus', 'edge_all_minus', 'edge6_plus', 'edge6_minus', 'edge7_plus', 'edge7_minus', 'edge8_plus', 'edge8_minus') if np.isfinite(P[x][k])]
        jF = np.array(P['joint_splF'][k], float); jF = jF[np.isfinite(jF)]
        est[f'{e}:{k}'] = dict(value=b, value_C7alt=P['base_C7alt'][k], edge_min=min(sh), edge_max=max(sh),
                               typ=[P['typ_all_plus'][k] - b, P['typ_all_minus'][k] - b],
                               joint_floor_variants_16_84=[float(np.percentile(jF, 16)), float(np.percentile(jF, 84))] if len(jF) else None,
                               P_med=P['P_dconn_med'][k] - b, P_mean=P['P_dconn_mean'][k] - b, P_model=P['P_dconn_model'][k] - b,
                               P_s46=P['P_dconn_s46'][k] - b,
                               n=P['base'].get('n' + k[3:]) if k.startswith('sel') else P['n'])
        lo_.append(b + min(sh)); hi_.append(b + max(sh))
vals = [v['value'] for v in est.values()]
S['C8_calibrated'] = dict(estimators=est, median_of_estimators=float(np.median(vals)), min=float(min(vals)), max=float(max(vals)),
                          envelope_with_edges=[float(min(lo_)), float(max(hi_))])
S['C8_uncalibrated'] = {k: dict(n=c8[f'{PRIM}_92_{k}']['n'], C8=c8[f'{PRIM}_92_{k}']['C8'], C6=c8[f'{PRIM}_92_{k}']['C6'], C7=c8[f'{PRIM}_92_{k}']['C7'],
                                om6=c8[f'{PRIM}_92_{k}']['om6'], raw_C8=c8[f'raw_92_{k}']['C8'])
                        for k in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'prior_crit_free', 'prior_crit_FL', 'near3_8', 'near3_8_fixed', 'near3_8_FL', 'near3_all', 'strict8_nostat')}
S['C8_raw_calibrated'] = {k: c8[f'raw_92_{k}']['cal'] for k in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed', 'near3_8')}
S['C8_hi_convergence'] = {f'{k}_{hi}': dict(med=c8[f'{PRIM}_{hi}_{k}']['C8'].get('median'), sel67=c8[f'{PRIM}_{hi}_{k}']['cal']['sel67']['C8'].get('median'),
                                              reg7=(c8[f'{PRIM}_{hi}_{k}']['cal']['reg_d7'] or {}).get('a'))
                          for k in ('prior_crit_prior_grid', 'prior_crit_full_grid', 'prior_crit_fixed') for hi in (70, 72, 80, 92)}
S['paired_shift_dconn_minus_raw'] = dict(o7=low['paired_shift'], o8_hi92=c8['paired_shift_hi92'], exact44=chk['exact44'])
S['prereg'] = low['prereg']; S['miss_relations'] = low['miss_relations']
S['checks'] = dict(precision=chk['precision'], fixed_omega6_slope_per_1e5=summ([r['slope_per_1e5'] for r in chk['fixed_omega6']]),
                   explicit_edge_vs_linear_max_rel=prop['explicit_edge_check']['max_rel_dev'], refit_reproduces_scan=prop['refit_max_rel_dev'])
json.dump(S, open(f'{rd}/summary{SUF}.json', 'w'), indent=1, default=float)
for k in (4, 5, 6, 7):
    for tag in ('floor', 'floor_stat'):
        d = S[f'{PRIM}_hi118_C{k}_{tag}']; r = S[f'raw_hi118_C{k}_{tag}']
        print(f'C{k} {tag:10s} dconn {fmt(d["C"], "%.6g")} | miss med {d["miss"].get("median", np.nan):+.4g} | raw miss {r["miss"].get("median", np.nan):+.4g} | modes {d["modes"]}'
              + (f' | delta edge/fit {d["delta_edge_abs_per_fit"].get("median", np.nan):.3g} floor-variant std/fit {d["delta_varF_std_per_fit"].get("median", np.nan):.3g} ens shift edge {np.round(d["ens_median_shift_edge"], 2).tolist()} typ {np.round(d["ens_median_shift_typ"], 2).tolist()}' if ('delta_edge_abs_per_fit' in d and d.get('ens_median_shift_edge')) else ''))
print('C8 calibrated estimators:')
for k, v in est.items():
    print(f'  {k:32s} {v["value"]:.0f} (C7alt {v["value_C7alt"]:.0f}) edges [{v["edge_min"]:+.0f},{v["edge_max"]:+.0f}] typ {v["typ"][0]:+.0f}/{v["typ"][1]:+.0f} floorvar16-84 {v["joint_floor_variants_16_84"]} Pmed {v["P_med"]:+.0f} n={v["n"]}')
print('median of estimators', S['C8_calibrated']['median_of_estimators'], 'min/max', S['C8_calibrated']['min'], S['C8_calibrated']['max'], 'envelope with edges', S['C8_calibrated']['envelope_with_edges'])
print('key fits:')
for kk in ('A_fixed_lo16', 'B_fixed_lo16', 'C_fixed_lo16', 'E_fixed_lo60', 'Dj_fixed_lo60', 'B_fixed_lo60', 'E_FL_lo60', 'Dj_FL_lo60', 'B_FL_lo60', 'E_free_lo60', 'B_free_lo60'):
    v = key[kk]; print(f'  {kk:14s} ' + ' '.join(f"C{n} {v[f'C{n}']:.7g} ({v[f'miss{n}']:+.3g})" for n in range(4, 8)) + f" fl {v['floor']} dEdge C6 {v['delta_edge_C6']:.2g} C7 {v['delta_edge_C7']:.2g}")
