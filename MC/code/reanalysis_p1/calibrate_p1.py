#!/usr/bin/env python3
"""Amendment P1 §4: calibration of the profiled-ω′ rule on synthetic data (existing records only; no new Monte Carlo of the model).

For every point of both productions (exactly the records the pinned baseline evaluations evaluated) and with the evaluators' own fitting code
(fit_series / truths / extrapolate of evaluate_2d.py rev 6 and evaluate_3d.py rev 2, imported, not re-implemented):
 (a) single-family ensembles q in {U4, U6, U8, Y}: truth = q's recorded fit (Δ_ε, c, ω′*), noise = q's recorded 4×4 bootstrap covariance;
     each synthetic set is fitted as q (A1 stratum (point, q));
 (b) the joint ensemble: truth = the recorded J fit (Δ_ε^J, c_U4^J, c_Y^J, ω′*_J), noise = the recorded 8×8 U4–Y covariance; the halves are
     fitted as U4 and Y and jointly as J (A1 stratum (point, J); A2 cross-check of the point, common true Δ_ε by construction);
 (m) one misspecified family (reported, not an adoption rule): the J truth plus a second correction a·L^(−2ω′*_J) in U4 (else in Y), with a
     chosen so that the noiseless single-series fits reproduce the recorded U4 − Y difference within 2 %; noise as in (b).
Each ensemble has --sets synthetic data sets y ~ N(μ, C), each with --draws synthetic "bootstrap" draws ~ N(y, C). The full §4.3 fit and its
gates run on every set with both σ rules; gate (iii) compares with the synthetic σ of the largest pair (the analogue of the recorded
statistical_stderr, which is the bootstrap σ of that pair). Seeds: SeedSequence([entropy, dim, point index, ensemble index, set index]), so the
result does not depend on the number of workers.

Usage: calibrate_p1.py OUTDIR [--workers N] [--sets 2000] [--draws 500] [--only 2:1.05,3:1.6] [--entropy E]
OUTDIR must not exist (atomic mkdir). Writes CALIBRATION.json (P1-007 header, strata with PASS / FAIL / UNCALIBRATED, A3), CALIBRATION.md,
sets.npz (every synthetic fit) and SHA256SUMS, then makes them read-only. The evaluators accept only --sets 2000 --draws 500.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, platform, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
AMENDMENT = HERE / 'AMENDMENT_PROFILED_SIGMA.md'
EVALUATORS = {2: ROOT / 'LRI_2d_MC/evaluate_2d.py', 3: ROOT / 'LRI_3d_MC/evaluate_3d.py'}
PLANS = {2: ROOT / 'LRI_2d_MC/FIT_MODEL_2D.md', 3: ROOT / 'LRI_3d_MC/FIT_MODEL_3D.md'}
PROD = {2: ROOT / 'LRI_2d_MC/prod', 3: ROOT / 'LRI_3d_MC/prod'}
ENTROPY = 20260930
SINGLE = ('U4', 'U6', 'U8', 'Y'); ENSEMBLES = SINGLE + ('joint', 'misspecified')
REASONS = ('eligible', 'chi2/dof', 'omega interval at the grid boundary', 'sigma resolution (gate iii)', 'other')

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

_EV = {}
def ev(dim):
    """The evaluator module of one dimension, loaded from its file (once per process)."""
    if dim not in _EV:
        spec = importlib.util.spec_from_file_location(f'evaluate_{dim}d_p1cal', EVALUATORS[dim]); m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m); _EV[dim] = m
    return _EV[dim]

def reason_code(s):
    if s.get('eligible'): return 0
    r = s.get('reason', '')
    return 1 if r.startswith('chi2/dof') else 2 if r.startswith("omega' interval") else 3 if r.startswith('sigma_inf') else 4

def fit(E, y, D, nser, sig_ref):
    """One §4.3 fit with the evaluator's extrapolate (all gates), both σ rules; per-draw values kept for the cross-check."""
    try: s = E.extrapolate(y, D, E.PAIRS, nser, sig_ref)
    except Exception as e: s = dict(eligible=False, reason=f'{type(e).__name__}: {e}')
    g = lambda k: s.get(k) if s.get(k) is not None else np.nan
    return dict(eligible=bool(s.get('eligible')), code=reason_code(s), Delta=g('Delta_inf'), sf=g('sigma_inf'), sp=g('sigma_inf_profiled'), omega=g('omega'),
                pd=np.array(s['per_draw']) if 'per_draw' in s else None, pp=np.array(s['per_draw_profiled']) if s.get('per_draw_profiled') is not None else None)

def run_chunk(task):
    """Synthetic sets j0..j1-1 of one ensemble. Returns per-set arrays for every fitted series (and the cross-check for (b)/(m))."""
    dim, pidx, eidx, ens, mu, C, j0, j1, n_draws, entropy = task
    E = ev(dim); n = len(E.PAIRS); Lc = np.linalg.cholesky(C); names = [ens] if ens in SINGLE else ['U4', 'Y', 'J']
    out = {f'{q}_{k}': [] for q in names for k in ('eligible', 'code', 'Delta', 'sf', 'sp', 'omega')}
    if ens not in SINGLE: out.update(x_both=[], x_diff=[], x_sdf=[], x_sdp=[])
    for j in range(j0, j1):
        rng = np.random.default_rng(np.random.SeedSequence([entropy, dim, pidx, eidx, j]))
        y = mu + Lc @ rng.standard_normal(len(mu)); D = y + rng.standard_normal((n_draws, len(mu))) @ Lc.T
        if ens in SINGLE: F = {ens: fit(E, y, D, 1, float(D[:, n - 1].std(ddof=1)))}
        else:
            F = dict(U4=fit(E, y[:n], D[:, :n], 1, float(D[:, n - 1].std(ddof=1))), Y=fit(E, y[n:], D[:, n:], 1, float(D[:, 2 * n - 1].std(ddof=1))),
                     J=fit(E, y, D, 2, float(D[:, n - 1].std(ddof=1))))
        for q in names:
            for k in ('eligible', 'code', 'Delta', 'sf', 'sp', 'omega'): out[f'{q}_{k}'].append(F[q][k])
        if ens not in SINGLE:
            both = F['U4']['eligible'] and F['Y']['eligible']; out['x_both'].append(both)
            if both:   # the evaluator's §4.5 / P1 §3.2 cross-check on the same paired draws
                out['x_diff'].append(F['U4']['Delta'] - F['Y']['Delta']); out['x_sdf'].append(float((F['U4']['pd'] - F['Y']['pd']).std(ddof=1)))
                out['x_sdp'].append(float((F['U4']['pp'] - F['Y']['pp']).std(ddof=1)))
            else: out['x_diff'].append(np.nan); out['x_sdf'].append(np.nan); out['x_sdp'].append(np.nan)
    return (dim, pidx, eidx, j0), {k: np.array(v) for k, v in out.items()}

def central_delta(E, y, C, nser):
    """The central §4.3 profile of extrapolate (same grid, same GLS, same argmin) without draws: used only to construct the misspecified truth."""
    prof = []
    for w in E.OMEGA_GRID:
        try: beta, chi = E.gls(y, C, E.design(E.PAIRS, w, nser)); prof.append((chi, float(beta[0])))
        except np.linalg.LinAlgError: pass
    return prof[int(np.argmin([p[0] for p in prof]))][1]

MIS_RTOL = 0.02   # (m): the achieved noiseless U4 − Y difference must be within 2 % of the recorded one (P1-012)
MIS_AMPS = sorted({0.0} | {sg * 2.0 ** (k / 4) for k in range(-56, 121) for sg in (1.0, -1.0)})   # |a| from 2^-14 to 2^30, quarter octaves

def misspecified_truth(E, TJ, dc, C8):
    """(m): the J truth (common Δ, ω′_J) with a second correction a L^(−2ω′_J) in one series — U4, or Y when no amplitude in U4 works — with
    a such that the noiseless single-series fits give Δ̂_U4 − Δ̂_Y = dc (the recorded difference). The fitted ω′ is a discrete argmin, so the
    difference is only piecewise continuous in a and a sign change can be a jump: the candidates are the scanned amplitudes within tolerance
    (P1-015) and the bisected sign changes of a quarter-octave scan, each accepted only if the achieved difference is within MIS_RTOL·|dc|
    (≥ 1e-6) of the target (P1-012); the smallest accepted |a| is used."""
    L = np.asarray(E.PAIRS, float); n = len(L); D0, (cU, cY), w = TJ['Delta'], TJ['c'], TJ['omega']; tol = max(1e-6, MIS_RTOL * abs(dc))
    mu0 = {'U4': D0 + cU * L ** -w, 'Y': D0 + cY * L ** -w}; Cs = {'U4': C8[:n, :n], 'Y': C8[n:, n:]}; reach = {}
    for tgt in ('U4', 'Y'):
        other = 'Y' if tgt == 'U4' else 'U4'; sgn_t = 1.0 if tgt == 'U4' else -1.0; d_other = central_delta(E, mu0[other], Cs[other], 1)
        f = lambda a: sgn_t * (central_delta(E, mu0[tgt] + a * L ** (-2 * w), Cs[tgt], 1) - d_other) - dc
        vals = [f(a) for a in MIS_AMPS]; reach[tgt] = [float(min(vals) + dc), float(max(vals) + dc)]
        roots = [a for a, fa in zip(MIS_AMPS, vals) if abs(fa) <= tol]   # P1-015: scanned amplitudes already within tolerance are candidates too
        for (a0, f0), (a1, f1) in zip(zip(MIS_AMPS, vals), zip(MIS_AMPS[1:], vals[1:])):
            if np.sign(f0) == np.sign(f1): continue
            lo, hi, flo = a0, a1, f0
            for _ in range(60):
                mid = (lo + hi) / 2; fm = f(mid)
                if np.sign(fm) == np.sign(flo): lo, flo = mid, fm
                else: hi = mid
            roots += [a for a in (lo, hi) if abs(f(a)) <= tol][:1]
        if roots:
            a = min(roots, key=abs); mu = dict(mu0); mu[tgt] = mu0[tgt] + a * L ** (-2 * w)
            return np.concatenate([mu['U4'], mu['Y']]), dict(second_correction_in=tgt, a=float(a), omega2=float(2 * w), target_difference=float(dc),
                                                             achieved_difference=float(f(a) + dc), tolerance=float(tol), reachable_difference_ranges=reach)
    return None, dict(reason=f'no amplitude in U4 or Y reproduces the recorded difference within {MIS_RTOL:.0%}', target_difference=float(dc),
                      tolerance=float(tol), reachable_difference_ranges=reach)

def a1_stratum(r, q, truth):
    e = r[f'{q}_eligible'].astype(bool); err = np.abs(r[f'{q}_Delta'][e] - truth); sp = r[f'{q}_sp'][e]; sf = r[f'{q}_sf'][e]; n = int(e.sum())
    st = dict(n_sets=int(len(e)), n_eligible=n, n_cov1_profiled=int((err <= sp).sum()), n_cov2_profiled=int((err <= 2 * sp).sum()),
              n_cov1_fixed=int((err <= sf).sum()), n_cov2_fixed=int((err <= 2 * sf).sum()),
              ineligible={REASONS[c]: int((r[f'{q}_code'] == c).sum()) for c in range(1, len(REASONS)) if (r[f'{q}_code'] == c).any()})
    for k in ('cov1_profiled', 'cov2_profiled', 'cov1_fixed', 'cov2_fixed'): st[k] = st[f'n_{k}'] / n if n else None
    st['median_sigma_ratio_profiled_over_fixed'] = float(np.median(sp / sf)) if n else None
    return st

def a2_stratum(r):
    b = r['x_both'].astype(bool); n = int(b.sum()); d = np.abs(r['x_diff'][b])
    st = dict(n_sets=int(len(b)), n_both_eligible=n, n_fail_profiled=int((d > 2 * r['x_sdp'][b]).sum()), n_fail_fixed=int((d > 2 * r['x_sdf'][b]).sum()))
    st['false_fail_profiled'] = st['n_fail_profiled'] / n if n else None; st['false_fail_fixed'] = st['n_fail_fixed'] / n if n else None
    return st

def empty(kind, reason):
    return (dict(n_sets=0, n_eligible=0, n_cov1_profiled=0, n_cov2_profiled=0, n_cov1_fixed=0, n_cov2_fixed=0, reason=reason) if kind == 'A1'
            else dict(n_sets=0, n_both_eligible=0, n_fail_profiled=0, n_fail_fixed=0, reason=reason))

def points_of(dim):
    """The primary records of the pinned baseline evaluation (P1-003), located in the local production copy and hash-checked."""
    E = ev(dim); path, sha = E.BASELINE_EVALUATIONS[dim]
    if sha256(ROOT / path) != sha: sys.exit(f'baseline {path} does not have the pinned sha256 {sha}')
    B = json.loads((ROOT / path).read_text()); out = []
    for key, P in B['points'].items():
        d = PROD[dim] / Path(P['inputs']['results']).parent.name
        if sha256(d / 'results.json') != P['inputs']['results_sha256'] or sha256(d / 'bootstrap.npy') != P['inputs']['draws_sha256']:
            sys.exit(f'{d}: record hashes differ from the baseline evaluation')
        out.append((float(P['s']), d, P))
    return path, sha, sorted(out, key=lambda t: t[0])

def calibrate(out_dir, sets=2000, draws=500, only=None, entropy=ENTROPY, workers=1, chunk=100, log=print):
    if sha256(AMENDMENT) != ev(2).AMENDMENT_SHA256 or ev(2).AMENDMENT_SHA256 != ev(3).AMENDMENT_SHA256: sys.exit('amendment is not the approved revision')
    thr = lambda E: dict(A1_min_eligible=E.A1_MIN_ELIGIBLE, A1_cov1_min=E.A1_COV1_MIN, A1_cov2_min=E.A1_COV2_MIN, A2_min_sets=E.A2_MIN_SETS,
                         A2_false_fail_max=E.A2_FALSE_FAIL_MAX, A3_fixed_cov1_max=E.A3_FIXED_COV1_MAX)
    if thr(ev(2)) != thr(ev(3)): sys.exit('the two evaluators disagree on the adoption thresholds')
    records = {dim: points_of(dim) for dim in (2, 3)}   # refuses unless the baselines and records are the pinned ones (P1-003)
    out_dir = Path(out_dir); out_dir.mkdir(parents=True)   # P1-007: a fresh directory, written once
    header = dict(title='Amendment P1 §4 calibration (synthetic data)', amendment=str(AMENDMENT.relative_to(ROOT)), amendment_sha256=sha256(AMENDMENT),
                  calibration_script=str(Path(__file__).resolve().relative_to(ROOT)), calibration_script_sha256=sha256(__file__),
                  evaluators={str(d): dict(path=str(p.relative_to(ROOT)), sha256=sha256(p)) for d, p in EVALUATORS.items()},
                  created=time.strftime('%F_%T'), host=platform.node(), python=sys.version.split()[0], numpy=np.__version__,
                  seed=dict(entropy=int(entropy), scheme='SeedSequence([entropy, dim, point index, ensemble index, set index])'),
                  ensembles=dict(single='truth = the series\' recorded fit, noise = its recorded 4x4 bootstrap covariance',
                                 joint='truth = the recorded J fit, noise = the recorded 8x8 U4-Y covariance; fitted as U4, Y and J',
                                 misspecified='J truth + a L^(-2 omega_J) in U4 (else Y), a reproducing the recorded U4-Y difference within 2 %; reported only',
                                 gate_iii='sigma_stat of the largest pair = the synthetic bootstrap sigma of that pair'),
                  adoption=thr(ev(2)), only=(sorted([list(x) for x in only]) if only is not None else None), dims={})
    tasks = []; meta = {}
    for dim in (2, 3):
        E = ev(dim); bpath, bsha, pts = records[dim]
        Hd = dict(protocol=str(PLANS[dim].relative_to(ROOT)), protocol_sha256=sha256(PLANS[dim]), baseline=bpath, baseline_sha256=bsha,
                  settings=dict(pairs=E.PAIRS, obs=E.OBS, omega_grid=[float(E.OMEGA_GRID[0]), float(E.OMEGA_GRID[-1]), 0.01], omega_margin=E.OMEGA_MARGIN,
                                chi2_dof_max=E.CHI2_DOF_MAX, resolution_max=E.RESOLUTION_MAX, common_valid_frac=E.COMMON_VALID_FRAC, n_sets=int(sets), n_draws=int(draws)),
                  points={})
        for pidx, (s, d, B) in enumerate(pts):
            if only is not None and (dim, E.skey(s)) not in only: continue
            res, dr, byL, order = E.load_point(d); n = len(E.PAIRS)
            H = dict(point_index=pidx, record=str(d.relative_to(ROOT)), results_sha256=sha256(d / 'results.json'), draws_sha256=sha256(d / 'bootstrap.npy'),
                     baseline_eligible=B.get('eligible'), baseline_decision=B.get('decision'), ensembles={})
            if any(L not in byL for L in E.PAIRS):
                H['truth'] = {q: None for q in SINGLE + ('J',)}; H['no_ensembles'] = 'a pre-registered pair is missing'; Hd['points'][E.skey(s)] = H; continue
            S, complete, inputs = E.fit_series(dr, byL, order); T = E.truths(S, inputs); H['truth'] = T
            C = {q: np.cov(inputs[q][1], rowvar=False, ddof=1) for q in inputs}
            for eidx, ens in enumerate(ENSEMBLES):
                mu = None
                if ens in SINGLE and T[ens] is not None:
                    mu = E.design(E.PAIRS, T[ens]['omega'], 1) @ np.array([T[ens]['Delta']] + T[ens]['c']); cov = C[ens]
                    H['ensembles'][ens] = dict(truth=T[ens], mu=mu.tolist())
                elif ens == 'joint' and T['J'] is not None:
                    mu = E.design(E.PAIRS, T['J']['omega'], 2) @ np.array([T['J']['Delta']] + T['J']['c']); cov = C['J']
                    H['ensembles'][ens] = dict(truth=T['J'], mu=mu.tolist())
                elif ens == 'misspecified' and T['J'] is not None and 'Delta_inf' in S['U4'] and 'Delta_inf' in S['Y']:
                    mu, info = misspecified_truth(E, T['J'], S['U4']['Delta_inf'] - S['Y']['Delta_inf'], C['J']); cov = C['J']
                    H['ensembles'][ens] = dict(truth=dict(T['J'], **info), mu=(mu.tolist() if mu is not None else None))
                if mu is None:
                    H['ensembles'].setdefault(ens, dict(truth=None, reason='no recorded fit to build the truth from')); continue
                truth = T['J']['Delta'] if ens in ('joint', 'misspecified') else T[ens]['Delta']
                meta[(dim, pidx, eidx)] = dict(s=s, ens=ens, truth=truth)
                for j0 in range(0, sets, chunk): tasks.append((dim, pidx, eidx, ens, mu, cov, j0, min(sets, j0 + chunk), draws, entropy))
            Hd['points'][E.skey(s)] = H
        header['dims'][str(dim)] = Hd
    log(f'{len(tasks)} tasks ({len(meta)} ensembles x {sets} sets x {draws} draws) on {workers} workers')
    t0 = time.time(); parts = {}
    if workers > 1:
        with Pool(workers) as pool:
            for i, (k, v) in enumerate(pool.imap_unordered(run_chunk, tasks, chunksize=1)):
                parts[k] = v
                if (i + 1) % max(1, len(tasks) // 20) == 0: log(f'  {i + 1}/{len(tasks)} tasks, {time.time() - t0:.0f} s')
    else:
        for t in tasks: k, v = run_chunk(t); parts[k] = v
    R = {}
    for (dim, pidx, eidx, j0) in sorted(parts):
        R.setdefault((dim, pidx, eidx), []).append(parts[(dim, pidx, eidx, j0)])
    R = {k: {f: np.concatenate([c[f] for c in v]) for f in v[0]} for k, v in R.items()}
    strata = {}; info = {}; arrays = {}
    for dim in (2, 3):
        E = ev(dim); strata[str(dim)] = {}; info[str(dim)] = {}
        for key, H in header['dims'][str(dim)]['points'].items():
            st = {}; inf = {}; pidx = H['point_index']
            get = lambda ens: R.get((dim, pidx, ENSEMBLES.index(ens))) if pidx is not None else None
            for q in SINGLE:
                r = get(q); st[q] = a1_stratum(r, q, meta[(dim, pidx, ENSEMBLES.index(q))]['truth']) if r is not None else empty('A1', H['ensembles'].get(q, {}).get('reason') or H.get('no_ensembles', 'no ensemble'))
            r = get('joint')
            if r is not None:
                tJ = meta[(dim, pidx, ENSEMBLES.index('joint'))]['truth']; st['J'] = a1_stratum(r, 'J', tJ); st['crosscheck'] = a2_stratum(r)
                inf['joint_U4_half'] = a1_stratum(r, 'U4', tJ); inf['joint_Y_half'] = a1_stratum(r, 'Y', tJ)
            else:
                why = H['ensembles'].get('joint', {}).get('reason') or H.get('no_ensembles', 'no ensemble'); st['J'] = empty('A1', why); st['crosscheck'] = empty('A2', why)
            r = get('misspecified')
            if r is not None:
                tJ = meta[(dim, pidx, ENSEMBLES.index('misspecified'))]['truth']; b = r['x_both'].astype(bool); d = np.abs(r['x_diff'])
                failp = b & (d > 2 * r['x_sdp']); failf = b & (d > 2 * r['x_sdf']); gate = ~(r['U4_eligible'].astype(bool) & r['Y_eligible'].astype(bool))
                eJ = r['J_eligible'].astype(bool)
                inf['misspecified'] = dict(n_sets=int(len(b)), U4_ineligible=float(1 - r['U4_eligible'].mean()), Y_ineligible=float(1 - r['Y_eligible'].mean()),
                                           J_ineligible=float(1 - eJ.mean()), crosscheck_fail_profiled=float(failp.mean()), crosscheck_fail_fixed=float(failf.mean()),
                                           flagged_profiled=float((gate | failp).mean()), flagged_fixed=float((gate | failf).mean()),
                                           J_bias_mean=(float(np.mean(r['J_Delta'][eJ] - tJ)) if eJ.any() else None),
                                           J_cov1_profiled=(float(np.mean(np.abs(r['J_Delta'][eJ] - tJ) <= r['J_sp'][eJ])) if eJ.any() else None))
            for q, s_ in st.items(): s_['status'] = E.stratum_status('A2' if q == 'crosscheck' else 'A1', s_)
            strata[str(dim)][key] = st; info[str(dim)][key] = inf
            for ens in ENSEMBLES:
                r = get(ens)
                if r is not None:
                    for f, v in r.items(): arrays[f'd{dim}_s{key}_{ens}_{f}'] = v
    A3 = ev(2).a3_pooled(strata)
    n = c1 = c2 = 0
    for dim in strata.values():
        for pt in dim.values():
            for q, s_ in pt.items():
                if q != 'crosscheck' and s_['n_eligible'] >= ev(2).A1_MIN_ELIGIBLE: n += s_['n_eligible']; c1 += s_['n_cov1_profiled']; c2 += s_['n_cov2_profiled']
    cal = dict(header=header, strata=strata, A3=A3, A3_information=dict(profiled_cov1_pooled=(c1 / n if n else None), profiled_cov2_pooled=(c2 / n if n else None)),
               information=info, elapsed_s=round(time.time() - t0, 1),
               note='P1-CALIBRATED status is decided per point by the evaluator from these strata (A1 of every series in E, A2 when U4 and Y are both in E)')
    (out_dir / 'CALIBRATION.json').write_text(json.dumps(cal, indent=1, default=float, allow_nan=False) + '\n')   # P1-010: no NaN / Infinity
    np.savez_compressed(out_dir / 'sets.npz', **arrays)
    (out_dir / 'CALIBRATION.md').write_text(markdown(cal, out_dir))
    (out_dir / 'SHA256SUMS').write_text(''.join(f'{sha256(out_dir / f)}  {f}\n' for f in ('CALIBRATION.json', 'CALIBRATION.md', 'sets.npz')))
    for f in out_dir.iterdir(): f.chmod(0o444)
    out_dir.chmod(0o555)
    log(f'wrote {out_dir} in {time.time() - t0:.0f} s; A3 {A3}')
    return cal

def markdown(cal, out_dir):
    H = cal['header']; f = lambda x, n=3: '—' if x is None else f'{x:.{n}f}'
    L = ['# Amendment P1 calibration (synthetic data)', '',
         f"Amendment sha256 {H['amendment_sha256'][:12]}…; calibration script {H['calibration_script_sha256'][:12]}…; evaluators "
         + ', '.join(f"{d}D {v['sha256'][:12]}…" for d, v in H['evaluators'].items()) + f"; {H['created']} on {H['host']} (python {H['python']}, numpy {H['numpy']}); "
         f"seed entropy {H['seed']['entropy']}; {cal['header']['dims']['2']['settings']['n_sets']} sets × {cal['header']['dims']['2']['settings']['n_draws']} draws per ensemble; "
         f"{cal['elapsed_s']} s.", '',
         f"Adoption: A1 per stratum with ≥ {H['adoption']['A1_min_eligible']} eligible fits: profiled 1σ coverage ≥ {H['adoption']['A1_cov1_min']} and 2σ ≥ "
         f"{H['adoption']['A1_cov2_min']}; A2 per point with ≥ {H['adoption']['A2_min_sets']} sets with U4 and Y eligible: profiled false-failure rate ≤ "
         f"{H['adoption']['A2_false_fail_max']}; A3 pooled fixed-ω′ 1σ coverage < {H['adoption']['A3_fixed_cov1_max']}.", '',
         f"**A3: {'holds' if cal['A3']['holds'] else 'DOES NOT HOLD (amendment withdrawn)'}** — pooled fixed-ω′ 1σ coverage {f(cal['A3']['fixed_cov1_pooled'])} over "
         f"{cal['A3']['n_pooled']} eligible synthetic fits (profiled: 1σ {f(cal['A3_information']['profiled_cov1_pooled'])}, 2σ {f(cal['A3_information']['profiled_cov2_pooled'])}).", '',
         '## A1 strata (coverage of the true Δ_ε by eligible synthetic fits)', '',
         '| dim | s | stratum | eligible / sets | profiled 1σ / 2σ | fixed 1σ / 2σ | median σ_prof/σ_fixed | ineligible (reason: sets) | status |', '|---|---|---|---|---|---|---|---|---|']
    for dim, pts in cal['strata'].items():
        for s, st in pts.items():
            for q in ('U4', 'U6', 'U8', 'Y', 'J'):
                x = st[q]; ine = ', '.join(f'{k}: {v}' for k, v in (x.get('ineligible') or {}).items()) or ('—' if x['n_sets'] else x.get('reason', '—'))
                L.append(f"| {dim}D | {s} | {q} | {x['n_eligible']} / {x['n_sets']} | {f(x.get('cov1_profiled'))} / {f(x.get('cov2_profiled'))} | "
                         f"{f(x.get('cov1_fixed'))} / {f(x.get('cov2_fixed'))} | {f(x.get('median_sigma_ratio_profiled_over_fixed'), 2)} | {ine} | {x['status']} |")
    L += ['', '## A2 cross-check (joint ensemble, common true Δ_ε)', '', '| dim | s | sets with U4 and Y eligible | false failures profiled | fixed | status |', '|---|---|---|---|---|---|']
    for dim, pts in cal['strata'].items():
        for s, st in pts.items():
            x = st['crosscheck']; L.append(f"| {dim}D | {s} | {x['n_both_eligible']} / {x['n_sets']} | {f(x.get('false_fail_profiled'))} | {f(x.get('false_fail_fixed'))} | {x['status']} |")
    L += ['', '## Production points: strata they use (E from the baseline evaluation; the evaluator decides P1-CALIBRATED)', '',
          '| dim | s | baseline decision | E | strata used → P1-CALIBRATED? |', '|---|---|---|---|---|']
    for dim, pts in cal['strata'].items():
        for s, st in pts.items():
            Hp = cal['header']['dims'][dim]['points'][s]; E = Hp.get('baseline_eligible') or []
            used = [(f'A1 {q}', st[q]['status']) for q in E] + ([('A2', st['crosscheck']['status'])] if 'U4' in E and 'Y' in E else [])
            ok = bool(E) and all(v == 'PASS' for _, v in used) and cal['A3']['holds']
            L.append(f"| {dim}D | {s} | {Hp.get('baseline_decision')} | {','.join(E) or '—'} | {', '.join(f'{k} {v}' for k, v in used) or '—'} → {'yes' if ok else 'no'} |")
    L += ['', '## Misspecified family (reported, not an adoption rule): J truth + a·L^(−2ω′_J) in U4 (else Y), achieved U4 − Y within 2 % of the recorded one', '',
          '| dim | s | series: a (achieved U4−Y / target) | U4 / Y / J ineligible | cross-check fails profiled / fixed | flagged (gates or cross-check) profiled / fixed | J bias, J profiled 1σ coverage |',
          '|---|---|---|---|---|---|---|']
    for dim, pts in cal['information'].items():
        for s, inf in pts.items():
            m = inf.get('misspecified'); t = (cal['header']['dims'][dim]['points'][s]['ensembles'].get('misspecified') or {}).get('truth') or {}
            if not m:
                rr = t.get('reachable_difference_ranges') or {}
                L.append(f"| {dim}D | {s} | {t.get('reason', 'unavailable')} (target {t.get('target_difference', float('nan')):+.4f}; reachable "
                         + ', '.join(f'{k} [{v[0]:+.4f}, {v[1]:+.4f}]' for k, v in rr.items()) + ') | | | | |'); continue
            L.append(f"| {dim}D | {s} | {t.get('second_correction_in')}: {t.get('a', float('nan')):.4g} ({t.get('achieved_difference', float('nan')):+.4f} / {t.get('target_difference', float('nan')):+.4f}) | "
                     f"{f(m['U4_ineligible'], 2)} / {f(m['Y_ineligible'], 2)} / {f(m['J_ineligible'], 2)} | {f(m['crosscheck_fail_profiled'], 2)} / {f(m['crosscheck_fail_fixed'], 2)} | "
                     f"{f(m['flagged_profiled'], 2)} / {f(m['flagged_fixed'], 2)} | {f(m['J_bias_mean'], 4)}, {f(m['J_cov1_profiled'], 2)} |")
    return '\n'.join(L) + '\n'

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out', type=Path); p.add_argument('--workers', type=int, default=1); p.add_argument('--sets', type=int, default=2000); p.add_argument('--draws', type=int, default=500)
    p.add_argument('--only', help='comma list dim:s (tests only; an evaluator rejects a calibration without every point)'); p.add_argument('--entropy', type=int, default=ENTROPY)
    a = p.parse_args()
    only = None if not a.only else {(int(x.split(':')[0]), str(round(float(x.split(':')[1]), 10))) for x in a.only.split(',')}
    calibrate(a.out, a.sets, a.draws, only, a.entropy, a.workers, log=lambda m: print(m, flush=True))

if __name__ == '__main__': main()
