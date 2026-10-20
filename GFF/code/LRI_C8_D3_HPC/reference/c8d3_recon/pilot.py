# Pilot sizing (RECON section 6.3.6; repair round 1: the full L8 pass is the default design, finding 4).
# Busy core-h, both campaigns, from the per-graph L8 costs of l8cost.py (central, calibrated to L7; band = the kappa
# band of costmodel.py) and the run1 per-graph busy core-s per point for L<=7 (L7 at 2,441 + 709 kernels: the 262
# s_G=4 kernels are costed at their group's mean).
import json, numpy as np
LC = json.load(open('l8cost_out.json')); PG = json.load(open('pergraph_out.json')); CM = json.load(open('costmodel_out.json'))
KAP = {tuple(k.split('|')): v for k, v in CM['KAP'].items()}; KAPM = {tuple(k.split('|')): v for k, v in CM['KAPmodel'].items()}
# repair round 2: the per-graph L8 costs follow the backtest-corrected kappa central (costmodel.py); band = kappa band
N7new = {'free': 2441, 'power': 709}
def l8(frac, R, pts, i, heavy=0.0):
    """frac of the L8 kernels (uniform), plus the heaviest `heavy` fraction by cost taken with certainty"""
    tot = 0
    for s in ('free', 'power'):
        for t in 'ab':
            c = np.array(LC['pop'][f'{s}|{t}']['c8']) * KAP[(s, t)][i] / KAPM[(s, t)]
            cs = np.sort(c)[::-1]; nh = int(round(heavy * len(c)))
            tot += R * pts * (cs[:nh].sum() + frac * cs[nh:].sum())
    return tot / 3600
def low(R, pts):
    tot = 0
    for s in ('free', 'power'):
        for L in range(3, 8):
            for t in 'ab':
                per = PG[f'{t}|{s}|{L}']['per']; c = np.array([p['cpp'] for p in per])
                tot += R * pts * (c.sum() + (N7new[s] - len(per)) * c.mean() if L == 7 else c.sum())
    return tot / 3600
rows = [('P1a  L8 stage A: 1/8 stratified + heaviest 1% with certainty, R=8, 4096', lambda i: l8(1 / 8, 8, 4096, i, heavy=0.01)),
        ('P1a+P2  L8 all 20,400 kernels, R=8, 4096 (default)', lambda i: l8(1, 8, 4096, i)),
        ('P1c  1/256 nested subset, R=8, 32768', lambda i: l8(1 / 256, 8, 32768, i)),
        ('P1b  L3-L7 all kernels, R=8, 4096', lambda i: low(8, 4096))]
res = {}
for nm, f in rows:
    v = [f(i) for i in range(3)]; res[nm] = v
    print(f'{nm:72s}: central {v[0]:7.1f}  band [{v[1]:.1f}, {v[2]:.1f}] busy core-h (both campaigns)')
tot = [res[rows[1][0]][i] + res[rows[2][0]][i] + res[rows[3][0]][i] for i in range(3)]
print(f'{"DEFAULT PILOT = full L8 pass + P1b + P1c":72s}: central {tot[0]:7.1f}  band [{tot[1]:.1f}, {tot[2]:.1f}] busy core-h')
print(f'{"  stage A alone (go/no-go, histograms) = P1a + P1b + P1c":72s}: central {res[rows[0][0]][0]+res[rows[2][0]][0]+res[rows[3][0]][0]:7.1f} busy core-h')
print(f'{"  R=16 instead of R=8 for the full L8 pass (halves the sigma-noise penalty, see checks [9])":72s}: +{res[rows[1][0]][0]:.0f} busy core-h')
print(f'{"  model-uncorrected kappa (repair round 1 basis), full L8 pass":72s}: {res[rows[1][0]][0]*np.mean([KAPM[k]/KAP[k][0] for k in KAP]):.0f} busy core-h (approx.)')
# ---- repair round 3 (verifier findings 9 and 14): every pre-registered branch of the pilot, costed. Busy core-h, both campaigns.
import csv
RL = json.load(open('realism_out.json')); FT = json.load(open('final_table.json'))
ARRAY = 2.5   # allocated/busy ALLOWANCE for array mode (round 1's "400 busy, at most about 1k allocated"); not a measurement
L8rows = {s: [r for r in csv.DictReader(open('sizes_L8.csv')) if r['status'] == s and r['sG'] != '4'] for s in ('free', 'power')}
def pass_cost(i):
    """per-graph busy core-h of the 4096-point R=8 L8 pass, both campaigns (scenario i), per sector"""
    return {s: sum(8 * 4096 * np.array(LC['pop'][f'{s}|{t}']['c8']) * KAP[(s, t)][i] / KAPM[(s, t)] for t in 'ab') / 3600 for s in ('free', 'power')}
PC = [pass_cost(i) for i in range(3)]; full = [sum(v.sum() for v in p.values()) for p in PC]
print(f'[R1] L8 pass by sector (central): free {PC[0]["free"].sum():.1f}, power {PC[0]["power"].sum():.1f} busy core-h; per-graph mean {full[0]/20400*3600:.1f} core-s, '
      f'median {np.median(np.concatenate(list(PC[0].values())))*3600:.1f} core-s, max {max(v.max() for v in PC[0].values())*3600:.0f} core-s')
# strata of RECON section 6.3.6: sector x T bins (0-8, 8-24, 24-48, 48-96, >96) x M tertiles within the sector
sh = {}
for s in ('free', 'power'):
    T = np.array([int(r['T']) for r in L8rows[s]]); M = np.array([int(r['M']) for r in L8rows[s]])
    st = np.digitize(T, [8, 24, 48, 96]) * 3 + np.digitize(M, np.quantile(M, [1 / 3, 2 / 3]))
    for k in sorted(set(st)): sh[(s, int(k))] = (PC[0][s][st == k].sum() / full[0], int((st == k).sum()))
v = np.array([x[0] for x in sh.values()])
top = sorted(sh.items(), key=lambda kv: -kv[1][0])[:3]
print(f'[R2] {len(sh)} strata: median share of the L8 pass {100*np.median(v):.1f}%, so re-running a median stratum at 32,768 points costs {800*np.median(v):.0f}% of the pass; '
      'largest: ' + ', '.join(f'{s} T-bin {k//3} M-tertile {k%3} {100*x:.1f}% ({n} graphs; re-run {800*x:.0f}% = {8*x*full[0]:.0f} busy)' for (s, k), (x, n) in top))
CAP = 0.25   # re-runs capped at 25% of the L8 pass (repair round 3)
print(f'[R3] graph re-runs at 32,768 points (x8 per graph) capped at {100*CAP:.0f}% of the L8 pass: {CAP*full[0]:.0f} busy core-h ({CAP*full[1]:.0f}-{CAP*full[2]:.0f}); '
      f'the cap holds every flagged graph while the flagged graphs carry <= {100*CAP/8:.1f}% of the pass cost (about {CAP/8*20400:.0f} graphs of mean cost)')
r16 = full; r16s = {s: [PC[i][s].sum() for i in range(3)] for s in ('free', 'power')}
print(f'[R4] R = 16 for the L8 pass: +{r16[0]:.0f} ({r16[1]:.0f}-{r16[2]:.0f}) busy core-h in all; per sector free +{r16s["free"][0]:.0f}, power +{r16s["power"][0]:.0f}')
base = [res[rows[1][0]][i] + res[rows[2][0]][i] + res[rows[3][0]][i] for i in range(3)]
cont = [r16[i] + CAP * full[i] for i in range(3)]
print(f'[R5] budget: default pilot {base[0]:.0f} ({base[1]:.0f}-{base[2]:.0f}) + contingency for every pre-registered branch (R = 16 for both sectors + capped re-runs) '
      f'{cont[0]:.0f} ({cont[1]:.0f}-{cont[2]:.0f}) = at most {base[0]+cont[0]:.0f} busy core-h ({base[1]+cont[1]:.0f}-{base[2]+cont[2]:.0f}); '
      f'allocated at the x{ARRAY} array-mode allowance: {ARRAY*base[0]:.0f} default, at most {ARRAY*(base[0]+cont[0]):.0f} ({ARRAY*(base[2]+cont[2]):.0f} at the band top)')
print(f'     allowance brackets: run1 lane mode x{10516/9681.8:.3f}; C7(3) M=1 pilot 1,181 task core-s in 4.7 min of one 64-core node = x{4.7*60*64/1181:.1f} (CAMPAIGN.md:31-33, '
      'overhead-bound); C8(1) L8 end-to-end QMC efficiency 0.12-0.14 (x7-8). Stage A measures it before the full pass')
# R = 16 break-even (finding 14): extra pilot cost (allocated, at the allowance) against the production saving on the non-floor busy cost
ab = 10516 / 9681.8
def pen(Rp, kex): return RL[f'noise|kex{kex}|R{Rp}']
for nm, r8, r16_ in (('Gaussian replicates (measured R=8 / R=16)', RL['noise|R8|median'], RL['noise|R16|median']), ('excess kurtosis 2 (Gamma model, high band)', pen(8, 2), pen(16, 2))):
    extra = ARRAY * r16[0]; rows_abs = [r for r in FT if r['kind'] == 'abs']
    sav = [(r['SE'], r['busy'] * (1 - r['floor_share']) * (r8 - r16_) * RL['pow2|exact'] * RL['samedata|R64'] * ab, r['alloc']) for r in rows_abs]
    be = None
    for (s1, v1, a1), (s2, v2, a2) in zip(sav, sav[1:]):
        if (v1 - extra) * (v2 - extra) <= 0: f = np.log(extra / v1) / np.log(v2 / v1); be = (s1 * (s2 / s1) ** f, a1 * (a2 / a1) ** f); break
    print(f'[R6] R = 16 break-even, {nm}: realism x{r8*RL["pow2|exact"]*RL["samedata|R64"]:.3f} -> x{r16_*RL["pow2|exact"]*RL["samedata|R64"]:.3f}; extra pilot {r16[0]:.0f} busy = {extra:.0f} allocated; '
          + (f'pays back at SE <= {be[0]:.2f} (production >= {be[1]:.3g} allocated core-h)' if be else 'no crossing in the table')
          + '; saving at SE 0.5: ' + f'{[x for x in sav if x[0] == 0.5][0][1]:.3g} allocated')
