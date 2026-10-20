#!/usr/bin/env python3
"""Delta-model propagation at the level of the ensemble estimators (uncalibrated medians and the C6/C7-calibrated
estimators), for the corrected (dconn) o8 hi=92 ensembles.

1. Re-fits every member of the selected ensembles with all perturbations (fitcore.fit perts) and keeps, per fit, the
   first-order response of C6, C7, C8 to every delta-v1 kept curve (spliced 'spl', everywhere 'evw'), to the envelope
   edges and to the alternative prescriptions; checks that the re-fit reproduces the scan intercepts.
2. Estimators recomputed on the shifted intercepts (selection is redone on the shifted C6/C7):
     med    : uncalibrated ensemble median of C8
     sel67  : median C8 of fits with |C6/C6ref-1|<=1e-4 and |C7-C7ref|<=82
     sel7   : median C8 of fits with |C7-C7ref|<=82
     reg7   : intercept a of C8 = a + b d7 over the ensemble (d7 = C7/C7ref - 1)
     reg67  : intercept of C8 = a + b d6 + c d7
   for: envelope edges (+-unc, all orders coherently and per order; typical +-typ), each kept curve of each order
   (k = 6, 7, 8 separately), 400 random joint draws (i6, i7, i8) of kept curves (spl, splF = floor-level curves only,
   evw), and the three alternative prescriptions.
3. Explicit (non-linearized) re-fits of 24 ensemble members with the corrected data shifted by +-unc (all orders) to
   verify the linear response.
Output: out/<run>/propagation.json"""
import sys, os, json, time
sys.dont_write_bytecode = True
import numpy as np
import fitcore as F
from data import load as dload
from tab import load as tload, sel, REF
from scan import spec_of, SIGRAW

rd = sys.argv[1] if len(sys.argv) > 1 else '../out/run1'
PRIM = os.environ.get('JOINT_PRIMARY', 'dconn')      # refit72: dconn (unweighted) or dconn_w (weighted fits of the same table)
SUF = '' if PRIM == 'dconn' else '_' + PRIM
T = tload(rd)
D = dload()
L = D['L']; C = D['dconn_s46' if PRIM == 'dconn_s46' else 'dconn']; PN = list(D['perts'])
WF = D['wrel'] if PRIM == 'dconn_w' else None
o8 = sel(T, kind='o8', ds=PRIM, hi=92) & (T['stat8'] <= 1000) & (T['lo'] >= 24)
print('primary', PRIM)
PRIOR_B = ('A', 'B', 'C', 'D', 'E', 'F', 'BD', 'S', 'Bp', 'A+tower1', 'B+tower1', 'A+tower15', 'A+L075', 'B+L075', 'D+L075')
ENS = {
    'prior_crit_prior_grid': o8 & (T['lo'] <= 60) & sel(T, mode='fixed', gap=('orig', 'ext'), base=PRIOR_B) & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4),
    'prior_crit_full_grid': o8 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4),
    'prior_crit_fixed': o8 & (T['rmsc8'] <= 1.125e-7) & (T['dof8'] >= 4) & sel(T, mode='fixed'),
    'near3_8': o8 & (T['fl8'] <= 3) & (T['dof8'] >= 4),
}
idx_all = sorted(set(np.where(np.any(list(ENS.values()), axis=0))[0]))
print('refitting', len(idx_all), 'fits with', len(PN), 'perturbations', flush=True)
t0 = time.time()
R = {}
maxdev = 0.
for i in idx_all:
    c = {k: T[k][i] for k in ('lo', 'hi', 'base', 'mode', 'sh', 'gap', 'low')}
    r = F.fit(L, C, int(c['lo']), int(c['hi']), spec_of(c), float(c['sh']), F.GAPS[c['gap']], maxorder=8,
              free_orders=((5, 6, 7) if c['mode'] == 'free' else ()), hi_low=(118 if c['low'] == 'th118' else None), perts=D['perts'], wfit=WF)
    maxdev = max(maxdev, max(abs(r['lim'][n] - T[f'C{n}'][i]) / abs(REF[n]) for n in range(4, 9)))
    R[i] = {n: np.array([r['dlim'][n][p] for p in PN]) for n in (6, 7, 8)}
print(f'refit done in {time.time() - t0:.1f}s; max rel deviation from scan intercepts {maxdev:.1e}', flush=True)
pidx = {p: j for j, p in enumerate(PN)}


def estimators(c6, c7, c8, c7ref=REF[7]):
    d6 = c6 / REF[6] - 1; d7 = c7 / c7ref - 1
    s67 = (np.abs(d6) <= 1e-4) & (np.abs(c7 - c7ref) <= 82)
    s7 = np.abs(c7 - c7ref) <= 82
    out = dict(med=float(np.median(c8)), sel67=float(np.median(c8[s67])) if s67.any() else np.nan, n67=int(s67.sum()),
               sel7=float(np.median(c8[s7])) if s7.any() else np.nan, n7=int(s7.sum()))
    for name, cols in (('reg7', [d7]), ('reg67', [d6, d7])):
        X = np.column_stack([np.ones(len(c8))] + cols)
        b, *_ = np.linalg.lstsq(X, c8, rcond=None)
        out[name] = float(b[0])
    return out


rng = np.random.default_rng(20261008)
res = {}
for ename, m in ENS.items():
    ii = [i for i in np.where(m)[0]]
    c = {n: np.array([T[f'C{n}'][i] for i in ii]) for n in (6, 7, 8)}
    resp = {n: np.array([R[i][n] for i in ii]) for n in (6, 7, 8)}          # nfit x npert

    def shifted(w):
        """w: dict pert -> weight; returns estimators on C + sum w * response"""
        cc = {n: c[n] + sum(wt * resp[n][:, pidx[p]] for p, wt in w.items()) for n in (6, 7, 8)}
        return estimators(cc[6], cc[7], cc[8])
    base = estimators(c[6], c[7], c[8])
    base_alt = estimators(c[6], c[7], c[8], F.C7_ALT)
    E = dict(n=len(ii), base=base, base_C7alt=base_alt)
    E['edge_all_plus'] = shifted({'unc6': 1, 'unc7': 1, 'unc8': 1})
    E['edge_all_minus'] = shifted({'unc6': -1, 'unc7': -1, 'unc8': -1})
    for k in (6, 7, 8):
        E[f'edge{k}_plus'] = shifted({f'unc{k}': 1}); E[f'edge{k}_minus'] = shifted({f'unc{k}': -1})
    E['typ_all_plus'] = shifted({'typ6': 1, 'typ7': 1, 'typ8': 1}); E['typ_all_minus'] = shifted({'typ6': -1, 'typ7': -1, 'typ8': -1})
    for p in ('dconn_med', 'dconn_mean', 'dconn_model', 'dconn_s46'):
        E['P_' + p] = shifted({'P:' + p: 1})
    # per-order variant sets and joint draws
    for k in (6, 7, 8):
        E[f'step{k}_unit'] = {est: shifted({f'stp{k}': 1})[est] - base[est] for est in ('med', 'sel67', 'sel7', 'reg7', 'reg67')}
    for fam in ('spl', 'evw', 'anc'):
        for k in (6, 7, 8):
            names = [p for p in PN if p.startswith(f'{fam}{k}_')]
            vals = [shifted({p: 1}) for p in names]
            E[f'var_{fam}{k}'] = {est: [v[est] - base[est] for v in vals] for est in ('med', 'sel67', 'sel7', 'reg7', 'reg67')}
            fl = set(D['floor_idx'][k])
            E[f'var_{fam}F{k}'] = {est: [v[est] - base[est] for v, p in zip(vals, names) if int(p.split('_')[1]) in fl] for est in ('med', 'sel67', 'sel7', 'reg7', 'reg67')}
        for tag, pick in ((fam, None), (fam + 'F', 'floor')):
            draws = []
            for _ in range(400):
                w = {}
                for k in (6, 7, 8):
                    pool = [p for p in PN if p.startswith(f'{fam}{k}_')]
                    if pick == 'floor':
                        pool = [p for p in pool if int(p.split('_')[1]) in set(D['floor_idx'][k])]
                    w[pool[rng.integers(len(pool))]] = 1
                draws.append(shifted(w))
            E[f'joint_{tag}'] = {est: [d[est] - base[est] for d in draws] for est in ('med', 'sel67', 'sel7', 'reg7', 'reg67')}
    res[ename] = E
    def sp(x):
        x = np.array(x, float); x = x[np.isfinite(x)]
        return f'[{np.percentile(x, 16):+.0f},{np.percentile(x, 84):+.0f}] ({x.min():+.0f}..{x.max():+.0f})' if len(x) else 'n/a'
    print(f'\n== {ename} (n={len(ii)}): base ' + ' '.join(f'{k}={v:.0f}' if isinstance(v, float) else f'{k}={v}' for k, v in base.items()))
    print('   C7alt base: ' + ' '.join(f'{k}={v:.0f}' if isinstance(v, float) else f'{k}={v}' for k, v in base_alt.items()))
    for est in ('med', 'sel67', 'sel7', 'reg7', 'reg67'):
        print(f'   {est:5s}: edge all +{E["edge_all_plus"][est] - base[est]:+.0f} -{E["edge_all_minus"][est] - base[est]:+.0f}'
              f' | edge6/7/8 + {E["edge6_plus"][est] - base[est]:+.0f}/{E["edge7_plus"][est] - base[est]:+.0f}/{E["edge8_plus"][est] - base[est]:+.0f}'
              f' | typ +{E["typ_all_plus"][est] - base[est]:+.0f} -{E["typ_all_minus"][est] - base[est]:+.0f}'
              f' | P med/mean/model/s46 {E["P_dconn_med"][est] - base[est]:+.0f}/{E["P_dconn_mean"][est] - base[est]:+.0f}/{E["P_dconn_model"][est] - base[est]:+.0f}/{E["P_dconn_s46"][est] - base[est]:+.0f}'
              f' | joint spl {sp(E["joint_spl"][est])} splF {sp(E["joint_splF"][est])} evw {sp(E["joint_evw"][est])}'
              f' anc {sp(E["joint_anc"][est])} ancF {sp(E["joint_ancF"][est])}')

# ---------------------------------------------------------------- explicit (non-linear) edge re-fits
print('\n== explicit re-fits with corrected data +- unc (all orders) vs linear response, 24 members of prior_crit_full_grid')
ii = list(np.where(ENS['prior_crit_full_grid'])[0])
pick = [ii[j] for j in rng.choice(len(ii), size=min(24, len(ii)), replace=False)]
up = sum(D['perts'][f'unc{k}'] for k in (6, 7, 8))
chk = []
for i in pick:
    c = {k: T[k][i] for k in ('lo', 'hi', 'base', 'mode', 'sh', 'gap', 'low')}
    kw = dict(maxorder=8, free_orders=((5, 6, 7) if c['mode'] == 'free' else ()), hi_low=(118 if c['low'] == 'th118' else None), wfit=WF)
    for s in (1, -1):
        r = F.fit(L, C + s * up, int(c['lo']), int(c['hi']), spec_of(c), float(c['sh']), F.GAPS[c['gap']], **kw)
        lin = {n: s * sum(R[i][n][pidx[f'unc{k}']] for k in (6, 7, 8)) for n in (6, 7, 8)}
        act = {n: r['lim'][n] - T[f'C{n}'][i] for n in (6, 7, 8)}
        chk.append(dict(cfg={k: (v if isinstance(v, str) else float(v)) for k, v in c.items()}, sign=s, act=act, lin=lin))
dev = max(abs(x['act'][n] - x['lin'][n]) / max(1e-12, abs(x['lin'][n])) for x in chk for n in (6, 7, 8) if abs(x['lin'][n]) > 1e-9)
print(f'   max |explicit - linear| / |linear| over C6..C8: {dev:.2e}; C8 shifts explicit: ' + ' '.join(f"{x['act'][8]:+.0f}" for x in chk[:12]))
res['explicit_edge_check'] = dict(max_rel_dev=dev, n=len(chk), samples=chk[:8])
res['refit_max_rel_dev'] = maxdev
json.dump(res, open(f'{rd}/propagation{SUF}.json', 'w'), default=float)
