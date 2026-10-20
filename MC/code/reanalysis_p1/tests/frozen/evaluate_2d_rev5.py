#!/usr/bin/env python3
"""FIT_MODEL_2D §4 evaluator (revision 5, after Codex rounds 1–3, FIT2D-001..016): from precision_analysis.py outputs to one decision label per point.

Usage: evaluate_2d.py --primary DIR [DIR ...] --reblock DIR [DIR ...] --plan FIT_MODEL_2D.md --manifest CAMPAIGN/manifest.json --centers production_centers.csv
                      [--extensions extensions.json] --out OUT
  DIR = one point (one s) at one block size: results.json + bootstrap.npy. --primary is block 2000; --reblock must supply blocks 1000 and 4000
  for every primary point (REBLOCKING UNAVAILABLE otherwise). Production records need bootstrap 500 with the pre-registered seed.
Pre-registered pair list: (64,128), (128,256), (256,512), (512,1024). A pair absent from a record is a coverage failure, never a shorter fit.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np

PAIRS = [64, 128, 256, 512]                        # smaller size of every pre-registered doubling pair
OBS = {'U4': 2, 'U6': 3, 'U8': 4, 'Y': 1}          # column in the analysis value vector [beta, Y, U4, U6, U8]
OMEGA_GRID = np.round(np.arange(0.2, 2.0 + 1e-9, 0.01), 2); OMEGA_MARGIN = 0.02
CHI2_DOF_MAX = 2.0; COMMON_VALID_FRAC = 0.9; ESS_MIN = 0.5; RATIO_LABEL = 3.0; REBLOCK_TOL = 0.30; RESOLUTION_MAX = 5.0
DRIFT_Z_MAX = 4.0; BLOCK_OVER_TAU_MIN = 20.0; POP_Z_HARD = 4.0; POP_Z_SOFT = 3.0; POP_FRAC_MAX = 0.02
PRODUCTION_BOOTSTRAP = 500; PRODUCTION_SEED = 571239; PRODUCTION_MIN_ESS = 0.2; PRIMARY_BLOCK = 2000; REBLOCKS = (1000, 4000); TARGET_SIGMA = 0.003; DIM = 2
# frozen production design (FIT_MODEL_2D D1–D4): the manifest and every chain must match it (FIT2D-002)
DESIGN = dict(replicas=12, measurements=1000000, warmup=50000, beta_points=5, sizes=[64, 128, 256, 512, 1024], s=[1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7],
              beta_halfwidth=0.0015, window_exponent=0.75, reference_length=64)

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def gls(y, C, X):
    Ci = np.linalg.inv(C); A = X.T @ Ci @ X; beta = np.linalg.solve(A, X.T @ Ci @ y); r = y - X @ beta
    return beta, float(r @ Ci @ r)

def design(L, omega, nser):
    """[Δ_ε, c_1 .. c_nser] for nser concatenated series over the same L (common Δ_ε and ω′, separate amplitudes)."""
    L = np.asarray(L, float); n = len(L); X = np.zeros((n * nser, 1 + nser)); X[:, 0] = 1
    for k in range(nser): X[k * n:(k + 1) * n, 1 + k] = L ** (-omega)
    return X

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
    if dof < 1: out['reason'] = 'no degree of freedom'; return out
    if chi / dof > CHI2_DOF_MAX: out['reason'] = f'chi2/dof {chi/dof:.2f} > {CHI2_DOF_MAX}'; return out
    if wlo <= OMEGA_GRID[0] + OMEGA_MARGIN + 1e-9 or whi >= OMEGA_GRID[-1] - OMEGA_MARGIN - 1e-9: out['reason'] = f"omega' interval [{wlo}, {whi}] reaches the grid boundary (unresolved)"; return out
    X = design(L, w, nser); per_draw = np.array([gls(D[i], C, X)[0][0] for i in range(len(D))]); sig = float(per_draw.std(ddof=1))
    out.update(sigma_inf=sig, per_draw=per_draw.tolist())
    if sig_ref and sig > RESOLUTION_MAX * sig_ref: out['reason'] = f'sigma_inf {sig:.4f} > {RESOLUTION_MAX} x sigma_stat(largest pair) {sig_ref:.4f}'; return out
    out['eligible'] = True; return out

def load_point(d: Path):
    res = json.loads((d / 'results.json').read_text()); draws = np.load(d / 'bootstrap.npy')
    byL = {r['L']: r for r in res['rows']}; order = list(res['joint_pair_order'])
    return res, draws, byL, order

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
    equal centre(s, L) ± 0.0015 (L/64)^-0.75 on 5 points from the frozen centres table."""
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
    return bad

def load_centers(path):
    import csv
    out = {}
    for r in csv.DictReader(open(path)):
        if int(r['d']) != DIM or not r.get('L', '').strip(): continue
        out[(round(float(r['s']), 10), int(r['L']))] = float(r['beta'])
    return out

def record_checks(res, manifest, manifest_sha, role, require_index=True, allowed_total=None):
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
        ip = res.get('index_path')
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

def evaluate_point(d: Path, reblock_dirs: list[Path], plan_sha, manifest, manifest_sha, centers, extensions, require_index=True):
    res, draws, byL, order = load_point(d); replicas = DESIGN['replicas']; total = int(extensions.get(str(res['s']), DESIGN['measurements']))
    P = dict(s=res['s'], Delta_sigma=res['Delta_sigma'], block=res['block'], bootstrap=res['bootstrap'], bootstrap_seed=res['bootstrap_seed'],
             inputs=dict(results=str(d / 'results.json'), results_sha256=sha256(d / 'results.json'), draws_sha256=sha256(d / 'bootstrap.npy'), plan_sha256=plan_sha,
                         manifest_sha256=manifest_sha, campaign_id=res.get('campaign_id'), index_path=res.get('index_path'), index_sha256=res.get('index_sha256'),
                         analysis_code_sha256=res.get('code_sha256')))
    nonprod = []
    if res['block'] != PRIMARY_BLOCK: nonprod.append(f'primary block {res["block"]} != {PRIMARY_BLOCK}')
    nonprod += design_checks(manifest, centers) + record_checks(res, manifest, manifest_sha, 'primary', require_index, total)
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
    top = byL.get(PAIRS[-1]); sig_top = (top.get('statistical_stderr') or [None] * 5)[2] if top else None   # FIT2D-005: criterion 2 is about 512->1024 only
    P['precision'] = dict(target=TARGET_SIGMA, pair=f'{PAIRS[-1]}->{2*PAIRS[-1]}', sigma_U4=sig_top, met=(sig_top is not None and sig_top <= TARGET_SIGMA), known=sig_top is not None)
    S = {}; E = []
    if not missing:
        idx = [order.index(L) for L in PAIRS]; ok = np.isfinite(draws[:, idx, :]).all(axis=(1, 2)); Dk = draws[ok]
        P['complete_draws'] = int(ok.sum()); enough = ok.sum() >= COMMON_VALID_FRAC * len(draws)
        for q, col in OBS.items():
            y = np.array([byL[L]['values'][col] for L in PAIRS]); D = Dk[:, idx, col]; sig_ref = (byL[PAIRS[-1]].get('statistical_stderr') or [None] * 5)[col]
            S[q] = extrapolate(y, D, PAIRS, 1, sig_ref) if enough else dict(eligible=False, reason=f'only {ok.sum()} of {len(draws)} complete draws')
            S[q].update(central=y.tolist())
        # joint series J: common Δ_ε and ω′ for U4 and Y, separate amplitudes (8 values, 4 parameters incl. ω′)
        yJ = np.concatenate([[byL[L]['values'][OBS['U4']] for L in PAIRS], [byL[L]['values'][OBS['Y']] for L in PAIRS]])
        DJ = np.concatenate([Dk[:, idx, OBS['U4']], Dk[:, idx, OBS['Y']]], axis=1)
        S['J'] = extrapolate(yJ, DJ, PAIRS, 2, (byL[PAIRS[-1]].get('statistical_stderr') or [None] * 5)[OBS['U4']]) if enough else dict(eligible=False, reason='insufficient complete draws')
        S['J'].update(central=yJ.tolist())
        seen = {}
        for q in ('U4', 'U6', 'U8', 'Y', 'J'):
            if not S[q]['eligible']: continue
            key = tuple(np.round(S[q]['central'], 12))
            if key in seen: S[q]['duplicate_of'] = seen[key]; continue
            seen[key] = q; E.append(q)
    P['series'] = {q: {k: v for k, v in s.items() if k != 'per_draw'} for q, s in S.items()}; P['eligible'] = E
    quoted = None; xcheck = dict(status='unavailable')
    if E:
        ref = 'J' if 'J' in E else ('U4' if 'U4' in E else E[0])
        vals = {q: S[q]['Delta_inf'] for q in E}; med_q = sorted(E, key=lambda q: vals[q])[len(E) // 2]
        sig_sys = (max(vals.values()) - min(vals.values())) / 2 + S[ref]['Delta_omega'] if len(E) >= 2 else None
        quoted = dict(Delta_epsilon=S[ref]['Delta_inf'], sigma_stat=S[ref]['sigma_inf'], sigma_sys=sig_sys, reference_series=ref, omega=S[ref]['omega'],
                      omega_interval=S[ref]['omega_interval'], Delta_omega=S[ref]['Delta_omega'], values=vals, median_series=med_q,
                      note='Delta_epsilon and sigma_stat from the reference series (J, else U4); sigma_sys = half-range over E + the reference omega-profile half-range')
        if 'U4' in E and 'Y' in E:
            a = np.array(S['U4']['per_draw']); b = np.array(S['Y']['per_draw']); diff = a - b; sd = float(diff.std(ddof=1)); dc = S['U4']['Delta_inf'] - S['Y']['Delta_inf']
            xcheck = dict(status='pass' if abs(dc) <= 2 * sd else 'CROSS-CHECK FAILED (|difference| > 2 sigma_D)', difference=dc, sigma_D=sd, paired_draws=int(len(diff)))
    P['quoted'] = quoted; P['crosscheck'] = xcheck
    # reblocking (mandatory, FIT2D-003): the SAME quantity at blocks 1000 and 4000 — σ_∞ of the reference series at the primary ω′* (per-draw GLS
    # on the reblock's complete draws, ≥ 90 % required) when an extrapolation is quoted, else σ_U4 of the 512->1024 pair — within ±30 % of the primary
    rb = {}; rb_bad = []
    for o in reblock_dirs:
        r2, d2, byL2, order2 = load_point(o)
        if abs(r2['s'] - res['s']) > 1e-12 or r2['block'] not in REBLOCKS: continue
        chk = record_checks(r2, manifest, manifest_sha, f'reblock b={r2["block"]}', require_index, total) + same_raw(res, r2, f'reblock b={r2["block"]}'); rb_bad += chk
        val = None; note = None
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
                else: note = f'only {int(ok2.sum())} of {len(d2)} complete draws'
            else: note = 'pair missing in the reblock record'
            prim = quoted['sigma_stat']
        else:
            t2 = byL2.get(PAIRS[-1]); val = (t2.get('statistical_stderr') or [None] * 5)[2] if t2 else None; prim = sig_top
            if val is None: note = '512->1024 pair missing in the reblock record'
        rb[r2['block']] = dict(sigma=val, primary=prim, ratio=(val / prim if val and prim else None), note=note)
    have = all(b in rb and rb[b]['ratio'] is not None for b in REBLOCKS) and not rb_bad
    P['reblocking'] = dict(available=have, comparisons=rb, record_problems=rb_bad,
                           passed=(all(abs(rb[b]['ratio'] - 1) <= REBLOCK_TOL for b in REBLOCKS) if have else None))
    if rb_bad: nonprod += rb_bad; P['production'] = False; P['non_production_reasons'] = nonprod   # FIT2D-001: an invalid reblock record taints the point
    # decision table §4.6 in order
    if not P['equilibration']['passed']: dec = 'EQUILIBRATION FAILED'
    elif not P['coverage']['passed']: dec = 'COVERAGE-LIMITED'
    elif not E: dec = 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE'
    elif len(E) == 1: dec = 'CONDITIONAL'
    elif not have: dec = 'REBLOCKING UNAVAILABLE'
    elif P['reblocking']['passed'] is False: dec = 'REBLOCKING FAILED'
    elif 'U4' not in E or 'Y' not in E: dec = 'CROSS-CHECK UNAVAILABLE'
    elif xcheck['status'] != 'pass': dec = 'CROSS-CHECK FAILED'
    else:
        med_stat = float(np.median([S[q]['sigma_inf'] for q in E]))
        dec = 'ACCEPTED' if quoted['sigma_sys'] <= RATIO_LABEL * med_stat else 'ACCEPTED (sigma_sys-dominated)'
    if dec in ('EQUILIBRATION FAILED', 'COVERAGE-LIMITED', 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE'): P['quoted'] = quoted = None   # FIT2D-004: finite-size pairs only
    if not P['precision']['known']: dec += ' [precision unknown: 512->1024 missing]'
    elif not P['precision']['met']: dec += ' [sigma_stat above target]'
    P['decision'] = dec if P['production'] else f'NON-PRODUCTION ({"; ".join(nonprod)}); would be: {dec}'
    return P

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--primary', type=Path, nargs='+', required=True); p.add_argument('--reblock', type=Path, nargs='*', default=[])
    p.add_argument('--plan', type=Path, required=True); p.add_argument('--manifest', type=Path, required=True); p.add_argument('--centers', type=Path, required=True)
    p.add_argument('--extensions', type=Path, help='registered per-point extension totals {"<s>": measurements} (FIT2D-015); absent = 10^6 everywhere')
    p.add_argument('--out', type=Path, required=True); p.add_argument('--no-index-check', action='store_true', help='preview only: skip the histogram-index verification (never for production)'); a = p.parse_args()
    try: a.out.mkdir(parents=True)   # FIT2D-008: atomic claim of a fresh output directory
    except FileExistsError: p.error(f'{a.out} exists: evaluations are immutable, use a new --out (FIT2D-008)')
    plan_sha = sha256(a.plan); manifest = json.loads(a.manifest.read_text()); manifest_sha = sha256(a.manifest); centers = load_centers(a.centers)
    extensions = json.loads(a.extensions.read_text()) if a.extensions else {}
    report = dict(protocol=str(a.plan), plan_sha256=plan_sha, evaluator_sha256=sha256(__file__), manifest=str(a.manifest), manifest_sha256=manifest_sha, campaign_id=manifest['campaign_id'], time=time.strftime('%F_%T'), design=DESIGN, index_check=not a.no_index_check,
                  centers=str(a.centers), centers_sha256=sha256(a.centers), extensions=extensions, extensions_sha256=(sha256(a.extensions) if a.extensions else None),
                  settings=dict(pairs=[f'{L}->{2*L}' for L in PAIRS], omega_grid=[float(OMEGA_GRID[0]), float(OMEGA_GRID[-1]), 0.01], omega_margin=OMEGA_MARGIN, chi2_dof_max=CHI2_DOF_MAX,
                                resolution_max=RESOLUTION_MAX, common_valid_frac=COMMON_VALID_FRAC, ess_min=ESS_MIN, ratio_label=RATIO_LABEL, reblock_tol=REBLOCK_TOL, reblocks=REBLOCKS,
                                primary_block=PRIMARY_BLOCK, production_bootstrap=PRODUCTION_BOOTSTRAP, production_seed=PRODUCTION_SEED, production_min_ess=PRODUCTION_MIN_ESS, target_sigma=TARGET_SIGMA,
                                population=dict(z_hard=POP_Z_HARD, z_soft=POP_Z_SOFT, frac_max=POP_FRAC_MAX, drift_z_max=DRIFT_Z_MAX, block_over_tau_min=BLOCK_OVER_TAU_MIN)), points={})
    lines = ['| Δσ | s | decision | Δε | σ_stat | σ_sys | E (ref) | ω′ [Δχ²≤1] | cross-check | reblock 1000/4000 | largest pair U4(σ) / Y |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for d in a.primary:
        P = evaluate_point(d, a.reblock, plan_sha, manifest, manifest_sha, centers, extensions, not a.no_index_check); report['points'][str(P['s'])] = P; q = P['quoted'] or {}
        f = lambda x: '—' if x is None else f'{x:.5f}'
        lp = P['largest_pairs'][-1] if P['largest_pairs'] else dict(pair='—', Delta_eff_U4=float('nan'), sigma_U4=float('nan'), Delta_eff_Y=float('nan'))
        rb = P['reblocking']['comparisons']; rbs = '/'.join(f"{rb[b]['ratio']:.2f}" if b in rb and rb[b]['ratio'] else '—' for b in REBLOCKS)
        oi = q.get('omega_interval'); ois = f"{q.get('omega')} [{oi[0]},{oi[1]}]" if oi else '—'
        lines.append(f"| {P['Delta_sigma']:.4g} | {P['s']} | {P['decision']} | {f(q.get('Delta_epsilon'))} | {f(q.get('sigma_stat'))} | {f(q.get('sigma_sys'))} | {','.join(P['eligible']) or '—'} ({q.get('reference_series','—')}) | {ois} | {P['crosscheck']['status']} | {rbs} | {lp['pair']}: {lp['Delta_eff_U4']:.4f}({(lp['sigma_U4'] or float('nan')):.4f}) / {lp['Delta_eff_Y']:.4f} |")
        print(lines[-1])
    (a.out / 'evaluation_2d.json').write_text(json.dumps(report, indent=1, default=float) + '\n')
    (a.out / 'EVALUATION_2D.md').write_text('# FIT_MODEL_2D evaluation\n\n' + '\n'.join(lines) + '\n'); print(a.out / 'EVALUATION_2D.md')
if __name__ == '__main__': main()
