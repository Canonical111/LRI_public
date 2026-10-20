# Calibration of the pilot's tail diagnostics (RECON section 6.3.6; repair round 3, findings 2/8 and 3/7). Seeded, light
# (about 1 min on a laptop). Two parts:
#  [A] per-graph tail statistics of the top-slot values t at R = 8 replicates per campaign, 4096 points per replicate
#      (screening, every L8 graph) and 32,768 nested points (confirmation, P1c and re-runs). Statistics:
#        hill  = mean over the 8 replicates of the Hill estimate of xi = 1/a from the K = 16 largest |t| of the replicate
#                (15 log-spacings above the 16th), i.e. the tail index a of P(|t| > x) ~ x^-a; a <= 2 is infinite variance;
#        smax  = max over replicates of max|t| / sum|t|  (the round-2 "largest single-weight share");
#        fall  = geometric-mean share at 4096 / at 32,768 (log-mean over the 8 replicates, instead of the max);
#        vrat  = per-point variance ratio V(32,768)/V(4096) of the replicate means (one campaign, 7 dof each).
#      Point models: iid draws, and scrambled Sobol points (scipy LMS + digital shift) for some families, since the
#      pilot's points are a randomized QMC net. They are models of the tail only, not of the d=3 integrand.
#  [B] stratum-level shape of the replicate means (replaces the self-standardized pooled excess kurtosis, which is
#      bounded by 3.14 at R = 8 and nearly insensitive). Split-half statistic Q = ln(s2[rep 1-4] / s2[rep 5-8]) per
#      graph and campaign; Var(Q) over a stratum's graphs is scale-free and not self-normalized. Under the Gamma model
#      of realism.py, s2/sigma2 ~ Gamma with Var = 2/(R-1) + kex/R, so Var(Q) = 2 psi'(a4) with 1/a4 = 2/3 + kex/4;
#      but the Gamma model maps kurtosis to the design penalty badly (it overstates P8 at a given kex: kex is set by
#      the extreme tail, P8 = E[e]E[1/e] ~ exp(Var ln e) by the bulk of e = s/sigma). So P8 is estimated from Var(Q)
#      directly: ln P8_hat = ln P8_gauss + C1 (Var(Q) - Var_gauss(Q)), with C1 fitted on the Student-t family and
#      tested out of family (Laplace, lognormal, contaminated normal). The Gamma-model value is printed beside it.
#      The true P8 of each family is computed by direct simulation and compared. A real-data check applies the same
#      estimator to run1's L6/L7 graphs (8 disjoint 8-replicate subsets of the 64), where realism.py measured the
#      R = 8 design penalty with held-out replicates (cd3:realism:2-10).
import numpy as np, json, math, os, sys
from scipy.special import polygamma, gammaln
from scipy.optimize import brentq
from scipy.stats import qmc, norm, f as fdist
RNG = np.random.default_rng(20261003)
R, N1, N2, K = 8, 4096, 32768, 16
out = {}
# ------------------------------------------------------------------ [A]
def stats(X):
    """X: (graphs, R, N2) |t| values; returns per-graph hill1, hill2, smax1, smax2, fall, vrat"""
    G = X.shape[0]; res = {}
    for nm, n in (('1', N1), ('2', N2)):
        Y = X[:, :, :n]
        top = -np.sort(-np.partition(Y, n - K, axis=2)[:, :, n - K:], axis=2)       # K largest, descending
        H = np.log(top[:, :, :K - 1] / top[:, :, K - 1:K]).mean(2)                  # Hill per replicate
        res['hill' + nm] = H.mean(1)
        sh = top[:, :, 0] / Y.sum(2)
        res['smax' + nm] = sh.max(1); res['lsh' + nm] = np.log(sh).mean(1)
        res['V' + nm] = n * Y.mean(2).var(1, ddof=1)
    res['fall'] = np.exp(res['lsh1'] - res['lsh2']); res['vrat'] = res['V2'] / res['V1']
    return res
def tval(name, U):
    """point values |t| of a model family from uniforms U (..., d)"""
    kind, _, a = name.partition('_'); a = float(a) if a else None
    u1, u2, u3 = U[..., 0], U[..., 1], U[..., 2]
    if kind == 'gauss': return np.abs(norm.ppf(u1))
    if kind == 'exp': return -np.log(u1)
    if kind == 'lognorm1': return np.exp(norm.ppf(u1))
    if kind == 'pareto': return u1 ** (-1 / a)                                       # P(t > x) = x^-a
    if kind == 'corner': return (u1 * u2) ** (-1 / a)                                # x^-a log x: two coordinates small
    if kind == 'sparse': return np.abs(norm.ppf(u1)) + 5 * (u2 < 0.002) * u3 ** (-1 / a)   # rare tail: about 8 of 4096
    raise ValueError(name)
def simulate(name, G, sobol):
    parts = []
    for c0 in range(0, G, 25):
        g = min(25, G - c0)
        if sobol:
            U = np.stack([qmc.Sobol(3, scramble=True, seed=RNG).random_base2(15) for _ in range(g * R)]).reshape(g, R, N2, 3)
        else:
            U = RNG.random((g, R, N2, 3))
        U = np.clip(U, 1e-300, 1.0)
        parts.append(stats(tval(name, U)))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
IID = ['gauss', 'exp', 'lognorm1', 'pareto_4', 'pareto_3', 'pareto_2.5', 'pareto_2', 'pareto_1.75', 'pareto_1.5',
       'corner_3', 'corner_2', 'sparse_2']
SOB = ['gauss', 'pareto_3', 'pareto_2', 'corner_2']
# pre-registered thresholds (fixed in repair round 3 from this calibration; the script prints their operating characteristic)
XI_SCREEN, XI_CONFIRM, SMAX_SCREEN, FALL_CONFIRM = 0.38, 0.42, 0.05, 3.4
V99 = fdist.ppf(0.99, 7, 7)                              # one campaign: 7 and 7 dof; normalised by 8^-(2 alpha - 1) in the pilot
print('[A] per-graph tail statistics, R = 8 replicates of one campaign; 4096 points (screen) and 32,768 nested (confirm)')
print('    hill = mean Hill xi-hat (xi = 1/a) from the 16 largest |t| per replicate; fall = geometric-mean share 4096 / 32,768;')
print('    smax = max-over-replicates largest share at 4096; vrat = V(32,768)/V(4096). Medians [10%, 90%] over simulated graphs;')
print(f'    rates: S = screen flag (hill_4096 > {XI_SCREEN} or smax_4096 > {SMAX_SCREEN}); C = confirmed "possible infinite variance"')
print(f'    (hill_32768 > {XI_CONFIRM}, among all graphs, i.e. screen AND confirm); old = round-2 rule (smax > 0.05, fall_max < 2, vrat > 3.70)')
print('    expected fall for a Pareto tail: 8^(1 - 1/a) = ' + ', '.join(f'a={a}: {8**(1-1/a):.2f}' for a in (1.5, 1.75, 2, 2.5, 3, 4)) + '; light tails about 7-8')
rows = []
for sobol, fams, G in ((False, IID, 300), (True, SOB, 200)):
    for nm in fams:
        s = simulate(nm, G, sobol)
        q = lambda v: f'{np.median(v):6.3f} [{np.quantile(v, .1):.3f}, {np.quantile(v, .9):.3f}]'
        S = (s['hill1'] > XI_SCREEN) | (s['smax1'] > SMAX_SCREEN); C = S & (s['hill2'] > XI_CONFIRM)
        Cf = S & ((s['hill2'] > XI_CONFIRM) | (s['fall'] < FALL_CONFIRM))
        smax2 = s['smax2']; fallmax = s['smax1'] / smax2
        old = (s['smax1'] > 0.05) | (fallmax < 2) | (s['vrat'] > 3.70)
        tag = ('sobol ' if sobol else 'iid   ') + nm
        r = dict(name=tag, hill1=float(np.median(s['hill1'])), hill2=float(np.median(s['hill2'])), fall=float(np.median(s['fall'])),
                 screen=float(S.mean()), confirm=float(C.mean()), confirm_or_fall=float(Cf.mean()), old=float(old.mean()),
                 fall_lt=float((s['fall'] < FALL_CONFIRM).mean()), vrat_gt=float((s['vrat'] > V99).mean()), smax_gt=float((s['smax1'] > SMAX_SCREEN).mean()))
        rows.append(r)
        print(f'  {tag:20s} hill4096 {q(s["hill1"])}  hill32768 {q(s["hill2"])}  fall {q(s["fall"])}  smax {np.median(s["smax1"]):.4f}  '
              f'S {100*r["screen"]:5.1f}%  C {100*r["confirm"]:5.1f}%  (C or fall<{FALL_CONFIRM}: {100*r["confirm_or_fall"]:5.1f}%; fall<{FALL_CONFIRM} alone {100*r["fall_lt"]:5.1f}%; '
              f'vrat>{V99:.2f} {100*r["vrat_gt"]:4.1f}%)  old {100*r["old"]:5.1f}%')
out['A'] = rows
# ------------------------------------------------------------------ [B]
def penalty_gamma(Rp, kex):
    v = 2 / (Rp - 1) + kex / Rp; a = 1 / v
    if a <= 0.5: return float('inf')
    return math.exp(gammaln(a + .5) + gammaln(a - .5) - 2 * gammaln(a))
def vq_of_kex(kex): return 2 * float(polygamma(1, 1 / (2 / 3 + kex / 4)))
VQ0 = vq_of_kex(0.0)
def kex_of_vq(vq):
    if vq <= VQ0: return 0.0
    f = lambda k: vq_of_kex(k) - vq
    return brentq(f, 0.0, 200.0) if f(200.0) > 0 else 200.0
def p8_gamma_of_vq(vq): return penalty_gamma(8, kex_of_vq(vq))
P8G = penalty_gamma(8, 0.0)                     # Gaussian R = 8 design penalty, 1.086
C1 = None                                       # fitted below on the t family
def p8_of_vq(vq): return math.exp(math.log(P8G) + C1 * (vq - VQ0))
def draw(name, size):
    if name == 'gauss': x = RNG.standard_normal(size)
    elif name.startswith('t'): nu = float(name[1:]); x = RNG.standard_t(nu, size) / math.sqrt(nu / (nu - 2))
    elif name == 'laplace': x = RNG.laplace(0, 1 / math.sqrt(2), size)
    elif name == 'lognorm0.5': s = 0.5; x = (RNG.lognormal(0, s, size) - math.exp(s * s / 2)) / math.sqrt((math.exp(s * s) - 1) * math.exp(s * s))
    elif name == 'cn': x = RNG.standard_normal(size) * np.where(RNG.random(size) < 0.05, 3.0, 1.0) / math.sqrt(1.4)   # 5% at 3 sigma
    else: raise ValueError(name)
    return x
TRUEKEX = {'gauss': 0, 't16': 0.5, 't10': 1.0, 't7': 2.0, 't6': 3.0, 't5': 6.0, 'laplace': 3.0, 'lognorm0.5': 5.90, 'cn': 4.65}
FIT = ('t16', 't10', 't7', 't6', 't5')
P16_SWITCH, STRATUM_FLAG = 1.13, 1.196        # P8_hat thresholds: R = 16 switch; above the cost table's high-band assumption (x1.196)
print('\n[B] stratum shape of the replicate means at R = 8 (per graph-campaign). Columns: true kex; true R = 8 design penalty P8 =')
print('    E[e]E[1/e], e = s8/sigma (direct simulation, 4e5 graphs); Var(Q) of the split-half statistic Q = ln(s2[1-4]/s2[5-8]);')
print(f'    P8_hat from Var(Q) (Gaussian Var(Q) = 2 psi\'(3/2) = {VQ0:.4f}); old self-standardized pooled excess kurtosis g2')
print('    (median over 300 strata of 500 graphs); then P8_hat over 300 simulated strata of G graph-campaigns: median [5%, 95%], and the')
print(f'    rates of P8_hat > {P16_SWITCH} (the R = 16 switch) and > {STRATUM_FLAG} (beyond the high band\'s x1.196, realism.py kex 2)')
rowsB = []; truth = {}
for nm, kx in TRUEKEX.items():
    Y = draw(nm, (400000, R)); s8 = Y.std(1, ddof=1); P8 = float(s8.mean() * (1 / s8).mean())
    Qa = np.log(Y[:, :4].var(1, ddof=1) / Y[:, 4:].var(1, ddof=1)); truth[nm] = (P8, float(Qa.var()))
x = np.array([truth[n][1] - VQ0 for n in FIT]); y = np.array([math.log(truth[n][0] / P8G) for n in FIT])
C1 = float((x * y).sum() / (x * x).sum())
print(f'    fitted on the t family {FIT}: ln P8 = ln {P8G:.4f} + {C1:.4f} (Var(Q) - {VQ0:.4f})')
for nm, kx in TRUEKEX.items():
    P8, VQ = truth[nm]
    Y5 = draw(nm, (300, 500, R)); Z = (Y5 - Y5.mean(2, keepdims=True)) / Y5.std(2, keepdims=True)    # g2 (ddof 0), as the verifiers
    oldk = float(np.median((Z ** 4).mean((1, 2)) - 3))
    line = (f'  {nm:11s} kex {kx:4.2f}: P8 true {P8:.3f} (Gamma model at true kex {penalty_gamma(8, kx):.3f}); Var(Q) {VQ:.3f} -> P8_hat {p8_of_vq(VQ):.3f} '
            f'({100*(p8_of_vq(VQ)/P8-1):+.1f}%{"" if nm in FIT else ", out of family"}; Gamma-model inversion {p8_gamma_of_vq(VQ):.3f}); old pooled kurtosis {oldk:+.2f}')
    rb = dict(name=nm, kex=kx, P8=P8, VQ=VQ, P8_hat=p8_of_vq(VQ), P8_gamma_inv=p8_gamma_of_vq(VQ), old=oldk)
    for G in (100, 500, 2500):
        Yg = draw(nm, (300, G, R)); Q = np.log(Yg[:, :, :4].var(2, ddof=1) / Yg[:, :, 4:].var(2, ddof=1))
        ph = np.array([p8_of_vq(v) for v in Q.var(1, ddof=1)])
        rb[f'G{G}'] = dict(med=float(np.median(ph)), lo=float(np.quantile(ph, .05)), hi=float(np.quantile(ph, .95)),
                           sw=float((ph > P16_SWITCH).mean()), fl=float((ph > STRATUM_FLAG).mean()))
        line += f'\n      G {G:5d}: P8_hat {np.median(ph):.3f} [{np.quantile(ph, .05):.3f}, {np.quantile(ph, .95):.3f}]  > {P16_SWITCH}: {100*rb[f"G{G}"]["sw"]:5.1f}%  > {STRATUM_FLAG}: {100*rb[f"G{G}"]["fl"]:5.1f}%'
    rowsB.append(rb); print(line)
out['B'] = rowsB
# real-data check on run1 (needs the work directory of run_all.sh)
if os.path.exists('run1-20260930-m4096/C7_result.json'):
    sys.path.insert(0, '.'); from common import graph_reps, graph_cost, SECT, CAMP
    po = json.load(open('partial_out.json')); J8 = {int(L): np.array(v) for L, v in po['J8'].items()}
    RO = json.load(open('realism_out.json'))
    print('\n[B2] real data, run1 L6/L7 (C8 old-slot combination, as realism.py): Var(Q) pooled over graphs and the 8 disjoint 8-replicate')
    print('     subsets of the 64; P8_hat from it, against realism.py\'s held-out measurement of the R = 8 design penalty (cd3:realism:2-9);')
    print('     and the 64-replicate pooled excess kurtosis (self-standardized at R = 64, bias about -6/65)')
    real = {}
    for L in (6, 7):
        k = 8 - L; idx = list(range(k)) + list(range(k + 1, 2 * k + 1)); j8 = J8[L][idx]
        for s in SECT:
            for t in CAMP:
                Gr = graph_reps(t, s, L); C = graph_cost(t, s, L)
                Y = np.array([Gr[g] @ j8 for g in Gr if C[g][0] > 0]); Y = Y[Y.std(1) > 0]
                Q = []
                for j in range(8):
                    B = Y[:, 8 * j:8 * j + 8]; Q.append(np.log(B[:, :4].var(1, ddof=1) / B[:, 4:].var(1, ddof=1)))
                Q = np.concatenate(Q); vq = float(Q.var(ddof=1)); ph = p8_of_vq(vq)
                Z = (Y - Y.mean(1, keepdims=True)) / Y.std(1, ddof=1, keepdims=True); k64 = float((Z ** 4).mean() - 3)
                held = RO[f'noise|R8|{t}_{s}_L{L}']
                real[f'{t}_{s}_L{L}'] = dict(VQ=vq, P8_hat=ph, held_out=held, kex64=k64)
                print(f'     {t}_{s}_L{L}: {len(Y)} graphs x 8 subsets; Var(Q) {vq:.3f} (Gaussian {VQ0:.3f}) -> P8_hat {ph:.3f}; held-out measurement {held:.3f}; kex(R=64) {k64:+.2f}')
    out['B2'] = real
json.dump(out, open('tail_calib_out.json', 'w'), indent=1)
# ======================================================================================================================
# Repair round 4 (appended; every line above and its output are unchanged, and the parts below use their own RNG, so the
# round-3 log lines 1-77 stand). Four verifier items: (1) run1 already holds real tail data (the native max_abs field);
# (2) masked and location-offset tails pass the 4096-point screen; (3) the operating characteristic must be quoted at the
# family-wise scale (40,800 L8 graph-campaigns, one hold per sector); (4) the grid skips a = 8/3 and 3.5 (the a = r/(r-m)
# face model at unscaled rate 1/2, margin 1/4, campaign rates 0.8 / 0.7).
#  [A2] direct simulation (iid points, 200 graphs x 2 campaigns per family): the round-4 rule. Screen per campaign as in
#       round 3; a graph flagged in either campaign is re-run at 32,768 nested points in BOTH campaigns and confirmed if
#       the two-campaign mean xi_hat(32,768) > 0.44 (P1c graphs: the same test without the screen). Also the Hill index
#       on excesses over the replicate mean (location-insensitive; supporting evidence only, see the printed rates).
#  [A3] exact top-order statistics (no bulk simulation), 2e5 graphs (4e5 graph-campaigns) per family: family-wise
#       rates of the round-3 rule (per graph-campaign) and of the round-4 rule (per graph), as expected counts over the
#       20,400 L8 graphs (40,800 graph-campaigns) and the 4,336 power graphs if every graph had that tail; and the
#       production-time monitor (R = 64, n_g = 2^18 and 2^22 points per replicate).
#  [A4] masked tails: the tail component's share of the per-point variance at production counts (analytic, truncated
#       at the sample maximum).
#  [B3] run1 block maxima (real data, every L3-L7 group): the native max_abs field of each row is the largest |t| over
#       the row's points, t = norm (3 w_B - w_A) v_0 (c7d3_integrate.cpp:58); per graph-replicate the maximum over its rows
#       is the maximum over n_g points. xi_sd = sd(ln max) sqrt(6)/pi over the 64 replicates is exactly 1/a for a Frechet
#       (Pareto-tail) maximum and overstates xi for mixtures; GEV maximum likelihood on the extreme graphs; a/b agreement
#       and the cross-campaign shift that the face model a = r/(r - m) predicts; variance and cost shares.
from scipy.special import lambertw
from scipy.stats import genextreme, skew as _skew, kurtosis as _kurt
RNG4 = np.random.default_rng(20261004)
XI2_MEAN = 0.44                                            # round-4 confirmation: two-campaign mean xi_hat(32,768)
SHARE_HOLD = 0.03                                          # round-4 action 3: a sector waits only above this share
def corner_q(u, a):                                        # quantile of (u1 u2)^(-1/a): survival x^-a (1 + a ln x)
    return np.exp((-lambertw(-u / np.e, k=-1).real - 1) / a)
def tval4(name, U):
    kind, _, p = name.partition('_'); u1 = U[..., 0]; u2 = U[..., 1] if U.shape[-1] > 1 else None; u3 = U[..., 2] if U.shape[-1] > 2 else None
    if kind == 'gauss': return np.abs(norm.ppf(u1))
    if kind == 'lgn': return np.exp(float(p) * norm.ppf(u1))
    if kind == 'logk': return (-np.log(u1)) ** float(p)
    if kind == 'pareto': return u1 ** (-1 / float(p))
    if kind == 'corner': return (u1 * u2) ** (-1 / float(p))
    if kind == 'sparse': return np.abs(norm.ppf(u1)) + 5 * (u2 < 0.002) * u3 ** (-1 / float(p))
    if kind == 'offset': return 10 + u1 ** (-1 / 2)                                      # 10 + Pareto(2): a location offset
    if kind == 'masked': return np.abs(1 + 0.3 * norm.ppf(u1) + 0.01 * u2 ** (-1 / 1.5))  # Pareto(1.5) under every point
    if kind == 'masksp': return np.abs(norm.ppf(u1)) + (u2 < 0.002) * u3 ** (-1 / 1.5)    # sparse Pareto(1.5), mass 0.002
    raise ValueError(name)
def stats4(X):
    r = {}
    for nm, n in (('1', N1), ('2', N2)):
        Y = X[:, :, :n]; top = -np.sort(-np.partition(Y, n - K, axis=2)[:, :, n - K:], axis=2); mu = Y.mean(2, keepdims=True)
        r['h' + nm] = np.log(top[:, :, :K - 1] / top[:, :, K - 1:K]).mean(2).mean(1)
        ex = np.maximum(top - mu, 1e-300); r['e' + nm] = np.log(ex[:, :, :K - 1] / ex[:, :, K - 1:K]).mean(2).mean(1)
        r['smax' + nm] = (top[:, :, 0] / Y.sum(2)).max(1)
    return r
DIMS4 = {'corner': 2, 'sparse': 3, 'masked': 2, 'masksp': 3}
def sim4(name, G):
    parts = []; dm = DIMS4.get(name.partition('_')[0], 1)
    for c0 in range(0, G, 25):
        g = min(25, G - c0); U = np.clip(RNG4.random((g, R, N2, dm)), 1e-300, 1.0); parts.append(stats4(tval4(name, U)))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
print('\n[A2] round-4 rule, direct simulation (iid, 200 graphs x 2 independent campaigns per family; campaign tails a / b).')
print(f'     S = screened in either campaign (round 3: xi_hat(4096) > {XI_SCREEN} or share > {SMAX_SCREEN}); C3 = round-3 confirmation per')
print(f'     graph-campaign (screened and xi_hat(32,768) > {XI_CONFIRM}); C4 = round 4 (screened in either campaign and the two-campaign mean')
print(f'     xi_hat(32,768) > {XI2_MEAN}); U4 = the same without the screen (P1c, production-type); X = excess-Hill two-campaign mean > {XI2_MEAN}')
PAIRS = [('gauss', 'gauss'), ('lgn_1.25', 'lgn_1.25'), ('logk_3', 'logk_3'), ('pareto_3.5', 'pareto_3.5'), ('pareto_3', 'pareto_3'),
         ('pareto_2.75', 'pareto_2.75'), ('pareto_2.6667', 'pareto_2.6667'), ('pareto_2.6667', 'pareto_3.5'), ('corner_3.5', 'corner_3.5'),
         ('corner_2.6667', 'corner_2.6667'), ('corner_2.6667', 'corner_3.5'), ('pareto_2.5', 'pareto_2.5'), ('pareto_2', 'pareto_2'),
         ('pareto_2', 'pareto_2.3333'), ('sparse_2', 'sparse_2'), ('pareto_1.75', 'pareto_1.75'), ('offset', 'offset'), ('masked', 'masked'), ('masksp', 'masksp')]
rowsA2 = []
for fa, fb in PAIRS:
    sa, sb = sim4(fa, 200), sim4(fb, 200)
    Sa = (sa['h1'] > XI_SCREEN) | (sa['smax1'] > SMAX_SCREEN); Sb = (sb['h1'] > XI_SCREEN) | (sb['smax1'] > SMAX_SCREEN); F = Sa | Sb
    m2 = (sa['h2'] + sb['h2']) / 2; me = (sa['e2'] + sb['e2']) / 2
    C3 = ((Sa & (sa['h2'] > XI_CONFIRM)).mean() + (Sb & (sb['h2'] > XI_CONFIRM)).mean()) / 2
    r = dict(a=fa, b=fb, h1=float(np.median(sa['h1'])), h2=float(np.median(sa['h2'])), e2=float(np.median(sa['e2'])), S=float(F.mean()), C3=float(C3),
             C4=float((F & (m2 > XI2_MEAN)).mean()), U4=float((m2 > XI2_MEAN).mean()), X=float((me > XI2_MEAN).mean()))
    rowsA2.append(r)
    print(f'  {fa:>13s} / {fb:<13s} xi_hat a: 4096 {r["h1"]:.3f}, 32,768 {r["h2"]:.3f} (excess {r["e2"]:.3f})  S {100*r["S"]:5.1f}%  C3 {100*r["C3"]:5.1f}%  '
          f'C4 {100*r["C4"]:5.1f}%  U4 {100*r["U4"]:5.1f}%  X {100*r["X"]:5.1f}%', flush=True)
out['A2'] = rowsA2
# ------------------------------------------------------------------ [A3]
def topU(G, n, Rr=R):                                      # the K largest of n uniforms' reciprocals: K smallest uniforms, ascending
    Ex = RNG4.exponential(size=(G, Rr, K)); S = np.cumsum(Ex, -1); return S / (S[..., -1:] + RNG4.gamma(n - K + 1, size=(G, Rr, 1)))
def hill(top): return np.log(top[..., :K - 1] / top[..., K - 1:K]).mean(-1)
QF = {'gauss': (lambda u: norm.isf(u / 2), math.sqrt(2 / math.pi)), 'lgn_1.25': (lambda u: np.exp(1.25 * norm.isf(u)), math.exp(1.25 ** 2 / 2)),
      'logk_3': (lambda u: (-np.log(u)) ** 3, 6.0)}
def qf(name):
    if name in QF: return QF[name]
    kind, _, p = name.partition('_'); a = float(p)
    if kind == 'pareto': return (lambda u: u ** (-1 / a)), a / (a - 1)
    if kind == 'corner': return (lambda u: corner_q(u, a)), (a / (a - 1)) ** 2
    raise ValueError(name)
def campaign(name, G):
    q, mu = qf(name); A = q(topU(G, N1)); B = q(topU(G, N2 - N1))
    h1 = hill(A).mean(1); smax = (A[..., 0] / (A.sum(-1) + (N1 - K) * mu)).max(1)       # bulk of the sum at its mean
    M2 = -np.sort(-np.concatenate([A, B], -1), -1)[..., :K]; return (h1 > XI_SCREEN) | (smax > SMAX_SCREEN), hill(M2).mean(1)
NG, NB = 100000, 2
print(f'\n[A3] family-wise rates, exact top-order statistics ({NG*NB:,} graphs = {2*NG*NB:,} graph-campaigns per family). Expected counts if EVERY')
print('     graph had the tail: round 3 per graph-campaign x 40,800 (power 8,672); round 4 per graph x 20,400 (power 4,336). "<x" = none seen')
FAMS3 = [('gauss', 'gauss'), ('lgn_1.25', 'lgn_1.25'), ('logk_3', 'logk_3'), ('pareto_3', 'pareto_3'), ('corner_3', 'corner_3'), ('pareto_2.75', 'pareto_2.75'),
         ('pareto_2.6667', 'pareto_2.6667'), ('pareto_2.6667', 'pareto_3.5'), ('corner_2.6667', 'corner_2.6667'), ('corner_2.6667', 'corner_3.5'),
         ('pareto_2.5', 'pareto_2.5'), ('pareto_2', 'pareto_2'), ('pareto_2', 'pareto_2.3333'), ('corner_2', 'corner_2')]
rowsA3 = []
for fa, fb in FAMS3:
    c3 = c4 = cv = 0
    for _ in range(NB):
        Sa, ha = campaign(fa, NG); Sb, hb = campaign(fb, NG)
        c3 += (Sa & (ha > XI_CONFIRM)).sum() + (Sb & (hb > XI_CONFIRM)).sum(); c4 += ((Sa | Sb) & ((ha + hb) / 2 > XI2_MEAN)).sum()
        cv += ((Sa | Sb) & (ha > XI_CONFIRM) & (hb > XI_CONFIRM)).sum()
    p3, p4, pv = c3 / (2 * NG * NB), c4 / (NG * NB), cv / (NG * NB)
    fmt = lambda p, n: (f'{p:.2e} ({p*n:,.1f})' if p > 0 else f'<{1/(NG*NB*(2 if n > 30000 else 1)):.0e} (<{n/(NG*NB*(2 if n > 30000 else 1)):.1f})')
    rowsA3.append(dict(a=fa, b=fb, round3=p3, round4=p4, both042=pv))
    print(f'  {fa:>13s} / {fb:<13s} round 3: {fmt(p3, 40800)}, power {p3*8672:,.1f}   round 4: {fmt(p4, 20400)}, power {p4*4336:,.1f}   '
          f'(verifier\'s alternative, both campaigns > {XI_CONFIRM}: {pv:.2e})', flush=True)
out['A3'] = rowsA3
print('     production-time monitor: per graph and campaign, the mean over R = 64 replicates of the Hill index from the replicate\'s merged')
print(f'     top 16 at n_g points; flag if the two-campaign mean > {XI2_MEAN} (20,000 graphs per family)')
rowsPM = []
for n in (2 ** 18, 2 ** 22):
    line = f'       n_g = 2^{int(math.log2(n))}:'
    for fa, fb in (('lgn_1.25', 'lgn_1.25'), ('logk_3', 'logk_3'), ('corner_3', 'corner_3'), ('pareto_2.6667', 'pareto_2.6667'), ('corner_2.6667', 'corner_2.6667'),
                   ('pareto_2.5', 'pareto_2.5'), ('pareto_2', 'pareto_2'), ('pareto_2', 'pareto_2.3333')):
        qa, _ = qf(fa); qb, _ = qf(fb); ha = hill(qa(topU(20000, n, 64))).mean(1); hb = hill(qb(topU(20000, n, 64))).mean(1)
        p = float(((ha + hb) / 2 > XI2_MEAN).mean()); rowsPM.append(dict(n=n, a=fa, b=fb, rate=p)); line += f' {fa}/{fb} {100*p:.2f}%;'
    print(line, flush=True)
out['A3prod'] = rowsPM
# ------------------------------------------------------------------ [A4]
print('\n[A4] masked tails: share of the per-point variance carried by the Pareto(1.5) component, truncated at the sample maximum')
print('     (E[P^2; P < x_n] = 3 (x_n^(1/2) - 1) for P ~ Pareto(1.5), x_n = (n p)^(2/3) for a tail of mass p)')
rowsA4 = []
for nm, eps, p, body in (('masked: |1 + 0.3 N + 0.01 P|', 0.01, 1.0, 0.09), ('masksp: |N| + P on 0.2% of points', 1.0, 0.002, 1 - 2 / math.pi)):
    line = f'  {nm:36s}'
    for n in (N1, N2, 2 ** 22, 2 ** 26, 2 ** 30):
        xn = (n * p) ** (2 / 3); vt = eps ** 2 * p * 3 * (math.sqrt(xn) - 1) - (eps * p * 3) ** 2; sh = vt / (vt + body)
        rowsA4.append(dict(name=nm, n=n, share=sh)); line += f'  n = 2^{int(math.log2(n))}: {100*sh:4.1f}%'
    print(line)
out['A4'] = rowsA4
# ------------------------------------------------------------------ [B3]
import tarfile, collections, csv as _csv
TGZ = '/Users/zheng/Documents/Agent_LRI/LRI_C7_D3_HPC_production/run1-20260930-m4096_full.tgz'
if os.path.exists('run1-20260930-m4096/C7_result.json') and os.path.exists(TGZ):
    mx = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float)))
    with tarfile.open(TGZ, 'r:gz') as tf:
        for m in tf:
            if '/checkpoints/' not in m.name or not m.name.endswith('.json'): continue
            grp = m.name.split('/groups/')[1].split('/')[0]
            for r in json.load(tf.extractfile(m))['native']['rows']:
                d = mx[grp][r['graph']]; d[r['rep']] = max(d[r['rep']], float(r['max_abs']))
    XI = lambda v: float(np.log(v).std(ddof=1) * math.sqrt(6) / math.pi)
    def xis(grp): return {g: XI(np.array([v[k] for k in sorted(v)])) for g, v in mx[grp].items() if len(v) == 64 and min(v.values()) > 0}
    print('\n[B3] run1 block maxima (64 replicate maxima of |t| per graph and campaign, n_g points each): xi_sd = sd(ln max) sqrt(6)/pi')
    print('     quantiles q50/q90/q99/max per campaign; corr(a, b); graphs above 0.38 / 0.42 (a, b, both); "used" excludes graphs with t = 0')
    real3 = {}
    for s in SECT:
        for L in range(3, 8):
            A, B = xis(f'a_{s}_L{L}'), xis(f'b_{s}_L{L}'); gs = sorted(set(A) & set(B))
            if len(gs) < 3: print(f'     {s}_L{L}: {len(gs)} graphs used, skipped'); continue
            xa, xb = np.array([A[g] for g in gs]), np.array([B[g] for g in gs])
            qq = lambda v: '/'.join(f'{x:.2f}' for x in np.quantile(v, [.5, .9, .99])) + f'/{v.max():.2f}'
            real3[f'{s}_L{L}'] = dict(graphs=len(gs), corr=float(np.corrcoef(xa, xb)[0, 1]), xi_a={str(g): A[g] for g in gs}, xi_b={str(g): B[g] for g in gs})
            print(f'     {s}_L{L}: {len(gs)} graphs; xi_a {qq(xa)}, xi_b {qq(xb)}; corr {np.corrcoef(xa, xb)[0, 1]:.2f}; > 0.38: {np.sum(xa > .38)}, {np.sum(xb > .38)}, both '
                  f'{np.sum((xa > .38) & (xb > .38))}; > 0.42: {np.sum(xa > .42)}, {np.sum(xb > .42)}, both {np.sum((xa > .42) & (xb > .42))}')
    nul = RNG4.exponential(size=(20000, 64))
    print('     null (exact Frechet maxima, 64 blocks): ' + '; '.join(f'a = {a}: median {np.median(np.log(nul ** (-1 / a)).std(1, ddof=1) * math.sqrt(6) / math.pi):.3f}, '
          f'P(xi_sd > 0.42) {np.mean(np.log(nul ** (-1 / a)).std(1, ddof=1) * math.sqrt(6) / math.pi > .42):.4f}, P(> 0.53) {np.mean(np.log(nul ** (-1 / a)).std(1, ddof=1) * math.sqrt(6) / math.pi > .53):.4f}'
          for a in (3, 2.5, 2)))
    print('     cross-campaign shift: the face model a = r/(r - m) with rates 0.8 (a) and 0.7 (b) predicts xi_b = 1 - (8/7)(1 - xi_a)')
    for key in ('power_L7', 'power_L6', 'free_L7'):
        A, B = real3[key]['xi_a'], real3[key]['xi_b']; gs = list(A); xa = np.array([A[g] for g in gs]); xb = np.array([B[g] for g in gs])
        for lab, msk in (('all', np.ones(len(gs), bool)), ('mean xi > 0.42', (xa + xb) / 2 > .42)):
            if msk.sum() < 2: continue
            d = xb[msk] - xa[msk]; pr = (1 - 8 / 7 * (1 - xa[msk])) - xa[msk]
            print(f'       {key} {lab:15s} ({msk.sum():4d} graphs): mean xi_b - xi_a {d.mean():+.3f} +- {d.std(ddof=1)/math.sqrt(msk.sum()):.3f}; face model {pr.mean():+.3f}')
    # extreme power-L7 graphs: GEV MLE, replicate-mean shape, variance shares, screen-load analogue
    A, B = real3['power_L7']['xi_a'], real3['power_L7']['xi_b']; gs = [int(g) for g in A]
    po = json.load(open('partial_out.json')); J8 = {int(L): np.array(v) for L, v in po['J8'].items()}; j8 = J8[7][[0, 2]]
    Ra, Rb = graph_reps('a', 'power', 7), graph_reps('b', 'power', 7)
    tcomb = lambda Y: 3 * Y[:, 1] - Y[:, 0]                # L7: values = [norm w_A sum, norm w_B sum]; t = 3 w_B - w_A
    Va = {g: tcomb(Ra[g]).var(ddof=1) for g in Ra}; Vb = {g: tcomb(Rb[g]).var(ddof=1) for g in Rb}
    Wa = {g: (Ra[g] @ j8).var(ddof=1) for g in Ra}; Wb = {g: (Rb[g] @ j8).var(ddof=1) for g in Rb}
    both = [g for g in gs if A[str(g)] > .42 and B[str(g)] > .42]
    sh = lambda V, S: sum(V[g] for g in S) / sum(V.values())
    print(f'     power_L7: {len(both)} graphs with xi_sd > 0.42 in both campaigns ({100*len(both)/len(gs):.1f}%); their share of the group variance of the '
          f'replicate mean: t combination a {100*sh(Va, both):.2f}%, b {100*sh(Vb, both):.2f}%; C8 old-slot combination a {100*sh(Wa, both):.2f}%, b {100*sh(Wb, both):.2f}%')
    for c, X_, V_, W_ in (('a', A, Va, Wa), ('b', B, Vb, Wb)):
        Hs = [g for g in gs if X_[str(g)] > .42]
        print(f'       campaign {c}: {len(Hs)} graphs with xi_sd > 0.42 carry {100*sh(V_, Hs):.2f}% (t) / {100*sh(W_, Hs):.2f}% (C8 old slots) of the group variance')
    Ca, Cb = graph_cost('a', 'power', 7), graph_cost('b', 'power', 7)
    scr = [g for g in gs if A[str(g)] > .38 or B[str(g)] > .38]
    cs = (sum(Ca[g][1] for g in scr) + sum(Cb[g][1] for g in scr)) / (sum(v[1] for v in Ca.values()) + sum(v[1] for v in Cb.values()))
    print(f'     screen-load analogue: {len(scr)} power_L7 graphs ({100*len(scr)/len(gs):.1f}%) have xi_sd > 0.38 in either campaign and carry {100*cs:.2f}% of the group\'s busy '
          f'cost; at L8 the both-campaign 32,768-point re-runs of such graphs would cost 8 x that share of the power pass')
    top = sorted(gs, key=lambda g: -(A[str(g)] + B[str(g)]))[:8]
    def maxima(grp, g): v = mx[grp][g]; return np.array([v[k] for k in sorted(v)])
    gev = {}
    for g in top:
        ma, mb = maxima('a_power_L7', g), maxima('b_power_L7', g)
        fa_, fb_ = genextreme.fit(ma / np.median(ma)), genextreme.fit(mb / np.median(mb)); ya, yb = tcomb(Ra[g]), tcomb(Rb[g])
        gev[str(g)] = dict(xi_sd=(A[str(g)], B[str(g)]), gev=(-fa_[0], -fb_[0]), share=(Va[g] / sum(Va.values()), Vb[g] / sum(Vb.values())))
        print(f'       graph {g}: xi_sd a {A[str(g)]:.3f} b {B[str(g)]:.3f}; GEV MLE xi a {-fa_[0]:.2f} b {-fb_[0]:.2f}; variance share a {100*Va[g]/sum(Va.values()):.3f}% '
              f'b {100*Vb[g]/sum(Vb.values()):.3f}%; 64 replicate means of t: skew a {_skew(ya):+.2f} b {_skew(yb):+.2f}, excess kurtosis a {_kurt(ya):+.2f} b {_kurt(yb):+.2f}')
    out['B3'] = dict(groups={k: dict(graphs=v['graphs'], corr=v['corr']) for k, v in real3.items()},
                     xi={k: dict(a=v['xi_a'], b=v['xi_b']) for k, v in real3.items() if k in ('power_L7', 'power_L6')}, both042=both, gev=gev)
json.dump(out, open('tail_calib_out.json', 'w'), indent=1)
