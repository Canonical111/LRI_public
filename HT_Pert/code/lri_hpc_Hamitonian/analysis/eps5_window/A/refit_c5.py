"""Re-extrapolate C4 and C5 of the campaign thermal data with consistently corrected data.
Corrections (finite-L tables from dC_table.json, L=8..118):
  raw      : campaign data
  g2D_MS   : C4 + dC4_g2D - log L/17496 ; C5 + dC5_g2D - b5 log L        (package convention of the eh review)
  g2D3W_MS : as g2D_MS plus the eps^3 bubble (dC5 += -2 dC4_g2D, its log -2/17496 removed)
  Dconn_full: C4 + dC4_Dconn ; C5 + dC5_Dconn  (complete Dconn, logs kept: consistent if raw carries -logs)
  Dconn_MS : Dconn_full minus log L/17496 in C4 and minus bD log L in C5 (bD = b5 - 2/17496)
  Dfull_full: literal E_vac difference (double counting), for comparison
Tail variants: the 18 of explore_lower_edge.py (12 distinct at C4), lo in {40,50,60,70}, hi=118.
The y5 target uses the corrected C4(L) and the corrected lim4 of the same fit (ThermalModel order by order).
Read-only use of the campaign analysis code."""
import sys, json, math
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load
from diagnose_systematic import thermal_fit, const_terms

EX4, EX5 = 45.42488010356, -731.13947662454
B5 = float(sys.argv[1]) if len(sys.argv) > 1 else 5.539e-4      # log coefficient of dC5_g2D (eh review fit)
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
ex = json.load(open(EXT + '/extended_summary.json'))
w_ext = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
w_orig = {int(k): v for k, v in ex['gap_reference']['original'].items()}
T = json.load(open('dC_table.json'))['table']
keep = np.array([str(int(l)) in T for l in L])
L = L[keep]; C = C[keep]
g = lambda pres, q: np.array([T[str(int(l))][pres][q] for l in L])
lg = np.log(L); a = 1 / 17496
bD = B5 - 2 * a
data = {'raw': C.copy()}
def mk(d4, d5):
    X = C.copy(); X[:, 4] += d4; X[:, 5] += d5; return X
data['g2D_MS'] = mk(g('g2D', 'dC4') - a * lg, g('g2D', 'dC5') - B5 * lg)
data['g2D3W_MS'] = mk(g('g2D', 'dC4') - a * lg, g('g2D3W', 'dC5') - bD * lg)
data['Dconn_full'] = mk(g('Dconn', 'dC4'), g('Dconn', 'dC5'))
data['Dconn_MS'] = mk(g('Dconn', 'dC4') - a * lg, g('Dconn', 'dC5') - bD * lg)
data['Dfull_full'] = mk(g('Dfull', 'dC4'), g('Dfull', 'dC5'))
variants = {name: (const_terms(name), w_ext, False) for name in MODELS if name != 'minimal'}
for name in ('A', 'B', 'D'):
    variants[f'{name}+free_exp'] = (const_terms(name), w_ext, True)
    variants[f'{name} gap=orig'] = (const_terms(name), w_orig, False)
for name in ('A', 'D'):
    variants[f'{name}+z^j/L'] = (lambda k, n=name: MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+z^j/L^1.5'] = (lambda k, n=name: MODELS[n] + [(1.5, j) for j in range(2, k - 1) if (1.5, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+L^-0.75'] = (lambda k, n=name: MODELS[n] + [(0.75, 0)], w_ext, False)
rows = []
for lo in (40, 50, 60, 70):
    mm = L >= lo
    for lab, (tk, w, free) in variants.items():
        r = dict(lo=lo, variant=lab)
        for key, CC in data.items():
            lim, diag = thermal_fit(L[mm], CC[mm], w, tk, free_exponents=free, maxorder=5)
            r[key] = (lim[4], lim[5], diag[4]['max_residual'], diag[5]['max_residual'])
        rows.append(r)
json.dump(dict(B5=B5, rows=rows), open('refit_c5.json', 'w'), indent=1)
keys = list(data)
print('C5 (and C5 - exact) per variant; columns:', keys)
for r in rows:
    if r['lo'] in (40, 60, 70):
        print(f"{r['lo']:3d} {r['variant']:16s} " + ' '.join(f"{r[k][1]:9.3f}" for k in keys) + f" | Dconn_full-exact {r['Dconn_full'][1]-EX5:+.3f} | C4 Dconn_full {r['Dconn_full'][0]:.5f} res4 {r['Dconn_full'][2]:.0e} res5 {r['Dconn_full'][3]:.0e}")
pre = ['A', 'B', 'C', 'D', 'E', 'F']
for lo in (40, 50, 60, 70):
    sel = [r for r in rows if r['lo'] == lo]
    pr = [r for r in sel if r['variant'] in pre]
    def rng(rs, k, i):
        v = [x[k][i] for x in rs]; return min(v), max(v)
    print(f'lo={lo}: ' + ' | '.join(f"{k}: C5 {rng(pr,k,1)[0]:.3f}..{rng(pr,k,1)[1]:.3f} (all {rng(sel,k,1)[0]:.3f}..{rng(sel,k,1)[1]:.3f})" for k in keys))
    sh = [r['Dconn_full'][1] - r['raw'][1] for r in sel]
    sh2 = [r['Dconn_full'][1] - r['g2D3W_MS'][1] for r in sel]
    print(f'        intercept shift Dconn_full - raw: {min(sh):.4f}..{max(sh):.4f}; Dconn_full - g2D3W_MS: {min(sh2):.4f}..{max(sh2):.4f}')
