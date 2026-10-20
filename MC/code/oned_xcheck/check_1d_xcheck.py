#!/usr/bin/env python3
"""Exploratory check, existing 1D records only (NOT a protocol decision; FIT_MODEL_V3 and the 1D report are unchanged).

Question (after amendment P1 of the 2D/3D protocols): is the 1D fit-versus-crossing cross-check at Delta_sigma = 0.15 and 0.175
(CROSS-CHECK FAILED at 2.1 and 2.0 sigma_D) conditional on a fixed correction exponent, as the 2D/3D sigma rule was?
FIT_MODEL_V3 already refits every nonlinear parameter (incl. the global correction exponent) in each bootstrap draw of the global fit
(fit_fss.run_fit), and each crossing series re-profiles omega' on the grid in each draw (select_model.crosscheck_series ->
gls_extrapolate). This script (1) reproduces the recorded per-draw crossing values with select_model.gls_extrapolate, (2) recomputes them
at the FIXED central omega' of each series (what a P1-style 'fixed' rule would have done), and (3) recomputes the paired cross-check
(sigma_D = hypot(16-84 half-width of D, model spread), as select_model.paired_comparison) with both, using the recorded global-fit draws.
Usage: check_1d_xcheck.py LRI_CLUSTER_DIR OUTDIR
"""
import hashlib, json, sys, time
from pathlib import Path
import numpy as np

LRI = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(LRI)); import select_model as v2
from scipy.linalg import solve_triangular
RUNS = {'0.15': 'scanA_exp/scan_data/ds0.15/fits_v3_20260920_102519', '0.175': 'scanA_exp/scan_data/ds0.175/fits_v3_20260920_102459'}

def fixed_fit(v, cov, sizes, kinds, om):
    L = np.linalg.cholesky(cov); X = np.zeros((len(v), 3)); X[:, 0] = 1.
    X[:, 1] = np.where(kinds == 0, sizes ** (-om), 0.); X[:, 2] = np.where(kinds == 1, sizes ** (-om), 0.)
    theta = np.linalg.lstsq(solve_triangular(L, X, lower=True), solve_triangular(L, v, lower=True), rcond=None)[0]
    return float(theta[0])

def half(x): q = np.percentile(x, [16, 84]); return float((q[1] - q[0]) / 2)

R = dict(note=__doc__.split('\n')[0], time=time.strftime('%F_%T'), script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         select_model_sha256=hashlib.sha256((LRI / 'select_model.py').read_bytes()).hexdigest(), points={})
for ds, run in RUNS.items():
    d = LRI / run; xf = d / f'xcheck_ds{ds}.json'; X = json.loads(xf.read_text()); smp = np.load(d / f'xcheck_ds{ds}.samples.npz')
    E = X['eligible_distinct']; pc = X['paired']; common = np.array(pc['common_valid_mask'], bool)
    P = dict(run=run, xcheck_sha256=hashlib.sha256(xf.read_bytes()).hexdigest(), eligible=E, recorded=dict(status=pc['status'], difference=pc['paired_difference_central'],
             sigma_D=pc['sigma_D'], z=pc['paired_difference_central'] / pc['sigma_D'], model_spread=pc['model_spread']), series={})
    prof_all, fixed_all = {}, {}
    for n in E:
        sr = X['series'][n]; S = np.asarray(smp[n])[:, sr['row_indices'], :]; valid = np.array(sr['draw_valid'], bool)
        draws8 = np.concatenate([S[:, :, 2], S[:, :, 1]], axis=1); cov = np.array(sr['covariance'])
        sizes = np.array(sr['pairs'] * 2, float); kinds = np.array([0] * 4 + [1] * 4); om = sr['central']['omega']
        prof = np.full(len(valid), np.nan); fixed = np.full(len(valid), np.nan); wdraw = np.full(len(valid), np.nan)
        for k in np.flatnonzero(valid):
            g = v2.gls_extrapolate(draws8[k], cov, sizes, kinds)
            if 'reason' not in g and g['unique'] and np.isfinite(g['Delta_inf']): prof[k] = g['Delta_inf']; wdraw[k] = g['omega']
            fixed[k] = fixed_fit(draws8[k], cov, sizes, kinds, om)
        rec = np.array(sr['per_draw_Delta_inf'], float); conv = np.array(sr['draw_converged'], bool)
        assert np.array_equal(np.isfinite(prof), conv) and np.max(np.abs(prof[conv] - rec[conv])) < 1e-12, n   # (1) reproduction
        c = fixed_fit(np.array(sr['values']), cov, sizes, kinds, om); assert abs(c - sr['central']['Delta_inf']) < 1e-12
        edge = (wdraw[conv] <= v2.OMEGA_GRID[0] + 1e-9) | (wdraw[conv] >= v2.OMEGA_GRID[-1] - 1e-9)
        P['series'][n] = dict(central_omega=om, central_Delta_inf=sr['central']['Delta_inf'], sigma_profiled_16_84=half(prof[conv]), sigma_fixed_16_84=half(fixed[conv]),
                              ratio=half(prof[conv]) / half(fixed[conv]), omega_draw_16_50_84=np.percentile(wdraw[conv], [16, 50, 84]).tolist(),
                              omega_draw_on_edge=float(edge.mean()), max_reproduction_error=float(np.max(np.abs(prof[conv] - rec[conv]))))
        prof_all[n], fixed_all[n] = prof, fixed
    Dk = np.median(np.array([prof_all[n][common] for n in E]), axis=0)
    assert np.max(np.abs(Dk - np.array(pc['per_draw_Delta_inf_median']))) < 1e-12
    gq = Dk + np.array(pc['paired_differences'])   # the quoted global fit's per-draw Delta_epsilon on the common draws (all parameters refitted)
    spread = pc['model_spread']; diff = pc['paired_difference_central']
    for label, per in (('profiled (recorded rule)', prof_all), ('fixed central omega\'', fixed_all)):
        Dm = np.median(np.array([per[n][common] for n in E]), axis=0); D = gq - Dm; sD = float(np.hypot(half(D), spread))
        P[label] = dict(sigma_crossing_16_84=half(Dm), sigma_D=sD, z=diff / sD, passes=bool(abs(diff) <= 2 * sD))
    assert abs(P['profiled (recorded rule)']['sigma_D'] - pc['sigma_D']) < 1e-12
    P['global_fit_sigma_16_84'] = half(gq)
    R['points'][ds] = P
(OUT / 'oned_xcheck.json').write_text(json.dumps(R, indent=1, default=float) + '\n')
L = ['# 1D cross-check at Δσ = 0.15, 0.175: is it already nuisance-aware? (exploratory, existing records only)', '', R['note'] + '.', '',
     f"Script sha256 {R['script_sha256'][:12]}…, select_model.py {R['select_model_sha256'][:12]}…, {R['time']}. Recorded per-draw crossing values reproduced to < 1e-12.", '',
     '| Δσ | series | ω′ central (per-draw 16/50/84 %) | σ crossing, ω′ per draw | σ crossing, fixed ω′ | ratio |', '|---|---|---|---|---|---|']
for ds, P in R['points'].items():
    for n, s in P['series'].items():
        w = s['omega_draw_16_50_84']
        L.append(f"| {ds} | {n} | {s['central_omega']} ({w[0]:.2f}/{w[1]:.2f}/{w[2]:.2f}) | {s['sigma_profiled_16_84']:.5f} | {s['sigma_fixed_16_84']:.5f} | {s['ratio']:.2f} |")
L += ['', '| Δσ | fit − crossing | σ(global fit) | σ_D (recorded: ω′ per draw) → z | σ_D with fixed ω′ → z |', '|---|---|---|---|---|']
for ds, P in R['points'].items():
    a, b = P['profiled (recorded rule)'], P["fixed central omega'"]
    L.append(f"| {ds} | {P['recorded']['difference']:+.5f} | {P['global_fit_sigma_16_84']:.5f} | {a['sigma_D']:.5f} → {a['z']:+.2f} | {b['sigma_D']:.5f} → {b['z']:+.2f} |")
(OUT / 'ONED_XCHECK.md').write_text('\n'.join(L) + '\n'); print('\n'.join(L))
