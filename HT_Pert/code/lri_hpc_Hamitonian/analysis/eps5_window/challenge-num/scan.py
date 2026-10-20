"""POST HOC scan: floor-level tail bases; joint behaviour of corrected C4 and C5 (exact values only compared)."""
import sys, itertools; sys.dont_write_bytecode=True
import numpy as np, json
from myfit import *
L, C = rows()
T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
w = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
col = lambda key: np.array([T[int(l)][key] for l in L])
Cf = C.copy(); Cf[:, 4] += col('dC4_Dconn'); Cf[:, 5] += col('dC5_Dconn')
rng = np.random.default_rng(7)
noise = [rng.normal(0, 1, (len(L), 2)) for _ in range(40)]
EXTRA = [(0.5, 0), (0.5, 1), (1, 2), (1, 3), (1.5, 2), (2, 2), (2.5, 0), (0.75, 0), (2.5, 1)]
res = []
for base in 'ABCDEF':
    for n in (0, 1, 2):
        for ex in itertools.combinations(EXTRA, n):
            tb = BASES[base] + [t for t in ex if t not in BASES[base]]
            if len(tb) != len(BASES[base]) + n: continue
            for lo in (30, 40, 50, 60):
                m = L >= lo
                if m.sum() < len(tb) + 6: continue
                lim, info = fit(L[m], Cf[m], tb, tb, w)
                res.append(dict(base=base, ex=ex, lo=lo, c4=lim[4] - EX4, c5=lim[5] - EX5, r4=info[4][0], r5=info[5][0], g5=info[5][1]))
json.dump(res, open('scan.json', 'w'), default=str)
fl = [r for r in res if r['r5'] < 6e-11 and r['r4'] < 6e-12 and r['g5'] < 2e9]
print('floor-level fits (res5<6e-11, res4<6e-12, gain5<2e9):', len(fl), 'of', len(res))
c4 = np.array([r['c4'] for r in fl]); c5 = np.array([r['c5'] for r in fl])
print('C4 miss range %.4f..%.4f ; C5 miss range %.3f..%.3f ; corr(C4miss,C5miss)=%.2f' % (c4.min(), c4.max(), c5.min(), c5.max(), np.corrcoef(c4, c5)[0, 1]))
# linear relation C5miss vs C4miss
p = np.polyfit(c4, c5, 1); print('C5miss ~ %.1f * C4miss + %.3f' % (p[0], p[1]))
for lo in (30, 40, 50, 60):
    s = [r for r in fl if r['lo'] == lo]
    if not s: continue
    a4 = np.array([r['c4'] for r in s]); a5 = np.array([r['c5'] for r in s])
    print(f'lo={lo}: n={len(s)} C4 miss {a4.min():+.4f}..{a4.max():+.4f} median {np.median(a4):+.4f}; C5 miss {a5.min():+.3f}..{a5.max():+.3f} median {np.median(a5):+.3f}; |C4miss|<0.002: C5 ' +
          (f'{a5[abs(a4)<0.002].min():+.3f}..{a5[abs(a4)<0.002].max():+.3f} (n={int((abs(a4)<0.002).sum())})' if (abs(a4) < 0.002).any() else 'none'))
print()
for r in sorted(fl, key=lambda r: (r['lo'], r['c5']))[:400]:
    if r['lo'] in (40, 50):
        print(f"lo={r['lo']} {r['base']}+{r['ex']}: C4 {r['c4']:+.4f} C5 {r['c5']:+.3f} res4 {r['r4']:.1e} res5 {r['r5']:.1e} gain {r['g5']:.1e}")
