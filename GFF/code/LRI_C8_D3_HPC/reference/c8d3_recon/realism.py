# Allocation-realism factor of the cost table (RECON section 6.3.5; repair round 2, findings 3 and 6).
# The Neyman metric (sum_g sigma_g sqrt c_g)^2 is reached only by an oracle design. A production design loses:
#  (i)  sigma noise: n_g is set from pilot sigma estimates with R_p replicates;
#  (ii) power-of-two counts (production.py:154; C62d's design rounds n_g to powers of two);
#  (iii) same-data optimism: for L<=7 the metric itself is evaluated on the replicates that estimate sigma.
# The penalty of a design n_g ∝ s_g/sqrt(c_g) evaluated with the true sigma is
#   P = (sum sigma^2/s sqrt c)(sum s sqrt c)/(sum sigma sqrt c)^2  >= 1   (Cauchy-Schwarz).
# (i) is measured on run1 L6/L7 graphs by splitting the 64 replicates: design on R_p of them, evaluate with the held-out
# rest (empirical, includes any non-Gaussian replicate distribution at run1 counts); the Gaussian value is printed
# beside it. (ii) is the exact log-uniform value and its realised value on the same graphs. Light: seconds.
from common import *
from math import gamma, sqrt, log
PG = json.load(open('pergraph_out.json')); po = json.load(open('partial_out.json')); J8 = {int(L): np.array(v) for L, v in po['J8'].items()}
def gauss(Rp):
    k = Rp - 1; return sqrt(2 / k) * gamma((k + 1) / 2) / gamma(k / 2) * sqrt(k / 2) * gamma((k - 1) / 2) / gamma(k / 2)
def pen(sig, s, c):
    w = np.sqrt(c); return float((sig ** 2 / s * w).sum() * (s * w).sum() / (sig * w).sum() ** 2)
out = {}
print('[1] sigma-noise penalty of a design from R_p pilot replicates (L6/L7, C8 old-slot contribution; mean over disjoint splits)')
for Rp in (8, 16):
    vals = []
    for L in (6, 7):
        k = 8 - L; idx = list(range(k)) + list(range(k + 1, 2 * k + 1)); j8 = J8[L][idx]
        for s in SECT:
            for t in CAMP:
                G = graph_reps(t, s, L); C = graph_cost(t, s, L)
                gs = [g for g in G if C[g][0] > 0]
                Y = np.array([G[g] @ j8 for g in gs])               # graphs x 64 replicate values
                c = np.array([C[g][1] / C[g][0] for g in gs])
                ok = Y.std(1) > 0; Y = Y[ok]; c = c[ok]
                ps = []
                for j in range(64 // Rp):
                    m = np.zeros(64, bool); m[j * Rp:(j + 1) * Rp] = True
                    s_est = Y[:, m].std(1, ddof=1); s_true = Y[:, ~m].std(1, ddof=1)
                    s_est = np.maximum(s_est, 1e-300); ps.append(pen(s_true, s_est, c))
                # the held-out sigma has its own noise (64 - R_p replicates): its denominator (sum s_true sqrt c)^2 is low
                # by about c4(64 - R_p)^2, which inflates the raw penalty; corr removes that first-order bias
                kh = 64 - Rp - 1; c4h = sqrt(2 / kh) * gamma((kh + 1) / 2) / gamma(kh / 2); corr = np.mean(ps) * c4h ** 2
                vals.append(corr); out[f'noise|R{Rp}|{t}_{s}_L{L}'] = float(corr)
                print(f'    R_p={Rp:2d}  {t}_{s}_L{L}: raw {np.mean(ps):.3f}, held-out-noise corrected {corr:.3f}  ({len(ps)} splits, {len(c)} graphs)')
    print(f'    R_p={Rp:2d}: empirical (corrected) median {np.median(vals):.3f}, range {min(vals):.3f}..{max(vals):.3f}; Gaussian {gauss(Rp):.3f}')
    out[f'noise|R{Rp}|median'] = float(np.median(vals)); out[f'noise|R{Rp}|max'] = float(max(vals)); out[f'noise|R{Rp}|gauss'] = gauss(Rp)
print('[2] power-of-two counts: E[e]E[1/e] for e log-uniform on [2^-1/2, 2^1/2] (nearest power of two in log2)')
p2 = ((sqrt(2) - 1 / sqrt(2)) / log(2)) ** 2; out['pow2|exact'] = p2
print(f'    exact: {p2:.4f}')
vals = []
for L in (6, 7):
    for s in SECT:
        for t in CAMP:
            per = PG[f'{t}|{s}|{L}']['per']; sg = np.array([p['sig8'] for p in per]); c = np.array([p['cpp'] for p in per])
            ok = sg > 0; sg = sg[ok]; c = c[ok]
            nopt = sg / np.sqrt(c); nopt *= 2 ** 20 / np.median(nopt)
            for sh in np.linspace(0, 1, 8, endpoint=False):     # average over the global scale's position between powers of two
                n2 = 2.0 ** np.round(np.log2(nopt) + sh)
                vals.append(float((sg ** 2 / n2).sum() * (n2 * c).sum() / (sg * np.sqrt(c)).sum() ** 2))
print(f'    realised on run1 L6/L7 graphs (8 global offsets x 8 groups): mean {np.mean(vals):.4f}, range {min(vals):.4f}..{max(vals):.4f}')
out['pow2|realised_mean'] = float(np.mean(vals))
print('[3] same-data optimism of the L<=7 metric (Gaussian): (sum s sqrt c)^2 / (sum sigma sqrt c)^2 = c4(R)^2 at R = 64')
k = 63; c4 = sqrt(2 / k) * gamma((k + 1) / 2) / gamma(k / 2); out['samedata|R64'] = 1 / c4 ** 2
print(f'    c4(64)^2 = {c4**2:.4f}: the run1-based metric is low by {100*(1-c4**2):.1f}%; the extrapolated L8 metric has no such term')
print('[4] heavier-tailed pilot replicates (assumption for the high band): Var(s^2)/sigma^4 = 2/(R-1) + kex/R; the penalty')
print('    E[e]E[1/e] is computed for e = s/sigma with s^2 ~ Gamma matched to that variance (Gaussian kex = 0 reproduces [1])')
def penk(Rp, kex):
    v = 2 / (Rp - 1) + kex / Rp; a = 1 / v          # s^2/sigma^2 ~ Gamma(shape a, scale 1/a): mean 1, variance 1/a = v
    Ee = gamma(a + .5) / gamma(a) / sqrt(a); Einv = gamma(a - .5) / gamma(a) * sqrt(a); return Ee * Einv
for kex in (0, 1, 2, 4):
    print(f'    R_p= 8, excess kurtosis {kex}: x{penk(8, kex):.3f}   R_p=16: x{penk(16, kex):.3f}')
    out[f'noise|kex{kex}|R8'] = penk(8, kex); out[f'noise|kex{kex}|R16'] = penk(16, kex)
# realism factors used by final_table.py (applied to the non-floor part of the busy cost only)
R8 = max(out['noise|R8|median'], gauss(8))
out['REAL_central'] = R8 * p2 * out['samedata|R64']
out['REAL_high'] = out['noise|kex2|R8'] * p2 * out['samedata|R64']
out['REAL_R16'] = max(out['noise|R16|median'], gauss(16)) * p2 * out['samedata|R64']
print(f'[5] realism on the non-floor busy cost: central (R_p = 8) {R8:.3f} x pow2 {p2:.4f} x same-data {out["samedata|R64"]:.3f} = x{out["REAL_central"]:.3f};'
      f' high band (excess kurtosis 2 at pilot counts) x{out["REAL_high"]:.3f}; option R_p = 16: x{out["REAL_R16"]:.3f}. Floor-bound graphs: x1')
json.dump(out, open('realism_out.json', 'w'), indent=1)
