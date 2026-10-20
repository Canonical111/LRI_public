# Per-graph L7->L8 cost factor kappa for the C8(3) cost model (RECON section 6.3.4; repair round 1, findings 2, 7, 8).
# Replaces the hand-typed per-point factors (free 7.0, power 4.5) of the first revision.
#
# The top-loop metric is M_L = (sum_g sigma_g sqrt(c_g))^2 = N^2 (mean sigma)^2 (mean sqrt c)^2 x corr, with
# corr = [mean(sigma sqrt c)/(mean sigma mean sqrt c)]^2 (toploop.py). The cost term of the L7->L8 growth is therefore
#   kappa = (mean_g sqrt c8_g)^2 / (mean_g sqrt c7_g)^2          (unweighted over graphs; NOT a sample-weighted mean),
# and the sigma-cost correlation stays a separate factor (corr, 1.04 [1.0, 1.12], costmodel.py). At L7, log sigma_g of
# D_{7,0} and log c_g are uncorrelated (r = -0.025 .. +0.024, checks.py [10]), so no sigma profile enters here.
# The L8 side is built graph by graph:
#   sizes     : size_probe.cpp on classes8.txt (M, T, products + trie addends A, max forest size fmax): the same
#               d-independent bodies as the payloads. It reproduces C7(3) inventory.json M and T and the kernel's
#               prepare() op counts (opcount.py, vendored here: products and trie addends re-derived from every C7(3)
#               payload in the frozen packs, 0 mismatches over all 3,511 L3-L7 kernels, out/opcount.log), and C62d's L8 census.
#   promotion : logistic models q, mp ~ [1, fmax, log T, L] fitted per (sector, campaign) on all non-primitive L5-L7
#               graphs (primitives promote 0 at L6/L7). Scenario = the L at which the loop term is evaluated:
#               low 7 (no growth beyond the graphs' own fmax and T), central 8, high 9 (twice the per-loop growth).
#   cost law  : the NNLS tier law c = c0 + a A + q (bq + b A) + mp (bm + c A), fitted on all L7 graphs (mixed CPUs; it
#               reproduces the kernel note's coefficients). Fixed per-call parts (c0, bq, bm) grow by E8/E7 = 16/14
#               (variant E) or by their fitted L6->L7 growth (variant G).
#   kappa     : model(L8)/model(L7), the same promotion fit evaluated on the L7 graphs (bias-cancelled); the direct
#               ratio model(L8)/actual(L7) is printed too. Part [A] backtests the whole pipeline on L6->L7.
from common import *
import csv
from scipy.optimize import nnls, least_squares
SZ = {}
for L in range(3, 9):
    for r in csv.DictReader(open(f'sizes_L{L}.csv')):
        SZ[(L, int(r['id']))] = r
def size(L, g):
    r = SZ[(L, g)]; return dict(T=int(r['T']), M=int(r['M']), A=int(r['addends']) + int(r['products']), fmax=int(r['fmax']), prim=int(r['primitive']), sG=int(r['sG']), status=r['status'])
# ---------- per-graph run1 data
ROWS = []
for key, v in CK['per_graph'].items():
    grp, g = key.split('|'); t, s, LL = grp.split('_'); L = int(LL[1:]); g = int(g)
    ROWS.append(dict(t=t, s=s, L=L, g=g, n=v[0], cpp=v[1] / v[0], q=v[2] / v[0], mp=v[3] / v[0], **size(L, g)))
def sel(**kw): return [r for r in ROWS if all(r[k] == v for k, v in kw.items())]
# ---------- promotion model
FE = lambda r, L: np.array([1.0, r['fmax'], np.log(max(r['T'], 1)), L])
def fit_frac(rs, key):
    X = np.array([FE(r, r['L']) for r in rs]); y = np.clip(np.array([r[key] for r in rs]), 1e-6, 1 - 1e-6)
    def res(b):
        p = 1 / (1 + np.exp(-(X @ b))); return (p - y) / np.sqrt(p * (1 - p) + 1e-4)
    return least_squares(res, np.zeros(4)).x
def frac(b, r, L):
    return 0.0 if r['prim'] else float(1 / (1 + np.exp(-(FE(r, L) @ b))))
# ---------- cost law
def fit_law(rs):
    X = np.array([[1, r['A'], r['q'], r['q'] * r['A'], r['mp'], r['mp'] * r['A']] for r in rs]); y = np.array([r['cpp'] * 1e6 for r in rs])
    sw = np.sqrt(1 / y); return nnls(X * sw[:, None], y * sw)[0]   # us; relative-error weighting (as the kernel note's fit)
def law_cost(co, A, q, mp):  # busy core-s per point
    return 1e-6 * (co[0] + co[1] * A + q * (co[2] + co[3] * A) + mp * (co[4] + co[5] * A))
def grow_fixed(co, f0, fq, fm):
    c = co.copy(); c[0] *= f0; c[2] *= fq; c[4] *= fm; return c
# ================= backtest: predict L6->L7 from L<=6 information only
msq = lambda c: float(np.mean(np.sqrt(c)) ** 2)          # (mean_g sqrt c_g)^2, the metric's cost term
print('[A] backtest on L6->L7 (promotion fit on L5-L6, cost law fitted on L6; flat kappa = (mean sqrt c)^2 ratio)')
law6 = fit_law(sel(L=6)); law5 = fit_law(sel(L=5))
BT = {}; BTP = {}
for s in SECT:
    for t in CAMP:
        r6 = sel(s=s, t=t, L=6); r7 = sel(s=s, t=t, L=7)
        tr = [r for r in sel(s=s, t=t) if r['L'] in (5, 6) and not r['prim']]
        bq, bm = fit_frac(tr, 'q'), fit_frac(tr, 'mp')
        BTP[(s, t)] = dict(q_pred=float(np.mean([frac(bq, r, 7) for r in r7])), q_act=float(np.mean([r['q'] for r in r7])),
                           mp_pred=float(np.mean([frac(bm, r, 7) for r in r7])), mp_act=float(np.mean([r['mp'] for r in r7])))
        c6 = np.array([r['cpp'] for r in r6]); c7 = np.array([r['cpp'] for r in r7]); act = msq(c7) / msq(c6)
        A6 = np.array([r['A'] for r in r6]); A7 = np.array([r['A'] for r in r7])
        c6m = law_cost(law6, A6, np.array([frac(bq, r, 6) for r in r6]), np.array([frac(bm, r, 6) for r in r6]))
        out = {}
        for var, f in (('E', (14 / 12,) * 3), ('G', (law6[0] / law5[0], law6[2] / law5[2], law6[4] / law5[4]))):
            c7m = law_cost(grow_fixed(law6, *f), A7, np.array([frac(bq, r, 7) for r in r7]), np.array([frac(bm, r, 7) for r in r7]))
            out[var] = dict(direct=msq(c7m) / msq(c6), cancelled=msq(c7m) / msq(c6m))
        BT[(s, t)] = dict(actual=act, **{v: o for v, o in out.items()})
        print(f'    {t}_{s}: actual {act:5.2f}; predicted bias-cancelled E {out["E"]["cancelled"]:5.2f} ({out["E"]["cancelled"]/act:.2f}x) G {out["G"]["cancelled"]:5.2f} ({out["G"]["cancelled"]/act:.2f}x); direct E {out["E"]["direct"]:5.2f} G {out["G"]["direct"]:5.2f} ({out["G"]["direct"]/act:.2f}x)')
# ================= L7 -> L8
law7 = fit_law(sel(L=7))
print('[B] L7 cost law (NNLS on all L7 graphs, mixed CPUs): c0 %.2f us, ld %.3f ns/op, quad %.1f us + %.2f ns/op, GMP %.0f us + %.2f ns/op' % (law7[0], law7[1] * 1e3, law7[2], law7[3] * 1e3, law7[4], law7[5] * 1e3))
GROW = dict(E=(16 / 14,) * 3, G=(law7[0] / law6[0], law7[2] / law6[2], law7[4] / law6[4]))
print('    fixed parts (c0, quad, GMP) grow L7->L8 by: variant E %s; variant G (fitted L6->L7 growth) %s' % (tuple(round(x, 2) for x in GROW['E']), tuple(round(x, 2) for x in GROW['G'])))
L8 = {s: [size(8, g) | dict(g=g) for (L, g), r in SZ.items() if L == 8 and r['status'] == s and r['sG'] != '4'] for s in SECT}
print('    L8 kernels: free %d (primitive %d), power %d' % (len(L8['free']), sum(r['prim'] for r in L8['free']), len(L8['power'])))
SCEN = dict(low=7, central=8, high=9)   # L at which the per-loop promotion term is evaluated (7 = no growth beyond features)
RES = {}; POP = {}
for s in SECT:
    for t in CAMP:
        r7 = sel(s=s, t=t, L=7); c7 = np.array([r['cpp'] for r in r7]); A7 = np.array([r['A'] for r in r7])
        tr = [r for r in sel(s=s, t=t) if r['L'] in (5, 6, 7) and not r['prim']]
        bq, bm = fit_frac(tr, 'q'), fit_frac(tr, 'mp')
        q7m = np.array([frac(bq, r, 7) for r in r7]); m7m = np.array([frac(bm, r, 7) for r in r7])
        c7m = law_cost(law7, A7, q7m, m7m); cal = msq(c7) / msq(c7m)      # model calibration at L7 (bias cancels in the ratio)
        A8 = np.array([r['A'] for r in L8[s]], float); T8 = np.array([r['T'] for r in L8[s]])
        hiT = T8 >= 96 if s == 'free' else T8 >= 48
        out = {}
        for sc, Lev in SCEN.items():
            q8 = np.array([frac(bq, r, Lev) for r in L8[s]]); m8 = np.array([frac(bm, r, Lev) for r in L8[s]])
            for var in ('E', 'G'):
                co = grow_fixed(law7, *GROW[var]); c8 = law_cost(co, A8, q8, m8)
                w = np.sqrt(c8); w = w / w.sum()   # CPU share per graph at the Neyman optimum if sigma is independent of cost
                ti = dict(ld=float(w @ (1e-6 * (co[0] + co[1] * A8) / c8)), quad=float(w @ (1e-6 * q8 * (co[2] + co[3] * A8) / c8)), mp=float(w @ (1e-6 * m8 * (co[4] + co[5] * A8) / c8)))
                out[(sc, var)] = dict(kappa=msq(c8) / msq(c7m), direct=msq(c8) / msq(c7), samplemean_ratio=float(c8.mean() / (sum(r['cpp'] * r['n'] for r in r7) / sum(r['n'] for r in r7))),
                                      q=float(q8.mean()), mp=float(m8.mean()), q_hiT=float(q8[hiT].mean()), mp_hiT=float(m8[hiT].mean()), cpp_mean_us=float(c8.mean() * 1e6), tiers=ti)
                if (sc, var) == ('central', 'G'): POP[f'{s}|{t}'] = dict(c8=(c8 * cal).tolist(), nref=float(np.median([r['n'] for r in r7])) / 64)
        # repair round 3 (verifier nits 4/13): the same central (promotion at L = 8, variant G) with the mp fraction deflated by
        # this campaign's measured mp over-prediction in the [A]/[D] backtest (mp predicted / actual at L6->L7)
        mpmiss = BTP[(s, t)]['mp_pred'] / BTP[(s, t)]['mp_act']
        q8 = np.array([frac(bq, r, 8) for r in L8[s]]); m8 = np.array([frac(bm, r, 8) for r in L8[s]]) / mpmiss
        co = grow_fixed(law7, *GROW['G']); c8 = law_cost(co, A8, q8, m8); w = np.sqrt(c8); w = w / w.sum()
        mpd = dict(mpmiss=mpmiss, kappa=msq(c8) / msq(c7m), mp=float(m8.mean()),
                   tiers=dict(ld=float(w @ (1e-6 * (co[0] + co[1] * A8) / c8)), quad=float(w @ (1e-6 * q8 * (co[2] + co[3] * A8) / c8)), mp=float(w @ (1e-6 * m8 * (co[4] + co[5] * A8) / c8))))
        RES[f'{s}|{t}'] = dict(cal=cal, out={f'{a}|{b}': v for (a, b), v in out.items()}, mpdefl=mpd)
        print(f'  {t}_{s}: L7 actual per-graph mean q {np.mean([r["q"] for r in r7]):.3f} mp {np.mean([r["mp"] for r in r7]):.4f}; model at L7 q {q7m.mean():.3f} mp {m7m.mean():.4f}; calibration actual/model (mean sqrt c)^2 = {cal:.3f}')
        for (sc, var), o in out.items():
            ti = o['tiers']
            print(f'     {sc:7s} {var}: L8 mean q {o["q"]:.3f} mp {o["mp"]:.4f} (T>={96 if s=="free" else 48}: q {o["q_hiT"]:.2f} mp {o["mp_hiT"]:.3f}); mean cost {o["cpp_mean_us"]:5.0f} us; kappa {o["kappa"]:5.2f} (direct {o["direct"]:5.2f}; sample-mean cost ratio {o["samplemean_ratio"]:5.2f}); CPU tiers ld {ti["ld"]:.2f} quad {ti["quad"]:.2f} GMP {ti["mp"]:.2f}')
# central = (promotion at L=8, variant G, bias-cancelled); band = min/max over the 6 (scenario, variant) combinations
K = {}
for key, v in RES.items():
    o = v['out']; ks = [x['kappa'] for x in o.values()]
    K[key] = dict(central=o['central|G']['kappa'], low=min(ks), high=max(ks), tiers=o['central|G']['tiers'], tiers_high=o['high|G']['tiers'], tiers_mpdefl=v['mpdefl']['tiers'])
print('[C] flat kappa(L7->L8) = (mean sqrt c8)^2/(mean sqrt c7)^2 per campaign, central [band]; CPU tier shares at the optimum (central):')
for k, v in K.items(): print(f'    {k:11s} {v["central"]:5.2f}  [{v["low"]:.2f}, {v["high"]:.2f}]   ld {v["tiers"]["ld"]:.2f} quad {v["tiers"]["quad"]:.2f} GMP {v["tiers"]["mp"]:.2f}')
print('[D] promotion part of the [A] backtest (repair round 2, finding 7): the L5-L6 logistic fit evaluated at L = 7 on every L7 graph')
print('    (per-graph means over all L7 graphs of the group; primitives promote 0 in both), against the measured run1 fractions:')
for (s, t), v in BTP.items():
    print(f"    {t}_{s}: q predicted {v['q_pred']:.4f} actual {v['q_act']:.4f} ({100*(v['q_pred']/v['q_act']-1):+.1f}%);  mp predicted {v['mp_pred']:.5f} actual {v['mp_act']:.5f} ({100*(v['mp_pred']/v['mp_act']-1):+.0f}%)")
print('[E] central (promotion at L = 8, variant G) with the L8 mp fractions deflated by the [D] mp over-prediction (repair round 3):')
for k, v in RES.items():
    m = v['mpdefl']; ti = m['tiers']; t0 = K[k]['tiers']
    print(f"    {k:11s} mp / {m['mpmiss']:.3f}: L8 mean mp {m['mp']:.4f}; kappa {m['kappa']:5.2f} (undeflated {K[k]['central']:.2f}); CPU tiers ld {ti['ld']:.2f} quad {ti['quad']:.2f} GMP {ti['mp']:.2f} (undeflated GMP {t0['mp']:.2f})")
json.dump(dict(kappa=K, results=RES, backtest={f'{s}|{t}': v for (s, t), v in BT.items()}, backtest_promotion={f'{s}|{t}': v for (s, t), v in BTP.items()}, pop=POP, law7=law7.tolist(), law6=law6.tolist(), grow=GROW), open('l8cost_out.json', 'w'))
