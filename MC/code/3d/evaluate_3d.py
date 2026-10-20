#!/usr/bin/env python3
"""FIT_MODEL_3D §4 evaluator (revision 2 = revision 1 plus amendment P1): the d = 3 instance of evaluate_2d.py revision 5 (FIT2D-001..016) with the constant block replaced (pairs 8→16 … 64→128,
D3/D4 of FIT_MODEL_3D). Everything below the constants is identical to evaluate_2d.py.

Usage: evaluate_3d.py --primary DIR [DIR ...] --reblock DIR [DIR ...] --plan FIT_MODEL_3D.md --manifest CAMPAIGN/manifest.json --centers production_centers_3d.csv
                      [--extensions extensions.json] --out OUT
  DIR = one point (one s) at one block size: results.json + bootstrap.npy. --primary is block 2000; --reblock must supply blocks 1000 and 4000
  for every primary point (REBLOCKING UNAVAILABLE otherwise). Production records need bootstrap 500 with the pre-registered seed.
Pre-registered pair list: (8,16), (16,32), (32,64), (64,128). A pair absent from a record is a coverage failure, never a shorter fit.
Amendment P1 (LRI_2d3d_reanalysis/AMENDMENT_PROFILED_SIGMA.md, approved revision 4, sha256 2a18c0ae…) adds:
  --sigma-rule {fixed,profiled}  fixed (default) = the frozen rule above, unchanged; profiled = amendment §3 for every point whose calibration
                                 strata all pass (P1-CALIBRATED), the complete fixed-rule evaluation for every other point (per point, atomic: P1-006)
  --calibration CALIBRATION.json required with profiled (calibrate_p1.py); its header is checked against these inputs before any row is used (P1-007)
  --amendment AMENDMENT.md       required with profiled; must hash to the approved amendment
  --index-remap OLD=NEW          operational deviation, recorded in the output: a histogram index recorded under the path prefix OLD is read from
                                 NEW (restored from the archive after the cluster copy was deleted); its hash must still equal the record's
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys, time, types
from pathlib import Path
import numpy as np

PAIRS = [8, 16, 32, 64]                        # smaller size of every pre-registered doubling pair
OBS = {'U4': 2, 'U6': 3, 'U8': 4, 'Y': 1}          # column in the analysis value vector [beta, Y, U4, U6, U8]
OMEGA_GRID = np.round(np.arange(0.2, 2.0 + 1e-9, 0.01), 2); OMEGA_MARGIN = 0.02
CHI2_DOF_MAX = 2.0; COMMON_VALID_FRAC = 0.9; ESS_MIN = 0.5; RATIO_LABEL = 3.0; REBLOCK_TOL = 0.30; RESOLUTION_MAX = 5.0
DRIFT_Z_MAX = 4.0; BLOCK_OVER_TAU_MIN = 20.0; POP_Z_HARD = 4.0; POP_Z_SOFT = 3.0; POP_FRAC_MAX = 0.02
PRODUCTION_BOOTSTRAP = 500; PRODUCTION_SEED = 571239; PRODUCTION_MIN_ESS = 0.2; PRIMARY_BLOCK = 2000; REBLOCKS = (1000, 4000); TARGET_SIGMA = 0.003; DIM = 3   # FIT_MODEL_3D criterion 2 (64->128)
# frozen production design (FIT_MODEL_3D D1–D4): the manifest and every chain must match it (FIT2D-002)
DESIGN = dict(replicas=12, measurements=1000000, warmup=50000, beta_points=5, sizes=[8, 16, 32, 64, 128], s=[1.55, 1.6, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95],
              beta_halfwidth=0.001, window_exponent=1.0, reference_length=16)   # FIT_MODEL_3D D3 (frozen 2026-09-21 from stage 0)
assert None not in (DESIGN['beta_halfwidth'], DESIGN['window_exponent']), 'evaluate_3d.py: D3 window constants not yet frozen (FIT_MODEL_3D D3)'

# Amendment P1 (approved revision 4): pinned identities and the §4 adoption thresholds (A1–A3), shared with calibrate_p1.py
AMENDMENT_SHA256 = '2a18c0ae3ae7b3f4fa5db8b83df0fb5a1d57eecd79d1603bdf04bcc7207574d0'
BASELINE_EVALUATIONS = {2: ('LRI_2d_MC/prod/evaluation_20260922_083649/evaluation_2d.json', 'fbfc0ef980a060d526c03fde6f1ec08e38ffec2d0099675ef13ec160542f552d'),
                        3: ('LRI_3d_MC/prod/evaluation_54387089_20260923_194523/evaluation_3d.json', 'ae9cf237d9eb9ba484ab44486882a6dafdedb5fae1a575a1ae2f1d38533755e0')}
FROZEN_PLAN_SHA256 = {2: '4d2efc635701a4ad699dae4b3acb948dc27f9709a947754a47523e65f129acfb', 3: '682858f0327f7dbd051353ffd44ab3dd2e6de51b10371b93775e24ab6687ea4c'}   # FIT_MODEL_2D.md / FIT_MODEL_3D.md
CAL_SETS = 2000; CAL_DRAWS = 500   # §4: synthetic data sets per ensemble, synthetic bootstrap draws per set
A1_MIN_ELIGIBLE = 200; A1_COV1_MIN = 0.60; A1_COV2_MIN = 0.90; A2_MIN_SETS = 200; A2_FALSE_FAIL_MAX = 0.10; A3_FIXED_COV1_MAX = 0.60
TRUTH_TOL = 1e-9   # P1-007: calibration truths vs this evaluator's own fit of the same records (absolute; allows cross-machine rounding only)
ROOT = Path(__file__).resolve().parent.parent   # the repository: P1-008 binds the calibration to the code in it
EVALUATOR_PATHS = {2: 'LRI_2d_MC/evaluate_2d.py', 3: 'LRI_3d_MC/evaluate_3d.py'}; CALIBRATION_SCRIPT = 'LRI_2d3d_reanalysis/calibrate_p1.py'
STRATA_KEYS = ('U4', 'U6', 'U8', 'Y', 'J', 'crosscheck'); SERIES_KEYS = ('U4', 'U6', 'U8', 'Y', 'J')

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def gls(y, C, X):
    Ci = np.linalg.inv(C); A = X.T @ Ci @ X; beta = np.linalg.solve(A, X.T @ Ci @ y); r = y - X @ beta
    return beta, float(r @ Ci @ r)

def design(L, omega, nser):
    """[Δ_ε, c_1 .. c_nser] for nser concatenated series over the same L (common Δ_ε and ω′, separate amplitudes)."""
    L = np.asarray(L, float); n = len(L); X = np.zeros((n * nser, 1 + nser)); X[:, 0] = 1
    for k in range(nser): X[k * n:(k + 1) * n, 1 + k] = L ** (-omega)
    return X

def profile_draws(D, C, L, nser):
    """Amendment P1 §3.1: every draw re-profiled over OMEGA_GRID with the SAME covariance C; Δ_ε at the draw's own minimising ω′ (ties to the
    smaller grid index, as np.argmin). Vectorised per-grid projector of LRI_2d3d_reanalysis/reanalyse.py (the reference implementation).
    Returns the per-draw Δ_ε and the per-draw ω′ distribution; draws whose minimum lies on a grid edge are kept and counted."""
    Ci = np.linalg.inv(C); Pg = []; Rg = []; wg = []
    for w in OMEGA_GRID:
        X = design(L, w, nser)
        try: M = np.linalg.solve(X.T @ Ci @ X, X.T @ Ci)   # beta = M y
        except np.linalg.LinAlgError: continue   # as in the central profile, a grid point without a GLS solution is skipped
        Pg.append(M[0]); Rg.append(np.eye(len(C)) - X @ M); wg.append(float(w))
    Pg = np.array(Pg); Rg = np.array(Rg); wg = np.array(wg)
    d = np.einsum('gn,...n->...g', Pg, D); r = np.einsum('gmn,...n->...gm', Rg, D); chi = np.einsum('...gm,mk,...gk->...g', r, Ci, r)
    kk = np.argmin(chi, axis=1); prof = d[np.arange(len(D)), kk]; wd = wg[kk]; edge = (kk == 0) | (kk == len(wg) - 1)
    return prof, dict(median=float(np.median(wd)), p16=float(np.percentile(wd, 16)), p84=float(np.percentile(wd, 84)), draws_on_edge=int(edge.sum()),
                      fraction_on_edge=float(edge.mean()))

def p1_information(out, D, C, L, nser, w, fixed):
    """P1 §3.5, information only (never a gate, P1-013): the profiled σ and the per-draw ω′ distribution of every fitted series and, for a series
    stopped by a gate before (iii), the fixed-ω′ σ it would have had (the frozen sigma_inf exists only for series that reach gate iii)."""
    try:
        prof, wdist = profile_draws(D, C, L, nser); out.update(sigma_inf_profiled=float(prof.std(ddof=1)), per_draw_profiled=prof.tolist(), omega_draws=wdist)
    except Exception as e: out.update(sigma_inf_profiled=None, profiled_error=f'{type(e).__name__}: {e}')
    if fixed:
        try: X = design(L, w, nser); out['sigma_inf_fixed_information'] = float(np.array([gls(D[i], C, X)[0][0] for i in range(len(D))]).std(ddof=1))
        except Exception as e: out['sigma_inf_fixed_information'] = None
    return out

def extrapolate(y, D, L, nser, sig_ref):
    """ω′-profiled GLS of Δ_eff(L) = Δ_ε + c L^(−ω′). y: central values (nser·n), D: complete draws (nd × nser·n); eligibility per §4.3."""
    n = len(L); out = dict(eligible=False, complete_draws=int(len(D)))
    C = np.cov(D, rowvar=False, ddof=1)
    if np.linalg.matrix_rank(C) < C.shape[0]: out['reason'] = 'singular covariance'; return out
    prof = []
    for w in OMEGA_GRID:
        try: beta, chi = gls(y, C, design(L, w, nser)); prof.append((float(w), float(beta[0]), chi))
        except np.linalg.LinAlgError: pass
    if not prof: out['reason'] = 'GLS failed'; return out
    k = int(np.argmin([p[2] for p in prof])); w, d, chi = prof[k]; dof = nser * n - (1 + nser) - 1   # ω′ profiled counts as a parameter
    inside = [p for p in prof if p[2] <= chi + 1.0]; wlo, whi = min(p[0] for p in inside), max(p[0] for p in inside)
    out.update(omega=w, Delta_inf=d, chi2=chi, dof=dof, omega_interval=[wlo, whi], Delta_omega=float((max(p[1] for p in inside) - min(p[1] for p in inside)) / 2))
    if dof < 1: out['reason'] = 'no degree of freedom'; return p1_information(out, D, C, L, nser, w, True)
    if chi / dof > CHI2_DOF_MAX: out['reason'] = f'chi2/dof {chi/dof:.2f} > {CHI2_DOF_MAX}'; return p1_information(out, D, C, L, nser, w, True)
    if wlo <= OMEGA_GRID[0] + OMEGA_MARGIN + 1e-9 or whi >= OMEGA_GRID[-1] - OMEGA_MARGIN - 1e-9: out['reason'] = f"omega' interval [{wlo}, {whi}] reaches the grid boundary (unresolved)"; return p1_information(out, D, C, L, nser, w, True)
    X = design(L, w, nser); per_draw = np.array([gls(D[i], C, X)[0][0] for i in range(len(D))]); sig = float(per_draw.std(ddof=1))
    out.update(sigma_inf=sig, per_draw=per_draw.tolist())
    p1_information(out, D, C, L, nser, w, False)   # P1 §3.1/§3.5: the profiled σ; gate (iii) below keeps the fixed σ (§3.3)
    if sig_ref and sig > RESOLUTION_MAX * sig_ref: out['reason'] = f'sigma_inf {sig:.4f} > {RESOLUTION_MAX} x sigma_stat(largest pair) {sig_ref:.4f}'; return out
    out['eligible'] = True; return out

def load_point(d: Path):
    res = json.loads((d / 'results.json').read_text()); draws = np.load(d / 'bootstrap.npy')
    byL = {r['L']: r for r in res['rows']}; order = list(res['joint_pair_order'])
    return res, draws, byL, order

def fit_series(draws, byL, order):
    """§4.3 fits of one record with every pair present: U4, U6, U8, Y individually and the joint series J (common Δ_ε and ω′ for U4 and Y,
    separate amplitudes). Shared by evaluate_point and calibrate_p1.py, so the calibration truths are this evaluator's own fits.
    Returns (series fits, number of complete draws, fit inputs {q: (central y, complete draws, families, σ_stat of the largest pair)})."""
    S = {}; inputs = {}
    idx = [order.index(L) for L in PAIRS]; ok = np.isfinite(draws[:, idx, :]).all(axis=(1, 2)); Dk = draws[ok]
    enough = ok.sum() >= COMMON_VALID_FRAC * len(draws)
    for q, col in OBS.items():
        y = np.array([byL[L]['values'][col] for L in PAIRS]); D = Dk[:, idx, col]; sig_ref = (byL[PAIRS[-1]].get('statistical_stderr') or [None] * 5)[col]
        S[q] = extrapolate(y, D, PAIRS, 1, sig_ref) if enough else dict(eligible=False, reason=f'only {ok.sum()} of {len(draws)} complete draws')
        S[q].update(central=y.tolist()); inputs[q] = (y, D, 1, sig_ref)
    # joint series J: common Δ_ε and ω′ for U4 and Y, separate amplitudes (8 values, 4 parameters incl. ω′)
    yJ = np.concatenate([[byL[L]['values'][OBS['U4']] for L in PAIRS], [byL[L]['values'][OBS['Y']] for L in PAIRS]])
    DJ = np.concatenate([Dk[:, idx, OBS['U4']], Dk[:, idx, OBS['Y']]], axis=1)
    sig_refJ = (byL[PAIRS[-1]].get('statistical_stderr') or [None] * 5)[OBS['U4']]
    S['J'] = extrapolate(yJ, DJ, PAIRS, 2, sig_refJ) if enough else dict(eligible=False, reason='insufficient complete draws')
    S['J'].update(central=yJ.tolist()); inputs['J'] = (yJ, DJ, 2, sig_refJ)
    return S, int(ok.sum()), inputs

def truths(S, inputs):
    """P1-007: the fitted parameters (Δ_ε, amplitudes c, ω′*) of every series of a record — the truths the §4 ensembles are built from."""
    T = {}
    for q, (y, D, nser, _) in inputs.items():
        if 'omega' not in S.get(q, {}): T[q] = None; continue
        beta, _ = gls(np.asarray(y, float), np.cov(D, rowvar=False, ddof=1), design(PAIRS, S[q]['omega'], nser))
        T[q] = dict(Delta=float(beta[0]), c=[float(x) for x in beta[1:]], omega=float(S[q]['omega']))
    return T

def drop_smallest(y, D, omega):
    """Amendment P1 §6 R4, reported with a changed label (information, not a gate): the two-parameter fit (Δ_ε, c) at the series' central ω′*
    to the three largest pairs only (covariance of those pairs), as reanalyse.cutoff."""
    y3 = np.asarray(y, float)[1:]; D3 = np.asarray(D)[:, 1:]; C3 = np.cov(D3, rowvar=False, ddof=1); X = design(PAIRS[1:], omega, 1)
    beta, chi = gls(y3, C3, X); per = np.array([gls(D3[i], C3, X)[0][0] for i in range(len(D3))])
    return dict(Delta_inf=float(beta[0]), sigma=float(per.std(ddof=1)), chi2=float(chi), dof=1, omega=float(omega), pairs=[f'{L}->{2*L}' for L in PAIRS[1:]])

def skey(s): return str(round(float(s), 10))

def stratum_status(kind, st):
    """§4 A1 (kind 'A1': a series stratum) and A2 (kind 'A2': the cross-check of a point) from the recorded counts."""
    if kind == 'A1':
        n = st['n_eligible']
        if n < A1_MIN_ELIGIBLE: return 'UNCALIBRATED'
        return 'PASS' if st['n_cov1_profiled'] >= A1_COV1_MIN * n and st['n_cov2_profiled'] >= A1_COV2_MIN * n else 'FAIL'
    n = st['n_both_eligible']
    if n < A2_MIN_SETS: return 'UNCALIBRATED'
    return 'PASS' if st['n_fail_profiled'] <= A2_FALSE_FAIL_MAX * n else 'FAIL'

def a3_pooled(strata):
    """§4 A3: fixed-ω′ 1σ coverage pooled over every calibrated A1 stratum (n_eligible ≥ A1_MIN_ELIGIBLE) of every dimension."""
    n = c = 0
    for dim in strata.values():
        for pt in dim.values():
            for q, st in pt.items():
                if q != 'crosscheck' and st['n_eligible'] >= A1_MIN_ELIGIBLE: n += st['n_eligible']; c += st['n_cov1_fixed']
    return dict(n_pooled=n, fixed_cov1_pooled=(c / n if n else None), holds=bool(n and c < A3_FIXED_COV1_MAX * n))

def fin(x):
    try: return np.isfinite(float(x))
    except (TypeError, ValueError): return False

def population_rule(res, replicas):
    """§4.1: per (L, β) group of `replicas` chains (hot/cold balanced), pull of every chain's m² block mean against the group mean (block
    standard errors); hard |z| ≤ 4, ≤ 2 % above 3; non-finite or zero diagnostics flag the chain (FIT2D-006); short groups are incomplete (FIT2D-002)."""
    groups = {}
    for c in res['chains']: groups.setdefault((c['L'], round(c['beta'], 12)), []).append(c)
    pulls = []; flagged = {}; incomplete = []
    for key, cs in groups.items():
        inits = [c.get('initialization') for c in cs]
        if len(cs) != replicas or abs(inits.count('hot') - inits.count('cold')) > 1: incomplete.append(dict(group=list(key), chains=len(cs), hot=inits.count('hot'), cold=inits.count('cold')))
        for c in cs:
            bad = []
            if not fin(c.get('half_drift_z')) or abs(c['half_drift_z']) > DRIFT_Z_MAX: bad.append('drift')
            if not fin(c.get('block_over_max_tau')) or c['block_over_max_tau'] < BLOCK_OVER_TAU_MIN: bad.append('tau')
            if not fin(c.get('m2_block_stderr')) or c['m2_block_stderr'] <= 0 or not fin(c.get('m2_mean')): bad.append('degenerate')
            if bad: flagged[c['task_id']] = bad
        good = [c for c in cs if 'degenerate' not in flagged.get(c['task_id'], [])]
        if len(good) < 2: continue
        m = np.array([c['m2_mean'] for c in good]); e = np.array([c['m2_block_stderr'] for c in good]); wgt = 1 / e ** 2; mean = float((wgt * m).sum() / wgt.sum())
        for c, mi, ei in zip(good, m, e): pulls.append((c['task_id'], float((mi - mean) / ei)))
    z = np.array([p[1] for p in pulls]) if pulls else np.zeros(0)
    hard = [p for p in pulls if abs(p[1]) > POP_Z_HARD]; soft = float(np.mean(np.abs(z) > POP_Z_SOFT)) if len(z) else 0.0
    lost = [list(k) for k, cs in groups.items() if sum(c['task_id'] in flagged for c in cs) * 2 >= len(cs)]
    passed = not hard and soft <= POP_FRAC_MAX and not lost
    return dict(passed=passed, groups=len(groups), chains=len(res['chains']), hard_outliers=hard, fraction_above_3=soft, flagged_tasks=flagged, groups_without_consensus=lost, incomplete_groups=incomplete)

def design_checks(manifest, centers):
    """FIT2D-002: the campaign manifest must be the frozen production design, including the temperature design (D3): every task's β must
    equal centre(s, L) ± w16 (L/16)^-p on 5 points from the frozen centres table (D3 of FIT_MODEL_3D)."""
    c = manifest['config']; bad = []
    for k in ('replicas', 'measurements', 'warmup', 'beta_points'):
        if c.get(k) != DESIGN[k]: bad.append(f'manifest {k}={c.get(k)} != {DESIGN[k]}')
    for k in ('beta_halfwidth', 'window_exponent', 'reference_length'):
        if c.get(k) is None or abs(float(c[k]) - DESIGN[k]) > 1e-12: bad.append(f'manifest {k}={c.get(k)} != {DESIGN[k]}')
    if sorted(c.get('sizes', [])) != DESIGN['sizes']: bad.append(f"manifest sizes {c.get('sizes')} != {DESIGN['sizes']}")
    if sorted(round(x, 10) for x in c.get('s', [])) != DESIGN['s']: bad.append(f"manifest s {c.get('s')} != {DESIGN['s']}")
    off = 0
    for t in manifest['tasks']:
        key = (round(t['s'], 10), t['L']); ctr = centers.get(key)
        if ctr is None: off += 1; continue
        w = DESIGN['beta_halfwidth'] * (t['L'] / DESIGN['reference_length']) ** (-DESIGN['window_exponent'])
        grid = ctr + np.linspace(-w, w, DESIGN['beta_points'])
        if np.min(np.abs(grid - t['beta'])) > 1e-12: off += 1
    if off: bad.append(f'{off} manifest tasks have temperatures outside the frozen D3 grid (centres table + window rule)')
    # FIT3D-007: the task list itself must be the full registered Cartesian product with unique identities and per-task design settings
    exp = {(round(s, 10), L, bi, rep) for s in DESIGN['s'] for L in DESIGN['sizes'] for bi in range(DESIGN['beta_points']) for rep in range(DESIGN['replicas'])}
    seen = set(); dup = 0; badtask = 0
    for t in manifest['tasks']:
        key = (round(t['s'], 10), t['L'], t.get('beta_index'), t.get('replica'))
        if key in seen: dup += 1
        seen.add(key)
        if t.get('d') != DIM or t.get('measurements') != DESIGN['measurements'] or t.get('warmup') != DESIGN['warmup'] or t.get('nn_extra', 0) != 0: badtask += 1
    ids = [t['id'] for t in manifest['tasks']]
    if len(set(ids)) != len(ids): bad.append('duplicate task ids in the manifest')
    if dup: bad.append(f'{dup} duplicate (s, L, beta_index, replica) tasks in the manifest')
    missing = exp - seen; extra = seen - exp
    if missing or extra: bad.append(f'manifest task grid != registered design: {len(missing)} (s, L, beta, replica) cells missing, {len(extra)} unregistered')
    if badtask: bad.append(f'{badtask} tasks with d, measurements, warmup or nn_extra outside the frozen design')
    return bad

def load_centers(path):
    import csv
    out = {}
    for r in csv.DictReader(open(path)):
        if int(r['d']) != DIM or not r.get('L', '').strip(): continue
        out[(round(float(r['s']), 10), int(r['L']))] = float(r['beta'])
    return out

def remap_path(p, remap):
    """--index-remap (operational deviation): the first OLD prefix that matches is replaced by its NEW prefix."""
    for old, new in remap or ():
        if p and p.startswith(old): return new + p[len(old):]
    return p

def record_checks(res, manifest, manifest_sha, role, require_index=True, allowed_total=None, index_remap=None):
    """FIT2D-001/002/007: a production record shares the campaign identity with the manifest, uses the §4.1 settings, holds every chain of its
    point at the frozen measurement count, and its provenance chain (index hash, raw and binary identities) verifies."""
    bad = []
    if res.get('campaign_id') != manifest['campaign_id']: bad.append(f'{role}: campaign_id {res.get("campaign_id")} != manifest {manifest["campaign_id"]}')
    if res.get('manifest_sha256') != manifest_sha: bad.append(f'{role}: manifest hash in the record ({str(res.get("manifest_sha256"))[:12]}) != supplied manifest ({manifest_sha[:12]})')
    if res.get('bootstrap') != PRODUCTION_BOOTSTRAP or res.get('bootstrap_seed') != PRODUCTION_SEED: bad.append(f'{role}: bootstrap {res.get("bootstrap")} seed {res.get("bootstrap_seed")}')
    if res.get('min_ess') is None: bad.append(f'{role}: min_ess unrecorded')
    elif abs(res['min_ess'] - PRODUCTION_MIN_ESS) > 1e-12: bad.append(f'{role}: min_ess {res["min_ess"]}')
    if any(min(r['diagnostics']['ESS_fraction']) < PRODUCTION_MIN_ESS for r in res['rows']): bad.append(f'{role}: a crossing with ESS below {PRODUCTION_MIN_ESS} was accepted')
    if res.get('d') != DIM or res.get('nn_extra', 0) != 0: bad.append(f'{role}: d={res.get("d")} nn_extra={res.get("nn_extra")}')
    expected = sorted(t['id'] for t in manifest['tasks'] if abs(t['s'] - res['s']) < 1e-10)
    have = sorted(c['task_id'] for c in res['chains'])
    if have != expected: bad.append(f'{role}: {len(have)} of {len(expected)} chains of this point in the record (incomplete campaign or wrong index)')
    total = allowed_total or DESIGN['measurements']   # FIT2D-015: a registered extension (extensions.json) raises the required total for the point
    short = [c['task_id'] for c in res['chains'] if c.get('measurements') != total or c.get('used') != total]
    if short: bad.append(f'{role}: {len(short)} chains not at the required {total} measurements (e.g. {short[:3]})')
    if any(not c.get('raw_sha256') for c in res['chains']): bad.append(f'{role}: raw_sha256 missing for some chains (packed with an older pack_histograms)')
    bins = {c.get('binary_sha256') for c in res['chains']}
    if None in bins or len(bins) != 1: bad.append(f'{role}: binary identity missing or not unique across chains ({len(bins)} values)')
    if require_index:
        ip = remap_path(res.get('index_path'), index_remap)
        if not ip or not Path(ip).exists(): bad.append(f'{role}: histogram index {ip} not accessible for verification')
        elif sha256(ip) != res.get('index_sha256'): bad.append(f'{role}: histogram index changed since the analysis (hash mismatch)')
        else:
            idx = json.loads(Path(ip).read_text())
            if idx.get('manifest_sha256') != manifest_sha: bad.append(f'{role}: index manifest hash != supplied manifest')
    return bad

def same_raw(res_a, res_b, role):
    """FIT2D-007: primary and reblock records must come from the same raw snapshot (identical per-chain raw hashes)."""
    a = {c['task_id']: c.get('raw_sha256') for c in res_a['chains']}; b = {c['task_id']: c.get('raw_sha256') for c in res_b['chains']}
    diff = [t for t in a if t in b and a[t] != b[t]]
    return [f'{role}: raw chain hashes differ from the primary for {len(diff)} chains (different raw snapshot, e.g. before/after an extension)'] if diff else []

def evaluate_point(d: Path, reblock_dirs: list[Path], plan_sha, manifest, manifest_sha, centers, extensions, require_index=True, index_remap=None):
    res, draws, byL, order = load_point(d); replicas = DESIGN['replicas']; total = int(extensions.get(round(float(res['s']), 10), DESIGN['measurements']))
    P = dict(s=res['s'], Delta_sigma=res['Delta_sigma'], block=res['block'], bootstrap=res['bootstrap'], bootstrap_seed=res['bootstrap_seed'],
             inputs=dict(results=str(d / 'results.json'), results_sha256=sha256(d / 'results.json'), draws_sha256=sha256(d / 'bootstrap.npy'), plan_sha256=plan_sha,
                         manifest_sha256=manifest_sha, campaign_id=res.get('campaign_id'), index_path=res.get('index_path'), index_sha256=res.get('index_sha256'),
                         analysis_code_sha256=res.get('code_sha256')))
    if index_remap: P['inputs']['index_path_read'] = remap_path(res.get('index_path'), index_remap)
    nonprod = []
    if res['block'] != PRIMARY_BLOCK: nonprod.append(f'primary block {res["block"]} != {PRIMARY_BLOCK}')
    nonprod += design_checks(manifest, centers) + record_checks(res, manifest, manifest_sha, 'primary', require_index, total, index_remap)
    if not require_index: nonprod.append('index verification disabled (--no-index-check preview)')   # FIT2D-016
    P['required_measurements'] = total
    P['equilibration'] = population_rule(res, replicas)
    if P['equilibration']['incomplete_groups']: nonprod.append(f"{len(P['equilibration']['incomplete_groups'])} (L, beta) groups without {replicas} balanced chains")
    P['production'] = not nonprod; P['non_production_reasons'] = nonprod
    missing = [L for L in PAIRS if L not in byL]; P['missing_pairs'] = [f'{L}->{2*L}' for L in missing]
    P['analysis_warnings'] = res['warnings']
    present = [L for L in PAIRS if L in byL]
    ess_bad = [f"{L}->{2*L}: ESS {min(byL[L]['diagnostics']['ESS_fraction']):.2f}" for L in PAIRS[-2:] if L in byL and min(byL[L]['diagnostics']['ESS_fraction']) < ESS_MIN]
    P['coverage'] = dict(passed=not missing and not ess_bad, missing=P['missing_pairs'], low_ess=ess_bad)
    largest = [dict(pair=f'{L}->{2*L}', Delta_eff_U4=byL[L]['values'][2], sigma_U4=(byL[L].get('statistical_stderr') or [None] * 5)[2],
                    Delta_eff_Y=byL[L]['values'][1], sigma_Y=(byL[L].get('statistical_stderr') or [None] * 5)[1]) for L in present[-2:]]
    P['largest_pairs'] = largest
    top = byL.get(PAIRS[-1]); sig_top = (top.get('statistical_stderr') or [None] * 5)[2] if top else None   # FIT2D-005: criterion 2 is about 64->128 only
    P['precision'] = dict(target=TARGET_SIGMA, pair=f'{PAIRS[-1]}->{2*PAIRS[-1]}', sigma_U4=sig_top, met=(sig_top is not None and sig_top <= TARGET_SIGMA), known=sig_top is not None)
    S = {}; E = []; inputs = {}
    if not missing:
        S, P['complete_draws'], inputs = fit_series(draws, byL, order)
        seen = {}
        for q in ('U4', 'U6', 'U8', 'Y', 'J'):
            if not S[q]['eligible']: continue
            key = tuple(np.round(S[q]['central'], 12))
            if key in seen: S[q]['duplicate_of'] = seen[key]; continue
            seen[key] = q; E.append(q)
    P['series'] = {q: {k: v for k, v in s.items() if k not in ('per_draw', 'per_draw_profiled')} for q, s in S.items()}; P['eligible'] = E
    quoted = None; xcheck = dict(status='unavailable'); xprof = None
    if E:
        ref = 'J' if 'J' in E else ('U4' if 'U4' in E else E[0])
        vals = {q: S[q]['Delta_inf'] for q in E}; med_q = sorted(E, key=lambda q: vals[q])[len(E) // 2]
        sig_sys = (max(vals.values()) - min(vals.values())) / 2 + S[ref]['Delta_omega'] if len(E) >= 2 else None
        quoted = dict(Delta_epsilon=S[ref]['Delta_inf'], sigma_stat=S[ref]['sigma_inf'], sigma_sys=sig_sys, reference_series=ref, omega=S[ref]['omega'],
                      omega_interval=S[ref]['omega_interval'], Delta_omega=S[ref]['Delta_omega'], values=vals, median_series=med_q,
                      note='Delta_epsilon and sigma_stat from the reference series (J, else U4); sigma_sys = half-range over E + the reference omega-profile half-range')
        quoted['sigma_stat_profiled'] = S[ref].get('sigma_inf_profiled')   # P1 §3.5: information only unless the point is P1-CALIBRATED
        if 'U4' in E and 'Y' in E:
            a = np.array(S['U4']['per_draw']); b = np.array(S['Y']['per_draw']); diff = a - b; sd = float(diff.std(ddof=1)); dc = S['U4']['Delta_inf'] - S['Y']['Delta_inf']
            xcheck = dict(status='pass' if abs(dc) <= 2 * sd else 'CROSS-CHECK FAILED (|difference| > 2 sigma_D)', difference=dc, sigma_D=sd, paired_draws=int(len(diff)))
            pu, py = S['U4'].get('per_draw_profiled'), S['Y'].get('per_draw_profiled')   # P1 §3.2: both series profiled per draw, same paired draws
            sdp = float((np.array(pu) - np.array(py)).std(ddof=1)) if pu is not None and py is not None else None
            xcheck['sigma_D_profiled'] = sdp
            xprof = dict(status=('unavailable' if sdp is None else 'pass' if abs(dc) <= 2 * sdp else 'CROSS-CHECK FAILED (|difference| > 2 sigma_D)'), difference=dc,
                         sigma_D=sdp, paired_draws=int(len(diff)), sigma_D_fixed=sd, status_fixed=xcheck['status'], sigma_D_profiled=sdp, sigma_rule='profiled')
    P['quoted'] = quoted; P['crosscheck'] = xcheck
    # reblocking (mandatory, FIT2D-003): the SAME quantity at blocks 1000 and 4000 — σ_∞ of the reference series at the primary ω′* (per-draw GLS
    # on the reblock's complete draws, ≥ 90 % required) when an extrapolation is quoted, else σ_U4 of the 64->128 pair — within ±30 % of the primary
    rb = {}; rb_bad = []; rb_unreadable = []
    for o in reblock_dirs:
        try:   # FIT3D-003/009: a missing or malformed reblock record is REBLOCKING UNAVAILABLE for its point, never a crash; the primary stays valid
            r2, d2, byL2, order2 = load_point(o)
            s2 = r2.get('s'); blk = r2.get('block')
            if not isinstance(s2, (int, float)) or blk is None or not hasattr(d2, 'ndim') or d2.ndim != 3 or 'chains' not in r2 or 'rows' not in r2:
                raise ValueError('missing s/block/chains/rows or draws array not 3-dimensional')
            if abs(s2 - res['s']) > 1e-12 or blk not in REBLOCKS: continue
            chk = record_checks(r2, manifest, manifest_sha, f'reblock b={blk}', require_index, total, index_remap) + same_raw(res, r2, f'reblock b={blk}')
        except Exception as e:
            rb_unreadable.append(f'{o}: {type(e).__name__}: {e}'); continue
        rb_bad += chk
        val = None; note = None; val_p = None; prim_p = None; note_p = None
        try:
          if quoted:
              if all(L in byL2 for L in PAIRS):
                  idx2 = [order2.index(L) for L in PAIRS]; ok2 = np.isfinite(d2[:, idx2, :]).all(axis=(1, 2)); Dk2 = d2[ok2]
                  if ok2.sum() >= COMMON_VALID_FRAC * len(d2):
                      ref = quoted['reference_series']
                      if ref == 'J': D2 = np.concatenate([Dk2[:, idx2, OBS['U4']], Dk2[:, idx2, OBS['Y']]], axis=1); X = design(PAIRS, quoted['omega'], 2)
                      else: D2 = Dk2[:, idx2, OBS[ref]]; X = design(PAIRS, quoted['omega'], 1)
                      C2 = np.cov(D2, rowvar=False, ddof=1)
                      try: val = float(np.array([gls(D2[i], C2, X)[0][0] for i in range(len(D2))]).std(ddof=1))
                      except np.linalg.LinAlgError: note = 'singular covariance'
                      try: val_p = float(profile_draws(D2, C2, PAIRS, 2 if ref == 'J' else 1)[0].std(ddof=1))   # P1 §3.4: this record's own covariance, ω′ per draw
                      except Exception as e: note_p = f'profiled sigma unavailable: {type(e).__name__}: {e}'
                  else: note = f'only {int(ok2.sum())} of {len(d2)} complete draws'
              else: note = 'pair missing in the reblock record'
              prim = quoted['sigma_stat']; prim_p = quoted.get('sigma_stat_profiled')
          else:
            t2 = byL2.get(PAIRS[-1]); val = (t2.get('statistical_stderr') or [None] * 5)[2] if t2 else None; prim = sig_top
            if val is None: note = '64->128 pair missing in the reblock record'
            val_p, prim_p = val, prim   # P1 §3.4: without a quoted extrapolation the comparison stays σ_U4 of the largest pair
          for name, x in (('sigma', val), ('primary', prim)):   # FIT3D-016: uncertainties must be finite numbers or absent
              if x is not None and not (isinstance(x, (int, float)) and np.isfinite(x)): raise ValueError(f'non-numeric {name} uncertainty {x!r}')
          ratio = (val / prim) if (val is not None and prim is not None and prim > 0) else None
          fp = lambda x: x is not None and isinstance(x, (int, float)) and bool(np.isfinite(x))   # P1: a non-finite profiled value only makes the profiled ratio absent
          ratio_p = (val_p / prim_p) if (fp(val_p) and fp(prim_p) and prim_p > 0) else None
          pop2 = population_rule(r2, replicas)   # FIT3D-021: the §4.1 equilibration rule (incl. block/τ ≥ 20 at THIS block) applies to every reblock record too
          entry = dict(sigma=val, primary=prim, ratio=ratio, note=note, equilibration_passed=bool(pop2['passed']), equilibration=pop2,
                       sigma_profiled=val_p, primary_profiled=prim_p, ratio_profiled=ratio_p, note_profiled=note_p)
        except Exception as e:   # FIT3D-009/016: any failure inside the reblock computation is attributed to the reblock
            rb_unreadable.append(f'{o}: {type(e).__name__}: {e}'); continue
        rb[blk] = entry
    have = all(b in rb and rb[b]['ratio'] is not None for b in REBLOCKS) and not rb_bad
    P['reblocking'] = dict(available=have, comparisons=rb, record_problems=rb_bad, unreadable_inputs=rb_unreadable,
                           passed=((all(abs(rb[b]['ratio'] - 1) <= REBLOCK_TOL for b in REBLOCKS) and all(rb[b]['equilibration_passed'] for b in REBLOCKS)) if have else None))
    have_p = all(b in rb and rb[b]['ratio_profiled'] is not None for b in REBLOCKS) and not rb_bad   # P1 §3.4, used only for P1-CALIBRATED points
    passed_p = ((all(abs(rb[b]['ratio_profiled'] - 1) <= REBLOCK_TOL for b in REBLOCKS) and all(rb[b]['equilibration_passed'] for b in REBLOCKS)) if have_p else None)
    # FIT3D-021: a reblock record failing the equilibration rule at its own block (block/τ < 20, drift, non-finite) makes the point REBLOCKING FAILED
    if rb_bad: nonprod += rb_bad; P['production'] = False; P['non_production_reasons'] = nonprod   # FIT2D-001: an invalid reblock record taints the point
    # decision table §4.6 in order (fixed rule; amendment P1 re-decides P1-CALIBRATED points in apply_p1 with the same table)
    dec = decision_table(P, E, S, quoted, have, P['reblocking']['passed'], xcheck['status'], 'sigma_inf')
    if dec in ('EQUILIBRATION FAILED', 'COVERAGE-LIMITED', 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE'): P['quoted'] = quoted = None   # FIT2D-004: finite-size pairs only
    P['decision'] = final_label(P, dec)
    P['sigma_rule'] = dict(requested='fixed', applied='fixed', p1_calibrated=False)
    try: T = truths(S, inputs)
    except Exception as e: T = dict(error=f'{type(e).__name__}: {e}')
    P['_p1'] = dict(S=S, E=E, inputs=inputs, truths=T, xcheck_profiled=xprof, reblocking_profiled=dict(available=have_p, passed=passed_p))   # internal, removed before writing
    return P

def decision_table(P, E, S, quoted, have, passed, xstatus, sig_key):
    """§4.6 rows in order, before the precision suffix; sig_key names the σ_∞ of the rule in force (the ACCEPTED ratio label uses it)."""
    if not P['equilibration']['passed']: dec = 'EQUILIBRATION FAILED'
    elif not P['coverage']['passed']: dec = 'COVERAGE-LIMITED'
    elif not E: dec = 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE'
    elif len(E) == 1: dec = 'CONDITIONAL'
    elif not have: dec = 'REBLOCKING UNAVAILABLE'
    elif passed is False: dec = 'REBLOCKING FAILED'
    elif 'U4' not in E or 'Y' not in E: dec = 'CROSS-CHECK UNAVAILABLE'
    elif xstatus != 'pass': dec = 'CROSS-CHECK FAILED'
    else:
        med_stat = float(np.median([S[q][sig_key] for q in E]))
        dec = 'ACCEPTED' if quoted['sigma_sys'] <= RATIO_LABEL * med_stat else 'ACCEPTED (sigma_sys-dominated)'
    return dec

def final_label(P, dec):
    """The precision suffix (§4.6, rule-independent) and the non-production prefix."""
    if not P['precision']['known']: dec += ' [precision unknown: 64->128 missing]'
    elif not P['precision']['met']: dec += ' [sigma_stat above target]'
    return dec if P['production'] else f'NON-PRODUCTION ({"; ".join(P["non_production_reasons"])}); would be: {dec}'

def apply_p1(P, p1):
    """Amendment P1 §3.6 / P1-006, per point and atomically. The point is P1-CALIBRATED when the calibration is bound to these inputs (P1-007),
    A3 holds, and every stratum the point uses passes: A1 of every series in E (the reference series is one of them; σ_sys's ratio label uses
    them all) and A2 of its cross-check when U4 and Y are both in E. A P1-CALIBRATED point is re-evaluated entirely under §3 (σ_stat, σ_D,
    reblocking, label); every other point keeps its complete fixed-rule evaluation and gets the note. A4 is checked on the result."""
    I = P.pop('_p1'); S, E = I['S'], I['E']; rule = P['sigma_rule']; rule['requested'] = 'profiled'; used = []; why = []
    if not p1['valid']: why.append('calibration not bound to these inputs')
    elif not p1['adopted']: why.append('amendment withdrawn (A3 does not hold)')
    elif not E: why.append('no eligible series (no calibrated quantity enters the label)')
    else:
        pt = p1['strata'].get(skey(P['s']))
        if pt is None: why.append(f'no calibration strata for s = {P["s"]}')
        else:
            for q in E:
                st = pt.get(q) or {}; used.append(dict(stratum=f'A1 {q}', status=st.get('status', 'MISSING'), n_eligible=st.get('n_eligible')))
                if st.get('status') != 'PASS': why.append(f"A1 stratum {q}: {st.get('status', 'MISSING')}" + (f" ({st['reason']})" if st.get('reason') else ''))
                if S[q].get('sigma_inf_profiled') is None: why.append(f'profiled sigma of {q} unavailable')
            if 'U4' in E and 'Y' in E:
                st = pt.get('crosscheck') or {}; used.append(dict(stratum='A2 cross-check', status=st.get('status', 'MISSING'), n_both_eligible=st.get('n_both_eligible')))
                if st.get('status') != 'PASS': why.append(f"A2 cross-check: {st.get('status', 'MISSING')}" + (f" ({st['reason']})" if st.get('reason') else ''))
                if I['xcheck_profiled'] is None or I['xcheck_profiled']['sigma_D'] is None: why.append('profiled sigma_D unavailable')
    rule['strata_used'] = used
    if why: rule.update(applied='fixed', p1_calibrated=False, note='P1 not applied: ' + '; '.join(why)); return P
    # the complete §3 evaluation is built in new objects and committed only at the end (no point ever mixes the two rules)
    q0 = P['quoted']; rb = P['reblocking']; rbp = I['reblocking_profiled']
    quoted = None if q0 is None else dict(q0, sigma_stat=S[q0['reference_series']]['sigma_inf_profiled'], sigma_stat_fixed=q0['sigma_stat'], sigma_rule='profiled')
    xcheck = I['xcheck_profiled'] if ('U4' in E and 'Y' in E) else dict(P['crosscheck'], sigma_rule='profiled')
    comps = {b: dict(c, sigma=c['sigma_profiled'], primary=c['primary_profiled'], ratio=c['ratio_profiled'], note=c.get('note_profiled') or c.get('note'),
                     sigma_fixed=c['sigma'], primary_fixed=c['primary'], ratio_fixed=c['ratio'], note_fixed=c.get('note')) for b, c in rb['comparisons'].items()}
    reblocking = dict(rb, comparisons=comps, available=rbp['available'], passed=rbp['passed'], available_fixed=rb['available'], passed_fixed=rb['passed'], sigma_rule='profiled')
    dec = decision_table(P, E, S, quoted, reblocking['available'], reblocking['passed'], xcheck['status'], 'sigma_inf_profiled')
    label = final_label(P, dec)
    ref = (q0 or {}).get('reference_series'); pt = p1['strata'][skey(P['s'])]
    a1 = (pt.get(ref) or {}).get('status') if ref else None; a2 = (pt.get('crosscheck') or {}).get('status') if xcheck is I['xcheck_profiled'] else None
    x_changed = xcheck.get('status') != P['crosscheck'].get('status')
    a4 = dict(label_changed=label != P['decision'], reference_series=ref, reference_A1=a1, crosscheck_changed=x_changed, crosscheck_A2=a2)
    a4['satisfied'] = (not a4['label_changed']) or (a1 == 'PASS' and (not x_changed or a2 == 'PASS'))
    if not a4['satisfied']: rule.update(applied='fixed', p1_calibrated=False, A4=a4, note='P1 not applied: A4 promotion gate not satisfied'); return P
    rule.update(applied='profiled', p1_calibrated=True, fixed_rule_decision=P['decision'], A4=a4)
    if a4['label_changed']:   # §6 R4: the drop-smallest check of U4 and Y is reported with a changed label
        rule['R4_drop_smallest'] = {q: drop_smallest(I['inputs'][q][0], I['inputs'][q][1], S[q]['omega']) for q in ('U4', 'Y') if q in E}
    P['quoted'] = quoted; P['crosscheck'] = xcheck; P['reblocking'] = reblocking; P['decision'] = label
    return P

def strict_json(text):
    """JSON without NaN / Infinity (P1-010)."""
    def bad(c): raise ValueError(f'non-standard JSON constant {c}')
    return json.loads(text, parse_constant=bad)

def finite(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def count(x, hi): return isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= hi

def valid_counts(q, st):
    """A stratum's counts: integers, n_sets ∈ {0, CAL_SETS} (0 = no ensemble could be built), every count within its parent count."""
    if not isinstance(st, dict) or st.get('status') not in ('PASS', 'FAIL', 'UNCALIBRATED'): return False
    n = st.get('n_sets')
    if not (count(n, CAL_SETS) and n in (0, CAL_SETS)): return False
    if q == 'crosscheck':
        b = st.get('n_both_eligible'); return count(b, n) and count(st.get('n_fail_profiled'), b) and count(st.get('n_fail_fixed'), b)
    e = st.get('n_eligible'); return count(e, n) and all(count(st.get(k), e) for k in ('n_cov1_profiled', 'n_cov2_profiled', 'n_cov1_fixed', 'n_cov2_fixed'))

def compare_truths(T, HT):
    """Recorded truths (finite numbers) against a refit: ω′* identical, Δ_ε and amplitudes within TRUTH_TOL."""
    if not isinstance(HT, dict): return ['truth missing']
    bad = []
    for q in SERIES_KEYS:
        a, b = T.get(q), HT.get(q, 'missing')
        if b == 'missing': bad.append(f'truth of {q} missing'); continue
        if a is None or b is None:
            if not (a is None and b is None): bad.append(f'truth of {q}: one side has no fit')
            continue
        if not (isinstance(b, dict) and finite(b.get('Delta')) and finite(b.get('omega')) and isinstance(b.get('c'), list) and len(b['c']) == len(a['c'])
                and all(finite(x) for x in b['c'])): bad.append(f'truth of {q} malformed or non-finite'); continue
        if b['omega'] != a['omega'] or abs(b['Delta'] - a['Delta']) > TRUTH_TOL or any(abs(x - y) > TRUTH_TOL for x, y in zip(b['c'], a['c'])): bad.append(f'truth of {q} differs from the refit')
    return bad

def settings_of(m):
    return dict(pairs=m.PAIRS, obs=m.OBS, omega_grid=[float(m.OMEGA_GRID[0]), float(m.OMEGA_GRID[-1]), 0.01], omega_margin=m.OMEGA_MARGIN, chi2_dof_max=m.CHI2_DOF_MAX,
                resolution_max=m.RESOLUTION_MAX, common_valid_frac=m.COMMON_VALID_FRAC, n_sets=CAL_SETS, n_draws=CAL_DRAWS)

def evaluator_module(dim):
    """This evaluator for DIM; the repository evaluator of the other dimension otherwise (its sha256 is checked before it is loaded)."""
    if dim == DIM: return types.SimpleNamespace(**globals())
    spec = importlib.util.spec_from_file_location(f'evaluate_{dim}d_p1_binding', ROOT / EVALUATOR_PATHS[dim]); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m

def load_calibration(path, amendment, plan_sha):
    """P1-007/008/009: all checks must pass, else the WHOLE calibration is invalid and every point uses the fixed rule. The calibration must
    be complete (both dimensions, every point of both pinned baselines, every stratum), written by calibrate_p1.py and the evaluators of this
    repository (sha256), bound to the pinned records (hashes) and to this code's refit of every truth of both dimensions (every contributor
    to A3). Malformed content never aborts the evaluation: it is a failed check (P1-011)."""
    checks = []
    def chk(name, ok, detail=''): checks.append(dict(check=name, passed=bool(ok), detail=str(detail)[:400])); return bool(ok)
    try:
        cal = strict_json(Path(path).read_text()); H = cal['header']
        if not (isinstance(H, dict) and isinstance(H.get('dims'), dict) and isinstance(cal.get('strata'), dict) and isinstance(cal.get('A3'), dict)):
            raise ValueError('header, header.dims, strata and A3 must be JSON objects')
        am = sha256(amendment)
        chk('amendment file is the approved revision', am == AMENDMENT_SHA256, am)
        chk('header amendment_sha256 = the amendment file', H.get('amendment_sha256') == am, H.get('amendment_sha256'))
        cs = sha256(ROOT / CALIBRATION_SCRIPT)
        chk('header calibration_script_sha256 = calibrate_p1.py of this repository', H.get('calibration_script_sha256') == cs, f"{H.get('calibration_script_sha256')} vs {cs}")
        ev = H.get('evaluators') if isinstance(H.get('evaluators'), dict) else {}
        for d, rel in EVALUATOR_PATHS.items():
            e = sha256(ROOT / rel); r = ev.get(str(d)) if isinstance(ev.get(str(d)), dict) else {}
            chk(f'header evaluator sha256 ({d}D) = {rel} of this repository', r.get('sha256') == e, f"{r.get('sha256')} vs {e}")
        chk('this evaluator is the repository file', sha256(__file__) == sha256(ROOT / EVALUATOR_PATHS[DIM]))
        chk('complete calibration (no --only subset)', 'only' in H and H['only'] is None, H.get('only', 'not recorded'))
        chk('header and strata cover both dimensions', set(H['dims']) == {'2', '3'} and set(cal['strata']) == {'2', '3'}, f"{sorted(H['dims'])} / {sorted(cal['strata'])}")
        adopt = dict(A1_min_eligible=A1_MIN_ELIGIBLE, A1_cov1_min=A1_COV1_MIN, A1_cov2_min=A1_COV2_MIN, A2_min_sets=A2_MIN_SETS, A2_false_fail_max=A2_FALSE_FAIL_MAX, A3_fixed_cov1_max=A3_FIXED_COV1_MAX)
        chk('header adoption thresholds = the amendment\'s', H.get('adoption') == adopt, H.get('adoption'))
        chk('the --plan given is the frozen protocol', plan_sha == FROZEN_PLAN_SHA256[DIM], plan_sha)
        if not all(c['passed'] for c in checks): return cal, checks   # no refits for a calibration already known to be unbound
        for d in (2, 3):
            m = evaluator_module(d); Hd = H['dims'][str(d)]; St = cal['strata'][str(d)]
            if not (isinstance(Hd, dict) and isinstance(Hd.get('points'), dict) and isinstance(St, dict)): raise ValueError(f'{d}D header or strata are not JSON objects')
            chk(f'{d}D protocol_sha256 = the frozen protocol', Hd.get('protocol_sha256') == FROZEN_PLAN_SHA256[d], Hd.get('protocol_sha256'))
            bpath, bsha = BASELINE_EVALUATIONS[d]
            chk(f'{d}D baseline_sha256 = the pinned baseline evaluation', Hd.get('baseline_sha256') == bsha, Hd.get('baseline_sha256'))
            chk(f'{d}D settings = the evaluator constants', Hd.get('settings') == settings_of(m), f"{Hd.get('settings')} vs {settings_of(m)}")
            if not chk(f'{d}D pinned baseline evaluation present', (ROOT / bpath).is_file() and sha256(ROOT / bpath) == bsha, bpath): continue
            want = {m.skey(P['s']): P['inputs'] for P in strict_json((ROOT / bpath).read_text())['points'].values()}
            chk(f'{d}D header points = the baseline points', set(Hd['points']) == set(want), f"{sorted(Hd['points'])} vs {sorted(want)}")
            chk(f'{d}D strata points = the baseline points', set(St) == set(want), f'{sorted(St)} vs {sorted(want)}')
            for s, inp in want.items():
                h = Hd['points'].get(s); st = St.get(s)
                # P1-014: a present but malformed (null / non-object) point header or strata entry is a failed check, never a silent skip
                if not chk(f'{d}D s={s}: header point and strata entry are JSON objects', isinstance(h, dict) and isinstance(st, dict), f'{type(h).__name__} / {type(st).__name__}'): continue
                chk(f'{d}D s={s}: strata {list(STRATA_KEYS)} with valid counts', set(st) == set(STRATA_KEYS) and all(valid_counts(q, x) for q, x in st.items()), sorted(st))
                if not chk(f'{d}D s={s}: record hashes = the baseline inputs', h.get('results_sha256') == inp['results_sha256'] and h.get('draws_sha256') == inp['draws_sha256']): continue
                rec = ROOT / str(h.get('record', ''))
                if not chk(f'{d}D s={s}: record present with the bound hashes', (rec / 'results.json').is_file() and (rec / 'bootstrap.npy').is_file()
                           and sha256(rec / 'results.json') == inp['results_sha256'] and sha256(rec / 'bootstrap.npy') == inp['draws_sha256'], rec): continue
                res, dr, byL, order = m.load_point(rec)
                if any(L not in byL for L in m.PAIRS): T = {q: None for q in SERIES_KEYS}
                else: S, _, inputs = m.fit_series(dr, byL, order); T = m.truths(S, inputs)
                bad = compare_truths(T, h.get('truth')); chk(f'{d}D s={s}: truths = this code\'s refit of the record', not bad, '; '.join(bad))
        bad = [f'{d}/{s}/{q}' for d, pts in cal['strata'].items() for s, pt in pts.items() for q, st in pt.items()
               if not isinstance(st, dict) or st.get('status') != stratum_status('A2' if q == 'crosscheck' else 'A1', st)]
        chk('every stratum status follows from its recorded counts', not bad, ', '.join(bad[:5]))
        a3 = a3_pooled(cal['strata']); chk('A3 recomputed from the strata = the recorded A3', a3 == cal['A3'], f"{a3} vs {cal['A3']}")
        return cal, checks
    except Exception as e:
        chk('calibration content is well formed', False, f'{type(e).__name__}: {e}'); return None, checks

def point_binding(P, cal):
    """P1-007 per evaluated point: the calibration's record hashes are those of the record being evaluated, and its truths equal this run's fit."""
    h = cal['header']['dims'][str(DIM)]['points'].get(skey(P['s']))
    if not isinstance(h, dict): return ['point missing from the calibration header']
    bad = [f'{k} differs' for k, v in (('results_sha256', P['inputs']['results_sha256']), ('draws_sha256', P['inputs']['draws_sha256'])) if h.get(k) != v]
    T = P['_p1']['truths']
    return bad + ([f"own fit failed: {T['error']}"] if 'error' in T else compare_truths(T, h.get('truth')))

def p1_run(report, sigma_rule, calibration, amendment, plan_sha):
    """Amendment P1 in main: header binding (P1-007), per-point binding, then apply_p1 for every point; strips the internal fields."""
    pts = [P for P in report['points'].values() if '_p1' in P]
    if sigma_rule == 'profiled':
        cal, checks = load_calibration(calibration, amendment, plan_sha)   # never raises: malformed content is a failed check (P1-011)
        if cal is not None and all(c['passed'] for c in checks):
            for P in pts:
                try: bad = point_binding(P, cal)
                except Exception as e: bad = [f'{type(e).__name__}: {e}']
                checks.append(dict(check=f's = {P["s"]}: record hashes and fitted truths', passed=not bad, detail='; '.join(bad)))
        valid = cal is not None and all(c['passed'] for c in checks)
        p1 = dict(valid=valid, adopted=bool(valid and cal['A3']['holds']), strata=(cal['strata'].get(str(DIM), {}) if valid else {}))
        report['amendment_P1'] = dict(amendment=str(amendment), amendment_sha256=sha256(amendment), calibration=str(calibration), calibration_sha256=sha256(calibration),
                                      calibration_valid=valid, binding_checks=checks, A3=(cal.get('A3') if valid else None), adopted=p1['adopted'],
                                      rule='labels of P1-CALIBRATED points are decided by the profiled quantities of amendment §3; every other point keeps the '
                                           'complete frozen fixed-rule evaluation and carries the note "P1 not applied: ..." (§3.6)')
        for P in pts:
            try: apply_p1(P, p1)
            except Exception as e:   # never a partial application: apply_p1 commits only at its end
                P.pop('_p1', None); P['sigma_rule'].update(requested='profiled', applied='fixed', p1_calibrated=False, note=f'P1 not applied: internal error {type(e).__name__}: {e}')
        for P in report['points'].values():
            P.setdefault('sigma_rule', dict(requested='profiled', applied='fixed', p1_calibrated=False, note='P1 not applied: no evaluable primary record'))
        report['amendment_P1']['p1_calibrated_points'] = [P['s'] for P in pts if P['sigma_rule']['applied'] == 'profiled']
    for P in pts: P.pop('_p1', None)

def p1_md(report):
    """Markdown for the amendment and the deviations (empty for a plain fixed-rule evaluation)."""
    L = []
    if report.get('deviations'): L += ['', '## Deviations', ''] + [f'- {x}' for x in report['deviations']]
    A = report.get('amendment_P1')
    if not A: return '\n'.join(L) + ('\n' if L else '')
    f = lambda x: '—' if x is None else f'{x:.5f}'
    r = lambda x: '—' if x is None else f'{x:.2f}'
    L += ['', '## Amendment P1: σ rule per point', '',
          f"Amendment sha256 {A['amendment_sha256'][:12]}…; calibration `{A['calibration']}` (sha256 {A['calibration_sha256'][:12]}…): binding "
          f"{'VALID' if A['calibration_valid'] else 'INVALID'}; A3 {'holds' if A['adopted'] else 'does not hold or not evaluated'}"
          f" (pooled fixed-ω′ 1σ coverage {f((A['A3'] or {}).get('fixed_cov1_pooled'))}). {A['rule']}.", '']
    L += [f"- binding check failed: {c['check']} ({c['detail']})" for c in A['binding_checks'] if not c['passed']]
    L += ['', '| s | rule applied | label | fixed-rule label | σ_stat fixed / profiled | σ_D fixed / profiled | reblock ratio fixed / profiled | strata / note |',
          '|---|---|---|---|---|---|---|---|']
    for P in report['points'].values():
        R = P.get('sigma_rule', {}); prof = R.get('applied') == 'profiled'; q = P.get('quoted') or {}; x = P.get('crosscheck') or {}
        cm = (P.get('reblocking') or {}).get('comparisons', {})
        sf, sp = (q.get('sigma_stat_fixed'), q.get('sigma_stat')) if prof else (q.get('sigma_stat'), q.get('sigma_stat_profiled'))
        df, dp = (x.get('sigma_D_fixed'), x.get('sigma_D')) if prof else (x.get('sigma_D'), x.get('sigma_D_profiled'))
        rf = '/'.join(r(cm[b].get('ratio_fixed' if prof else 'ratio')) if b in cm else '—' for b in REBLOCKS)
        rp = '/'.join(r(cm[b].get('ratio' if prof else 'ratio_profiled')) if b in cm else '—' for b in REBLOCKS)
        st = ', '.join(f"{u['stratum']} {u['status']}" for u in R.get('strata_used', []))
        L.append(f"| {P['s']} | {R.get('applied', '—')}{' (P1-CALIBRATED)' if prof else ''} | {P['decision']} | {R.get('fixed_rule_decision', P['decision'])} | {f(sf)} / {f(sp)} | "
                 f"{f(df)} / {f(dp)} | {rf} ; {rp} | {st}{'; ' if st and R.get('note') else ''}{R.get('note', '')} |")
    for P in report['points'].values():
        R4 = (P.get('sigma_rule') or {}).get('R4_drop_smallest')
        if R4: L += ['', f"s = {P['s']} (label changed by P1): drop-smallest check (§6 R4; information) at each series' own ω′*, pairs {next(iter(R4.values()))['pairs']}: "
                     + '; '.join(f"{q} {v['Delta_inf']:.4f}({v['sigma']:.4f}) at ω′ {v['omega']}, χ² {v['chi2']:.2f}/1" for q, v in R4.items())
                     + f" (all four pairs: Δε {P['quoted']['Delta_epsilon']:.5f} from {P['quoted']['reference_series']})"]
    return '\n'.join(L) + '\n'

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--primary', type=Path, nargs='*', default=[], help='primary (b=2000) records; may be empty: every registered point without a record gets a NON-PRODUCTION row (FIT3D-020)')
    p.add_argument('--reblock', type=Path, nargs='*', default=[]); p.add_argument('--snapshot', help='snapshot identity (pack job id) recorded in the evaluation provenance (FIT3D-019)')
    p.add_argument('--plan', type=Path, required=True); p.add_argument('--manifest', type=Path, required=True); p.add_argument('--centers', type=Path, required=True)
    p.add_argument('--extensions', type=Path, help='registered per-point extension totals {"<s>": measurements} (FIT2D-015); absent = 10^6 everywhere')
    p.add_argument('--out', type=Path, required=True); p.add_argument('--no-index-check', action='store_true', help='preview only: skip the histogram-index verification (never for production)')
    p.add_argument('--sigma-rule', choices=('fixed', 'profiled'), default='fixed', help='amendment P1 §3.6: fixed = the frozen rule (default); profiled = §3 for P1-CALIBRATED points')
    p.add_argument('--calibration', type=Path, help='CALIBRATION.json from calibrate_p1.py (required with --sigma-rule profiled)')
    p.add_argument('--amendment', type=Path, help='AMENDMENT_PROFILED_SIGMA.md (required with --sigma-rule profiled; must be the approved revision)')
    p.add_argument('--index-remap', action='append', default=[], metavar='OLD=NEW', help='operational deviation: read an index recorded under path prefix OLD from NEW (hash check unchanged)')
    a = p.parse_args()
    if a.sigma_rule == 'profiled' and not (a.calibration and a.amendment): p.error('--sigma-rule profiled requires --calibration and --amendment (amendment P1 §3.6)')
    if a.sigma_rule == 'fixed' and (a.calibration or a.amendment): p.error('--calibration and --amendment apply only to --sigma-rule profiled')
    remap = []
    for r in a.index_remap:
        old, sep, new = r.partition('=')
        if not sep or not old or not new: p.error(f'--index-remap {r!r}: expected OLD=NEW')
        remap.append((old, new))
    for x in (a.calibration, a.amendment):
        if x is not None and not x.is_file(): p.error(f'{x} is not a file')
    try: a.out.mkdir(parents=True)   # FIT2D-008: atomic claim of a fresh output directory
    except FileExistsError: p.error(f'{a.out} exists: evaluations are immutable, use a new --out (FIT2D-008)')
    plan_sha = sha256(a.plan); manifest = json.loads(a.manifest.read_text()); manifest_sha = sha256(a.manifest); centers = load_centers(a.centers)
    raw_ext = json.loads(a.extensions.read_text()) if a.extensions else {}
    extensions = {}   # FIT3D-001/004: keys must be registered points; totals ≥ the design count and multiples of the largest block (4000)
    for k, v in raw_ext.items():
        try: ks = round(float(k), 10)
        except ValueError: p.error(f'extensions.json: key {k!r} is not a registered point (allowed: the s values of the design)')
        if ks not in DESIGN['s']: p.error(f'extensions.json: unregistered point {k!r}')
        if not isinstance(v, int) or v < DESIGN['measurements'] or v % max(REBLOCKS) != 0: p.error(f'extensions.json: total for s={k} must be an integer ≥ {DESIGN["measurements"]} and a multiple of {max(REBLOCKS)} (got {v!r})')
        extensions[ks] = v
    report = dict(protocol=str(a.plan), plan_sha256=plan_sha, evaluator_sha256=sha256(__file__), manifest=str(a.manifest), manifest_sha256=manifest_sha, campaign_id=manifest['campaign_id'], snapshot=a.snapshot, time=time.strftime('%F_%T'), design=DESIGN, index_check=not a.no_index_check,
                  centers=str(a.centers), centers_sha256=sha256(a.centers), extensions=extensions, extensions_sha256=(sha256(a.extensions) if a.extensions else None),
                  settings=dict(pairs=[f'{L}->{2*L}' for L in PAIRS], omega_grid=[float(OMEGA_GRID[0]), float(OMEGA_GRID[-1]), 0.01], omega_margin=OMEGA_MARGIN, chi2_dof_max=CHI2_DOF_MAX,
                                resolution_max=RESOLUTION_MAX, common_valid_frac=COMMON_VALID_FRAC, ess_min=ESS_MIN, ratio_label=RATIO_LABEL, reblock_tol=REBLOCK_TOL, reblocks=REBLOCKS,
                                primary_block=PRIMARY_BLOCK, production_bootstrap=PRODUCTION_BOOTSTRAP, production_seed=PRODUCTION_SEED, production_min_ess=PRODUCTION_MIN_ESS, target_sigma=TARGET_SIGMA,
                                population=dict(z_hard=POP_Z_HARD, z_soft=POP_Z_SOFT, frac_max=POP_FRAC_MAX, drift_z_max=DRIFT_Z_MAX, block_over_tau_min=BLOCK_OVER_TAU_MIN)), points={})
    report.update(sigma_rule=a.sigma_rule, index_remap=[dict(old=o, new=n) for o, n in remap],
                  deviations=[f'--index-remap {o}={n}: histogram indices read from restored copies (operational deviation; each must still hash to the index_sha256 of its record)' for o, n in remap])
    report['reblock_inputs'] = [dict(path=str(o), readable=(o / 'results.json').is_file() and (o / 'bootstrap.npy').is_file()) for o in a.reblock]
    for d in a.primary:
        try: P = evaluate_point(d, a.reblock, plan_sha, manifest, manifest_sha, centers, extensions, not a.no_index_check, remap)
        except Exception as e:   # FIT3D-003: a malformed primary record is reported, never silently dropped
            P = dict(s=str(d), Delta_sigma=float('nan'), decision=f'NON-PRODUCTION (primary record unreadable: {type(e).__name__}: {e})', quoted=None, eligible=[], largest_pairs=[], reblocking=dict(comparisons={}), crosscheck=dict(status='unavailable'), production=False)
        key = str(P['s'])
        if key in report['points']: p.error(f'duplicate primary record for s={key} ({d}); exactly one record per point')
        report['points'][key] = P
    for s in DESIGN['s']:   # FIT3D-003: every registered point gets a row
        if str(s) not in report['points'] and f'{s:g}' not in report['points']:
            report['points'][str(s)] = dict(s=s, Delta_sigma=(DIM - s) / 2, decision='NON-PRODUCTION (no primary record supplied for this point)', production=False)
    p1_run(report, a.sigma_rule, a.calibration, a.amendment, plan_sha)   # amendment P1: binding checks, then the rule per point (no-op for fixed)
    lines = ['| Δσ | s | decision | Δε | σ_stat | σ_sys | E (ref) | ω′ [Δχ²≤1] | cross-check | reblock 1000/4000 | largest pair U4(σ) / Y |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for P in report['points'].values():
        if 'largest_pairs' not in P:
            lines.append(f"| {P['Delta_sigma']:.4g} | {P['s']} | {P['decision']} | — | — | — | — | — | — | — | — |"); print(lines[-1]); continue
        q = P['quoted'] or {}
        f = lambda x: '—' if x is None else f'{x:.5f}'
        lp = P['largest_pairs'][-1] if P['largest_pairs'] else dict(pair='—', Delta_eff_U4=float('nan'), sigma_U4=float('nan'), Delta_eff_Y=float('nan'))
        rb = P['reblocking']['comparisons']; rbs = '/'.join(f"{rb[b]['ratio']:.2f}" if b in rb and rb[b]['ratio'] else '—' for b in REBLOCKS)
        oi = q.get('omega_interval'); ois = f"{q.get('omega')} [{oi[0]},{oi[1]}]" if oi else '—'
        lines.append(f"| {P['Delta_sigma']:.4g} | {P['s']} | {P['decision']} | {f(q.get('Delta_epsilon'))} | {f(q.get('sigma_stat'))} | {f(q.get('sigma_sys'))} | {','.join(P['eligible']) or '—'} ({q.get('reference_series','—')}) | {ois} | {P['crosscheck']['status']} | {rbs} | {lp['pair']}: {lp['Delta_eff_U4']:.4f}({(lp['sigma_U4'] or float('nan')):.4f}) / {lp['Delta_eff_Y']:.4f} |")
        print(lines[-1])
    (a.out / 'evaluation_3d.json').write_text(json.dumps(report, indent=1, default=float) + '\n')
    title = '# FIT_MODEL_3D evaluation' + (' — amendment P1 (--sigma-rule profiled)' if a.sigma_rule == 'profiled' else '')
    (a.out / 'EVALUATION_3D.md').write_text(title + '\n\n' + '\n'.join(lines) + '\n' + p1_md(report)); print(a.out / 'EVALUATION_3D.md')
if __name__ == '__main__': main()
