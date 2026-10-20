# Cost table of RECON section 6.3.5 (repair round 1): allocated core-h against absolute and relative C8(3) SE.
# Population: every L<=7 graph of run1 (sigma of its C8 contribution x sqrt(F_L), busy core-s per point, run1 points
# per replicate as the reference count) and every one of the 20,400 L8 kernels of the size probe, with its modelled
# per-point cost (l8cost.py, central, calibrated to L7) and a sigma drawn from the measured L7 D_{7,0} sigmas
# independently of cost (seeded), rescaled so that the population reproduces the L8 metric of costmodel.py exactly.
# Allocation: exact optimum of  min sum n_g c_g  s.t.  Var(C8) = SE^2,  n_g >= FLOOR, with per-point variance
# sigma_g^2 (n_ref,g / n_g)^(2 alpha - 1) (alpha = QMC rate; alpha = 1/2 is plain Neyman). Campaigns a and b: weights 1/2.
# Repair round 2 (findings 1-4, 6): the L8 per-graph costs follow the corrected kappa central (costmodel.py); the realism
# factor is no longer a flat x1.10 on everything: realism.py's x1.140 (R=8 pilot sigma noise x power-of-two counts x
# same-data) multiplies only the NON-floor part of the busy cost (floor-bound graphs have fixed n_g, so no Neyman
# misallocation; exact at alpha = 1/2 when the floor set is unchanged, an approximation otherwise). The high band uses
# x1.255 (pilot replicates with excess kurtosis 2). The 'd=2 growth' column is computed at |C8| = 1,500.
from common import *
PG = json.load(open('pergraph_out.json')); CM = json.load(open('costmodel_out.json')); TL = json.load(open('toploop_out.json'))
LC = json.load(open('l8cost_out.json'))
FL = {tuple([k.split('|')[0], int(k.split('|')[1])]): v for k, v in CM['FL'].items()}
G8 = {tuple(k.split('|')): v for k, v in CM['G8'].items()}; KAP = {tuple(k.split('|')): v for k, v in CM['KAP'].items()}
ZC = {'free': 1.02, 'power': 1.07}
KAPM = {tuple(k.split('|')): v for k, v in CM['KAPmodel'].items()}   # l8cost central, before the backtest correction
RL = json.load(open('realism_out.json')); REAL_C, REAL_HI = RL['REAL_central'], RL['REAL_high']
ALLOC_BUSY = 10516 / 9681.8      # x1.086 assumes optimisation #3 (bounded tasks, no small tail block)
R = 64; FLOOR = 4096
RNG = np.random.default_rng(20261003)
SIGDRAW = {}
L8_STRESS = CM['out']['stress_d2growth']['factor']   # C62d's relative L7->L8 growth applied to d=3 (finding 1)
def population(t, i):
    """arrays (sigma_ref [C8 units per point], cost [core-s/point], n_ref [points/replicate]) for campaign t;
    scenario i = 0 central, 1 low, 2 high, 3 'd=2 growth' stress (central with the L8 metric growth x L8_STRESS)"""
    st = i == 3; i = 0 if st else i
    sig, cst, nref = [], [], []
    for s in SECT:
        for L in LOOPS:
            f = FL[(s, L)][i]
            for p in PG[f'{t}|{s}|{L}']['per']:
                sig.append(p['sig8'] * f ** .5 * (ZC[s] ** .5 if L == 7 else 1)); cst.append(p['cpp']); nref.append(p['n'])
        P = LC['pop'][f'{s}|{t}']; c8 = np.array(P['c8']) * KAP[(s, t)][i] / KAPM[(s, t)]
        if (s, t) not in SIGDRAW:
            s7 = np.array([p['sigt'] for p in PG[f'{t}|{s}|7']['per'] if p['sigt'] > 0]); SIGDRAW[(s, t)] = RNG.choice(s7, size=len(c8))
        sg = SIGDRAW[(s, t)].copy()
        target = (TL[f'{s}|7|{t}']['M'] * G8[(s, t)][i] * (L8_STRESS if st else 1) * 3600) ** .5   # sqrt metric, core-s^.5 x C8
        sg *= target / np.sum(sg * np.sqrt(c8))
        sig += list(sg); cst += list(c8); nref += [P['nref']] * len(c8)
    return np.array(sig), np.array(cst), np.array(nref)
POPS = {(t, i): population(t, i) for t in CAMP for i in range(4)}
def plan(SE, i, alpha=0.5, floor=FLOOR):
    """busy core-h at the exact optimum; returns (busy, floor-binding fraction, Neyman-without-floor busy, floor-bound busy)"""
    P = [POPS[(t, i)] for t in CAMP]
    # Var(C8) = sum over campaigns of (1/4) sum_g sigma_g^2 nref^(2a-1) / (R n_g^(2a)) ; cost = sum R n_g c_g
    k = [0.25 * p[0] ** 2 * p[2] ** (2 * alpha - 1) / R for p in P]
    def alloc(lam, fl):
        return [np.maximum(fl, (lam * 2 * alpha * kk / (R * p[1])) ** (1 / (2 * alpha + 1))) for kk, p in zip(k, P)]
    def var(ns): return sum((kk / n ** (2 * alpha)).sum() for kk, n in zip(k, ns))
    def solve(fl):
        lo, hi = 1e-30, 1e30
        for _ in range(300):
            mid = (lo * hi) ** .5
            if var(alloc(mid, fl)) > SE ** 2: lo = mid
            else: hi = mid
        ns = alloc(hi, fl); return ns, sum((R * n * p[1]).sum() for n, p in zip(ns, P)) / 3600
    ns, busy = solve(floor); _, busy0 = solve(0.0)
    bind = sum((n <= floor * 1.000001).sum() for n in ns) / sum(len(n) for n in ns)
    bfloor = sum((R * n * p[1] * (n <= floor * 1.000001)).sum() for n, p in zip(ns, P)) / 3600
    return busy, bind, busy0, bfloor
def alloc(pl, real):
    """allocated core-h: realism on the non-floor part only, then allocated/busy"""
    busy, _, _, bfl = pl; return (bfl + real * (busy - bfl)) * ALLOC_BUSY
print('M_eff check (alpha 1/2, no floor, SE 1): ', [round(plan(1.0, i, 0.5, 0.0)[0]) for i in range(4)], ' costmodel:', [round(CM['out'][k]['Meff']) for k in ('central', 'low', 'high')], round(CM['out']['stress_d2growth']['Meff']))
day_run1 = 10516 / 7.05 * 24
# |C8| band for the relative-SE rows (repair round 3, verifier nit 5): the low edge 1,050 covers the slot methods' top-sum
# backtest errors (E1 +-1.4%, lin +4.5% / +1.05% at C6 / C7, magnitude.log:1-6) at order 8's 5.1x cancellation; round 2 had 1,200
C8c, C8lo, C8hi = 1500, 1050, 1900
ALPHA_C, ALPHA_BAND = 0.534, (0.514, 0.554)
def row(ses, kind):
    """central at alpha 0.534; band = min/max over (low|high scenario) x alpha in [0.514, 0.554]; also alpha=1/2 central"""
    pc = plan(ses[0], 0, ALPHA_C); b, bind = pc[0], pc[1]
    lo = min(alloc(plan(ses[1], 1, a), REAL_C) for a in ALPHA_BAND); hi = max(alloc(plan(ses[2], 2, a), REAL_HI) for a in ALPHA_BAND)
    return dict(busy=b, bind=bind, floor_share=pc[3] / b, alloc=alloc(pc, REAL_C), alloc_half=alloc(plan(ses[0], 0, 0.5), REAL_C), lo=lo, hi=hi,
                stress=alloc(plan(ses[0], 3, ALPHA_C), REAL_C), alloc_flat110=b * 1.10 * ALLOC_BUSY)
out = []
print(f'run1 footprint: {day_run1:.0f} allocated core-h/day;  "d=2 growth" stress: L8 metric growth x{L8_STRESS:.2f} (costmodel, |C8| = 1,500)')
print(f'realism on the non-floor busy cost: central x{REAL_C:.3f}, high band x{REAL_HI:.3f}; floor-bound busy cost x1 (realism.py)')
print('target          SE    busy(alpha .534)  floor-binding  ALLOCATED central [band]           alpha=1/2   d=2-growth stress   wall d central   (floor share of busy; old flat x1.10)')
for kind, x in [('abs', v) for v in (10, 5, 3, 2, 1.5, 1.0, 0.75, 0.5, 0.3, 0.22)] + [('rel', v) for v in (1e-2, 3e-3, 1e-3, 5e-4, 2.5e-4, 1.44e-4)]:
    ses = (x, x, x) if kind == 'abs' else (x * C8c, x * C8hi, x * C8lo)
    r = row(ses, kind); tag = f'SE {x}' if kind == 'abs' else f'rel {x:g}'
    print(f'{tag:12s} {ses[0]:7.3g}  {r["busy"]:11.4g}   {r["bind"]*100:6.1f}%      {r["alloc"]:9.3g} [{r["lo"]:.3g}, {r["hi"]:.3g}]   {r["alloc_half"]:9.3g}   {r["stress"]:9.3g}       {r["alloc"]/day_run1:6.2f}      ({100*r["floor_share"]:.0f}%; {r["alloc_flat110"]:.3g})')
    out.append(dict(kind=kind, x=x, SE=ses[0], **{k: float(v) for k, v in r.items()}, days=r['alloc'] / day_run1))
json.dump(out, open('final_table.json', 'w'), indent=1)
for i, nm in enumerate(('central', 'low', 'high')):
    tot = sum((R * FLOOR * POPS[(t, i)][1]).sum() for t in CAMP)
    print(f'floor-only run (every graph 4096 pts/replicate, R=64, a+b) {nm}: {tot/3600:.3g} busy core-h')
for i, nm in enumerate(('central', 'low', 'high')):
    v = 0
    for s in SECT:
        for L in LOOPS:
            v += sum(PG[f'{t}|{s}|{L}']['se8old'] ** 2 / 4 for t in CAMP) * FL[(s, L)][i]
    print(f'C8 SE from loops 3-7 incl. new top slots at run1 sample sizes ({nm}): {v**.5:.3f}')
