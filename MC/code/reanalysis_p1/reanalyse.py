#!/usr/bin/env python3
"""Exploratory reanalysis of the finished 2D and 3D LRI productions (NO new Monte Carlo; NOT a production decision).

Inputs: the primary b=2000 analysis records (results.json + bootstrap.npy, 500 paired draws over the four doubling pairs) copied to
LRI_2d_MC/prod/ and LRI_3d_MC/prod/. The production evaluators (evaluate_2d.py / evaluate_3d.py, frozen protocols) quote sigma_stat from
per-draw GLS fits at the CENTRAL fitted omega' and treat the omega' profile separately. This script asks what changes when the nuisance
exponent is treated as a fitted parameter in every bootstrap draw, and how sensitive each extrapolation is to the smallest pair.

Per point and series (U4, U6, U8, Y and the joint series J = {U4, Y} with common Delta and omega'):
  A  reproduction of the evaluator: profiled GLS on the production omega' grid [0.2, 2.0] step 0.01, sigma at fixed omega'* (must match the
     production evaluation to rounding);
  B  nuisance-aware uncertainty: every draw refitted with its own profiled omega' (same covariance, same grid); sigma_prof = std, plus the
     16/84 percentiles and the fraction of draws whose omega' sits on a grid edge; the same on a wide grid [0.02, 4.0] for diagnosis;
  C  paired U4 - Y cross-check with per-draw profiling (sigma_D_prof), next to the fixed-omega' version the evaluator uses;
  D  cutoff sensitivity: at the central omega'*, the two-parameter fit to the three largest pairs (1 dof) vs all four pairs; and the constant
     fit (no correction) to the two and three largest pairs with its chi2/dof.
Usage: reanalyse.py OUTDIR
"""
from __future__ import annotations
import json, sys, hashlib, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
# P1-003: the baseline production evaluations are pinned by path AND SHA-256 (never "the newest evaluation_*"), so later amendment
# evaluations in the same directory can never be mistaken for the baseline
BASELINE = {2: ('LRI_2d_MC/prod/evaluation_20260922_083649/evaluation_2d.json', 'fbfc0ef980a060d526c03fde6f1ec08e38ffec2d0099675ef13ec160542f552d'),
            3: ('LRI_3d_MC/prod/evaluation_54387089_20260923_194523/evaluation_3d.json', 'ae9cf237d9eb9ba484ab44486882a6dafdedb5fae1a575a1ae2f1d38533755e0')}
def baseline(dim):
    path, sha = BASELINE[dim]; f = ROOT / path
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    if got != sha: raise SystemExit(f'baseline evaluation {path} has sha256 {got}, expected {sha}')
    return [f]
SETS = {2: dict(prod=ROOT / 'LRI_2d_MC/prod', glob='analysis_b2000_s*', pairs=[64, 128, 256, 512], evaluation=baseline(2)),
        3: dict(prod=ROOT / 'LRI_3d_MC/prod', glob='analysis_54387089_b2000_s*', pairs=[8, 16, 32, 64], evaluation=baseline(3))}
OBS = {'U4': 2, 'U6': 3, 'U8': 4, 'Y': 1}
GRID = np.round(np.arange(0.2, 2.0 + 1e-9, 0.01), 2)          # production grid
WIDE = np.round(np.arange(0.02, 4.0 + 1e-9, 0.01), 2)         # diagnostic grid

def design(L, w, nser):
    L = np.asarray(L, float); n = len(L); X = np.zeros((n * nser, 1 + nser)); X[:, 0] = 1
    for k in range(nser): X[k * n:(k + 1) * n, 1 + k] = L ** (-w)
    return X

class Fitter:
    """GLS with a fixed covariance C; precomputes the projector for every omega' on a grid so per-draw profiling is a matrix product."""
    def __init__(self, C, L, nser, grid):
        self.Ci = np.linalg.inv(C); self.grid = grid; self.P = []; self.R = []
        for w in grid:
            X = design(L, w, nser); A = X.T @ self.Ci @ X; M = np.linalg.solve(A, X.T @ self.Ci)   # beta = M y
            self.P.append(M[0]); self.R.append(np.eye(len(C)) - X @ M)                             # residual = R y
        self.P = np.array(self.P); self.R = np.array(self.R)
    def profile(self, y):
        """y: (..., n) -> (Delta at each omega', chi2 at each omega')"""
        d = np.einsum('gn,...n->...g', self.P, y)
        r = np.einsum('gmn,...n->...gm', self.R, y)
        chi = np.einsum('...gm,mk,...gk->...g', r, self.Ci, r)
        return d, chi

def series_fit(y, D, L, nser):
    out = {}
    C = np.cov(D, rowvar=False, ddof=1)
    F = Fitter(C, L, nser, GRID)
    d, chi = F.profile(y); k = int(np.argmin(chi)); w = float(GRID[k]); dof = nser * len(L) - (1 + nser) - 1
    inside = chi <= chi[k] + 1.0; inside4 = chi <= chi[k] + 4.0
    out.update(Delta_inf=float(d[k]), omega=w, chi2=float(chi[k]), dof=dof, chi2_dof=float(chi[k] / dof) if dof > 0 else None,
               omega_interval=[float(GRID[inside].min()), float(GRID[inside].max())],
               Delta_omega_1=float((d[inside].max() - d[inside].min()) / 2), Delta_omega_4=float((d[inside4].max() - d[inside4].min()) / 2))
    # A: fixed-omega' sigma (evaluator)
    dd, cc = F.profile(D); fixed = dd[:, k]; out['sigma_fixed'] = float(fixed.std(ddof=1))
    # B: per-draw profiled
    kk = np.argmin(cc, axis=1); prof = dd[np.arange(len(D)), kk]; wd = GRID[kk]
    out.update(sigma_prof=float(prof.std(ddof=1)), prof_p16_p84=[float(np.percentile(prof, 16)), float(np.percentile(prof, 84))],
               omega_draw_median=float(np.median(wd)), frac_draw_omega_on_edge=float(np.mean((kk == 0) | (kk == len(GRID) - 1))))
    Fw = Fitter(C, L, nser, WIDE); dw, cw = Fw.profile(y); kw = int(np.argmin(cw)); ddw, ccw = Fw.profile(D); kkw = np.argmin(ccw, axis=1); profw = ddw[np.arange(len(D)), kkw]
    out.update(wide=dict(omega=float(WIDE[kw]), Delta_inf=float(dw[kw]), chi2=float(cw[kw]), sigma_prof=float(profw.std(ddof=1)),
                         prof_p16_p84=[float(np.percentile(profw, 16)), float(np.percentile(profw, 84))], frac_edge=float(np.mean((kkw == 0) | (kkw == len(WIDE) - 1)))))
    return out, fixed, prof

def cutoff(y, D, L, w):
    """D: two-parameter fit (Delta, c) at fixed omega' to the three largest pairs; constant fits to the 2 and 3 largest pairs."""
    y3, D3, L3 = y[1:], D[:, 1:], L[1:]; C3 = np.cov(D3, rowvar=False, ddof=1); Ci = np.linalg.inv(C3)
    X = design(L3, w, 1); M = np.linalg.solve(X.T @ Ci @ X, X.T @ Ci); b = M @ y3; r = y3 - X @ b
    per = D3 @ M[0]
    out = dict(drop_smallest=dict(Delta_inf=float(b[0]), sigma=float(per.std(ddof=1)), chi2=float(r @ Ci @ r), dof=1))
    for m in (2, 3):
        ym, Dm = y[-m:], D[:, -m:]; Cm = np.cov(Dm, rowvar=False, ddof=1); Cim = np.linalg.inv(Cm); one = np.ones(m)
        c = float(one @ Cim @ ym / (one @ Cim @ one)); rr = ym - c; chi = float(rr @ Cim @ rr)
        per = Dm @ (Cim @ one / (one @ Cim @ one))
        out[f'constant_last{m}'] = dict(Delta=c, sigma=float(per.std(ddof=1)), chi2=chi, dof=m - 1, chi2_dof=chi / (m - 1))
    return out

def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=False)
    report = dict(note='EXPLORATORY reanalysis of existing records; not a production decision under FIT_MODEL_2D/3D', time=time.strftime('%F_%T'),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), grid=[0.2, 2.0, 0.01], wide_grid=[0.02, 4.0, 0.01], points={})
    for dim, S in SETS.items():
        ev = json.loads(S['evaluation'][-1].read_text())['points'] if S['evaluation'] else {}
        for d in sorted(S['prod'].glob(S['glob']), key=lambda p: float(p.name.split('_s')[-1])):
            res = json.loads((d / 'results.json').read_text()); draws = np.load(d / 'bootstrap.npy')
            s = res['s']; L = np.array(S['pairs'], float); byL = {r['L']: r for r in res['rows']}; order = list(res['joint_pair_order'])
            idx = [order.index(l) for l in S['pairs']]; ok = np.isfinite(draws[:, idx, :]).all(axis=(1, 2)); Dk = draws[ok]
            P = dict(dim=dim, s=s, Delta_sigma=(dim - s) / 2, complete_draws=int(ok.sum()), record=str(d.relative_to(ROOT)),
                     record_sha256=hashlib.sha256((d / 'results.json').read_bytes()).hexdigest(), production_decision=ev.get(str(s), {}).get('decision'), series={})
            per = {}
            for q, col in OBS.items():
                y = np.array([byL[l]['values'][col] for l in S['pairs']]); D = Dk[:, idx, col]
                fit, fixed, prof = series_fit(y, D, L, 1); fit['central'] = y.tolist(); fit['cutoff'] = cutoff(y, D, L, fit['omega'])
                evs = ev.get(str(s), {}).get('series', {}).get(q, {})
                fit['evaluator'] = dict(Delta_inf=evs.get('Delta_inf'), sigma_inf=evs.get('sigma_inf'), omega=evs.get('omega'), eligible=evs.get('eligible'), reason=evs.get('reason'))
                P['series'][q] = fit; per[q] = (fixed, prof)
            yJ = np.concatenate([[byL[l]['values'][OBS['U4']] for l in S['pairs']], [byL[l]['values'][OBS['Y']] for l in S['pairs']]])
            DJ = np.concatenate([Dk[:, idx, OBS['U4']], Dk[:, idx, OBS['Y']]], axis=1)
            fJ, _, _ = series_fit(yJ, DJ, L, 2); evJ = ev.get(str(s), {}).get('series', {}).get('J', {})
            fJ['evaluator'] = dict(Delta_inf=evJ.get('Delta_inf'), sigma_inf=evJ.get('sigma_inf'), omega=evJ.get('omega'), eligible=evJ.get('eligible'), reason=evJ.get('reason'))
            P['series']['J'] = fJ
            dc = P['series']['U4']['Delta_inf'] - P['series']['Y']['Delta_inf']
            sd_fixed = float((per['U4'][0] - per['Y'][0]).std(ddof=1)); sd_prof = float((per['U4'][1] - per['Y'][1]).std(ddof=1))
            P['crosscheck'] = dict(difference=dc, sigma_D_fixed=sd_fixed, z_fixed=dc / sd_fixed, sigma_D_prof=sd_prof, z_prof=dc / sd_prof,
                                   pass_fixed=abs(dc) <= 2 * sd_fixed, pass_prof=abs(dc) <= 2 * sd_prof)
            report['points'][f'{dim}D_s{s}'] = P
            print(f"{dim}D s={s}: U4 {P['series']['U4']['Delta_inf']:.4f} sf {P['series']['U4']['sigma_fixed']:.4f} sp {P['series']['U4']['sigma_prof']:.4f} | "
                  f"Y {P['series']['Y']['Delta_inf']:.4f} sf {P['series']['Y']['sigma_fixed']:.4f} sp {P['series']['Y']['sigma_prof']:.4f} | "
                  f"U4-Y {dc:+.4f} z_fixed {dc/sd_fixed:+.2f} z_prof {dc/sd_prof:+.2f}", flush=True)
    (out_dir / 'reanalysis.json').write_text(json.dumps(report, indent=1, default=float) + '\n')
    write_md(report, out_dir / 'REANALYSIS.md'); print(out_dir / 'REANALYSIS.md')

def write_md(R, path):
    f = lambda x, n=4: '—' if x is None else f'{x:.{n}f}'
    L = ['# Exploratory reanalysis of the 2D and 3D productions (existing data only)', '',
         f"{R['note']}. Script sha256 {R['script_sha256'][:12]}…, {R['time']}. Production omega' grid [0.2, 2.0]; wide diagnostic grid [0.02, 4.0].", '',
         '## Per series: fixed-omega\' vs per-draw-profiled uncertainty', '',
         "| point | series | production eligible (reason) | Δ∞ | ω′* [Δχ²≤1] | χ²/dof | σ fixed ω′ | σ profiled | profiled 16–84 % | draws on ω′ edge | ω′ profile half-range (Δχ²≤1 / ≤4) | wide grid: ω′, Δ∞ |",
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for k, P in R['points'].items():
        for q in ('U4', 'U6', 'U8', 'Y', 'J'):
            S = P['series'][q]; e = S['evaluator']; el = 'yes' if e.get('eligible') else f"no ({(e.get('reason') or '')[:48]})"
            L.append(f"| {k} (Δσ {P['Delta_sigma']:.4g}) | {q} | {el} | {f(S['Delta_inf'])} | {S['omega']} [{S['omega_interval'][0]}, {S['omega_interval'][1]}] | {f(S['chi2_dof'],2)} | "
                     f"{f(S['sigma_fixed'])} | {f(S['sigma_prof'])} | [{f(S['prof_p16_p84'][0])}, {f(S['prof_p16_p84'][1])}] | {S['frac_draw_omega_on_edge']:.2f} | "
                     f"{f(S['Delta_omega_1'])} / {f(S['Delta_omega_4'])} | {S['wide']['omega']}, {f(S['wide']['Delta_inf'])} |")
    L += ['', '## Paired U4 − Y cross-check', '', '| point | production decision | U4 − Y | σ_D fixed ω′ (z) | σ_D profiled (z) | pass fixed / profiled |', '|---|---|---|---|---|---|']
    for k, P in R['points'].items():
        c = P['crosscheck']
        L.append(f"| {k} | {P['production_decision']} | {c['difference']:+.4f} | {c['sigma_D_fixed']:.4f} ({c['z_fixed']:+.2f}) | {c['sigma_D_prof']:.4f} ({c['z_prof']:+.2f}) | "
                 f"{'yes' if c['pass_fixed'] else 'no'} / {'yes' if c['pass_prof'] else 'no'} |")
    L += ['', '## Cutoff sensitivity (U4 and Y)', '',
          '| point | series | Δ∞ all 4 pairs | Δ∞ 3 largest pairs at ω′* (χ², 1 dof) | constant fit, 3 largest (χ²/dof) | constant fit, 2 largest (χ²/dof) |', '|---|---|---|---|---|---|']
    for k, P in R['points'].items():
        for q in ('U4', 'Y'):
            S = P['series'][q]; c = S['cutoff']
            L.append(f"| {k} | {q} | {f(S['Delta_inf'])}({f(S['sigma_fixed'])}) | {f(c['drop_smallest']['Delta_inf'])}({f(c['drop_smallest']['sigma'])}) ({c['drop_smallest']['chi2']:.2f}) | "
                     f"{f(c['constant_last3']['Delta'])}({f(c['constant_last3']['sigma'])}) ({c['constant_last3']['chi2_dof']:.1f}) | {f(c['constant_last2']['Delta'])}({f(c['constant_last2']['sigma'])}) ({c['constant_last2']['chi2_dof']:.1f}) |")
    path.write_text('\n'.join(L) + '\n')

if __name__ == '__main__': main()
