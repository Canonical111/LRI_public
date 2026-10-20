# Margin re-derivation, first step (RECON section 6.3.6 action 3, section 7.2; repair round 4, item 1). Light: about 4 min.
# Read-only inputs: the frozen C7(3) payloads (LRI_C7_D3_HPC/inputs/packs) and tail_calib_out.json ([B3], run1 tail index).
# [M1] The d=3 rate line of every free L5-L7 and power L6/L7 payload is recomputed from the payload's own masks and forest
#      terms with the logic of regenerate_rates.cpp:16: per term p4 = 3|s| + 4 nu_N - 6 h (h = min overlap of s with the
#      term's monomial masks; nu_N = 1 if the numerator support lies in s), lifted into (0, 4] quarter units when p4 <= 0
#      ("clamped"), and the minimum over terms. It is compared with the payload's rate line. Raw valuations are tabulated:
#      clamped subsets by raw value, and "double-lift" subsets (raw <= -5), which need two units of cancellation.
#      Single-scale bound (why a rate-table face cannot have true margin below its table rate): along x_e -> lam x_e
#      (e in s), each forest term expands in lam^(p4_T/4 + integer), so the forest sum's leading exponent is congruent mod 1
#      to some term's p4/4 and, the integral being finite, positive; hence it is at least that term's lifted value, which
#      is at least the table's minimum. [M3] checks this numerically.
# [M2] run1's per-graph tail index (xi_sd from the 64 replicate maxima of |t|, tail_calib [B3]) against those features.
# [M3] Graphs 228, 1357, 318 and 3754 (the heaviest run1 power-L7 tails) and two light controls: the forest sum's exponent,
#      measured with mpmath (80 digits) from two scalings of the subset (1e-10, 1e-14) at a fixed random base point, at
#      every clamped subset (single scale), against the table rate and against the proposal rates 0.8 and 0.7 x table;
#      two-scale flags S1 < S2 with S1 or S2 a double-lift subset; and every chain of >= 3 nested scales inside the 6-edge
#      double-lift subset of graph 228 (120 digits). Exponent per level k of a flag: |S_k| + d ln|f| / d ln t_k, with the
#      other levels' scales fixed small; the weight is bounded at that level iff it is >= the proposal rate there.
import json, math, os, time, itertools
import numpy as np
import mpmath as mp
ROOT = '/Users/zheng/Documents/Agent_LRI/LRI_C7_D3_HPC/inputs/'
INV = json.load(open(ROOT + 'inventory.json'))
def load(sector, L, rec):
    with open(ROOT + f'packs/{sector}_L{L}.pack', 'rb') as fh:
        fh.seek(rec['offset']); t = fh.read(rec['length']).decode().split()
    L = int(t[1]); M = int(t[5]); T = int(t[6]); E = 2 * L; i = 7
    masks = [int(x) for x in t[i:i + M]]; i += M; terms = []
    for _ in range(T):
        n = int(t[i]); i += 1; ids = [int(x) for x in t[i:i + n]]; i += n; c = [int(x) for x in t[i:i + E]]; i += E; terms.append((ids, c))
    nr = int(t[i]); i += 1; rates = np.array([float(x) for x in t[i:i + nr]])
    return dict(id=int(t[2]), L=L, E=E, M=M, T=T, masks=masks, terms=terms, rates=rates, wb=float(t[4]))
def raw_rates(g):
    L, E = g['L'], g['E']; ALL = (1 << E) - 1; idx = np.arange(ALL + 1); pc = np.array([bin(s).count('1') for s in range(ALL + 1)])
    raw = np.full(ALL + 1, 1000); pos = np.full(ALL + 1, 1000)
    for ids, c in g['terms']:
        d = np.full(ALL + 1, 100, dtype=np.int16); d[[g['masks'][m] for m in ids]] = 0
        for b in range(E):                                 # Hamming distance to the nearest monomial mask (regenerate_rates.cpp)
            v = d.reshape(-1, 2, 1 << b); x = v[:, 0, :].copy(); y = v[:, 1, :].copy(); v[:, 0, :] = np.minimum(x, y + 1); v[:, 1, :] = np.minimum(y, x + 1)
        supp = sum(1 << j for j in range(E) if c[j]); h = (L - E + pc + d[ALL - idx]) // 2; nuN = ((idx & supp) == supp).astype(int)
        p4 = 3 * pc + 4 * nuN - 6 * h; cl = np.where(p4 <= 0, np.where(p4 % 4 == 0, 4, p4 % 4), p4)
        raw = np.minimum(raw, p4); pos = np.minimum(pos, cl)
    tab = pos * 0.25; tab[0] = 0; tab[ALL] = 0
    return raw, tab
pcount = lambda s: bin(s).count('1')
t0 = time.time(); out = {}
print('[M1] d=3 rate lines recomputed from masks and forest terms (regenerate_rates.cpp:16 logic) and compared with the payloads')
feats = {}
for sector, L in (('free', 5), ('free', 6), ('free', 7), ('power', 6), ('power', 7)):
    bad = 0; hist = {}; dbl = 0; tabcl = {}
    for rec in INV[sector][str(L)]:
        g = load(sector, L, rec); raw, tab = raw_rates(g); bad += not np.array_equal(tab, g['rates'])
        ALL = (1 << g['E']) - 1; S = np.arange(1, ALL); cl = S[raw[S] <= 0]
        for v in raw[cl]: hist[int(v)] = hist.get(int(v), 0) + 1
        for v in tab[cl]: tabcl[float(v)] = tabcl.get(float(v), 0) + 1
        dbl += bool((raw[cl] <= -5).any())
        if sector == 'power' and L == 7:
            feats[g['id']] = dict(M=g['M'], T=g['T'], clamped=int(len(cl)), raw3=int((raw[cl] == -3).sum()), raw0=int((raw[cl] == 0).sum()),
                                  double=int((raw[cl] <= -5).sum()), rmin=int(raw[cl].min()) if len(cl) else 0)
    n = len(INV[sector][str(L)])
    print(f'  {sector}_L{L}: {n} payloads, rate-line mismatches {bad}; clamped subsets by raw value (quarter units) '
          + ', '.join(f'{k}: {v}' for k, v in sorted(hist.items())) + '; their table rates ' + ', '.join(f'{k:g}: {v}' for k, v in sorted(tabcl.items()))
          + f'; graphs with double-lift subsets (raw <= -5): {dbl}')
    out[f'{sector}_L{L}'] = dict(payloads=n, mismatches=bad, raw_hist=hist, graphs_double=dbl)
print(f'  ({time.time()-t0:.0f} s)')
print('\n[M2] run1 power_L7 tail index (mean of xi_sd over campaigns a, b; tail_calib [B3]) against the rate-table features')
TC = json.load(open('tail_calib_out.json'))['B3']['xi']['power_L7']
gs = [g for g in feats if str(g) in TC['a']]; xi = np.array([(TC['a'][str(g)] + TC['b'][str(g)]) / 2 for g in gs])
from scipy.stats import spearmanr
for k in ('M', 'T', 'clamped', 'raw3', 'raw0', 'double'):
    v = np.array([feats[g][k] for g in gs]); print(f'  {k:8s} Spearman rho {spearmanr(v, xi).correlation:+.2f}; median {np.median(v[xi > .42]):.0f} where mean xi_sd > 0.42, {np.median(v[xi < .25]):.0f} where < 0.25')
dbl = np.array([feats[g]['double'] > 0 for g in gs])
print(f'  graphs with double-lift subsets: {dbl.sum()} of {len(gs)}; mean xi_sd {xi[dbl].mean():.3f} (with) vs {xi[~dbl].mean():.3f} (without); '
      f'mean xi_sd > 0.42: {np.sum(xi[dbl] > .42)} of {dbl.sum()} with, {np.sum(xi[~dbl] > .42)} of {(~dbl).sum()} without; max without {xi[~dbl].max():.3f}')
out['M2'] = dict(graphs=len(gs), double=int(dbl.sum()), heavy_with=int(np.sum(xi[dbl] > .42)), heavy_without=int(np.sum(xi[~dbl] > .42)), max_without=float(xi[~dbl].max()))
print('\n[M3] measured exponents of the forest sum f = prod x^(-1/4) sum_T N_T/(S U_T^(3/2)) (mpmath), against table and proposal rates')
class Kern:
    def __init__(self, g, dps):
        mp.mp.dps = dps; self.g = g; rng = np.random.default_rng(3); self.Y = [mp.mpf(int(v)) / 1000 for v in rng.integers(500, 2000, g['E'])]
    def f(self, x):
        g = self.g; E = g['E']; mono = [mp.fprod(x[e] for e in range(E) if m >> e & 1) for m in g['masks']]; S = mp.fsum(x); tot = mp.mpf(0)
        for ids, c in g['terms']:
            tot += mp.fsum(c[j] * x[j] for j in range(E) if c[j]) / (S * mp.fsum(mono[i] for i in ids) ** mp.mpf(1.5))
        return mp.fprod(xe ** mp.mpf(-0.25) for xe in x) * tot
    def expo(self, sets, k, a, b, fix):
        """exponent at level k of the flag `sets` (nested, inner first): |S_k| + slope of ln|f| in ln t_k, other levels at `fix`"""
        def val(t):
            x = list(self.Y)
            for j, S in enumerate(sets):
                sc = t if j == k else fix
                for e in range(self.g['E']):
                    if S >> e & 1: x[e] *= sc
            return mp.log(abs(self.f(x)))
        return pcount(sets[k]) + float((val(b) - val(a)) / (mp.log(b) - mp.log(a)))
recs = {r['id']: r for r in INV['power']['7']}
light = sorted([g for g in gs if feats[g]['double'] == 0 and feats[g]['M'] <= 300], key=lambda g: (TC['a'][str(g)] + TC['b'][str(g)]))[:2]
res3 = {}
for gid in (228, 1357, 318, 3754) + tuple(light):
    g = load('power', 7, recs[gid]); raw, tab = raw_rates(g); ALL = (1 << g['E']) - 1; K = Kern(g, 80)
    cl = [s for s in range(1, ALL) if raw[s] <= 0]; ms = np.array([K.expo([s], 0, mp.mpf('1e-10'), mp.mpf('1e-14'), 1) for s in cl]); tb = tab[cl]
    dl = [s for s in cl if raw[s] <= -5]
    line = (f'  graph {gid} (mean xi_sd {(TC["a"][str(gid)] + TC["b"][str(gid)]) / 2:.3f}; M {g["M"]}, T {g["T"]}): single scale, {len(cl)} clamped subsets: '
            f'measured - table min {np.min(ms - tb):+.3f}, max {np.max(ms - tb):+.3f}; equal (+-0.02) at {int(np.sum(abs(ms - tb) < .02))}; below 0.8 x table at '
            f'{int(np.sum(ms < 0.8 * tb - .02))}; double-lift subsets {len(dl)}: ' + ', '.join(f'|s| {pcount(s)} table {tab[s]:g} measured {m:.3f}' for s, m in zip(cl, ms) if raw[s] <= -5))
    r = dict(clamped=len(cl), min_diff=float(np.min(ms - tb)), equal=int(np.sum(abs(ms - tb) < .02)))
    if gid in (228, 3754):
        A_, B_, F_ = mp.mpf('1e-9'), mp.mpf('1e-13'), mp.mpf('1e-11'); nfl = nbad = 0; worst = 9.0
        for S2 in dl:
            for S1 in [t for t in range(1, S2) if t & S2 == t]:
                for k in (0, 1):
                    m = K.expo([S1, S2], k, A_, B_, F_); rr = 0.8 * tab[[S1, S2][k]]; worst = min(worst, m - rr); nbad += m < rr - .02
                nfl += 1
        for S1 in dl:
            for S2 in [t for t in range(S1 + 1, ALL) if t & S1 == S1]:
                for k in (0, 1):
                    m = K.expo([S1, S2], k, A_, B_, F_); rr = 0.8 * tab[[S1, S2][k]]; worst = min(worst, m - rr); nbad += m < rr - .02
                nfl += 1
        line += f'\n      two-scale flags with a double-lift subset as inner or outer set: {nfl}; levels below the proposal rate (0.8 x table): {nbad}; min(measured - rate) {worst:+.3f}'
        r.update(flags2=nfl, flags2_below=int(nbad))
    if gid == 228:
        s0 = min(dl, key=pcount); el = [e for e in range(g['E']) if s0 >> e & 1]; K = Kern(g, 120)
        def chains(elems):
            if not elems: yield []; return
            for k in range(1, len(elems) + 1):
                for blk in itertools.combinations(elems, k):
                    for ch in chains([e for e in elems if e not in blk]): yield [blk] + ch
        nch = nbad = 0; worst = 9.0; A_, B_, F_ = mp.mpf('1e-6'), mp.mpf('1e-8'), mp.mpf('1e-4')
        for parts in chains(el):
            if len(parts) < 3: continue
            sets = list(itertools.accumulate([sum(1 << e for e in p) for p in parts], lambda a, b: a | b)); nch += 1
            for k in range(len(sets)):
                m = K.expo(sets, k, A_, B_, F_); rr = 0.8 * tab[sets[k]]; worst = min(worst, m - rr); nbad += m < rr - .02
        line += f'\n      chains of >= 3 scales inside the {pcount(s0)}-edge double-lift subset: {nch}; levels below the proposal rate: {nbad}; min(measured - rate) {worst:+.3f}'
        r.update(chains=nch, chains_below=int(nbad))
    res3[str(gid)] = r; print(line, flush=True)
out['M3'] = res3
print(f'  ({time.time()-t0:.0f} s in all)')
json.dump(out, open('margin_probe_out.json', 'w'), indent=1)
