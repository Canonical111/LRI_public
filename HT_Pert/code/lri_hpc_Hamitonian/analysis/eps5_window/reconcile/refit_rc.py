"""Reconciler C5 refit with the reconciled correction table (dC_reconciled.json), campaign data L=2..118.
Correction sets:
  raw         : campaign data
  g2D_MS      : C4 + fast(L) - z/17496 ; C5 + dC5_g2D - b5 z                  (eh-review package convention)
  g2D3W_MS    : g2D_MS + bubble on C5 with its log removed (-2fast + 2z/17496)
  Dconn_MS    : C4 + fast - z/17496 + shift4 ; C5 + dC5_Dconn - (b5 - 2/17496) z
  Dconn_full  : C4 + fast + shift4 ; C5 + dC5_Dconn                          (all logs kept)
  Dconn_C5only: C4 raw, C5 + dC5_Dconn (INCONSISTENT; shows the e1/lim4 coupling effect)
Fits: diagnose_systematic.thermal_fit (checked vs ThermalModel), maxorder 5, hi = 118, lo in 16,40,50,60,70.
Read-only import of the campaign code."""
import sys, json, math
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load, ThermalModel
from diagnose_systematic import thermal_fit, const_terms
R = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
B5 = 5.5388e-4; a = 1 / 17496
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
assert all(int(l) in T for l in L), 'missing cutoff in correction table'
ex = json.load(open(EXT + '/extended_summary.json'))
w_ext = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
w_orig = {int(k): v for k, v in ex['gap_reference']['original'].items()}
col = lambda k: np.array([T[int(l)][k] for l in L])
z = np.log(L)
fastL = col('dC4_g2D'); sh4 = col('shift4'); g5 = col('dC5_g2D'); dC5 = col('dC5_Dconn')
def mk(d4, d5):
    X = C.copy(); X[:, 4] += d4; X[:, 5] += d5; return X
data = {'raw': C.copy(),
        'g2D_MS': mk(fastL - a * z, g5 - B5 * z),
        'g2D3W_MS': mk(fastL - a * z, g5 - B5 * z - 2 * fastL + 2 * a * z),
        'Dconn_MS': mk(fastL - a * z + sh4, dC5 - (B5 - 2 * a) * z),
        'Dconn_full': mk(fastL + sh4, dC5),
        'Dconn_C5only': mk(0 * z, dC5)}
pre = ['A', 'B', 'C', 'D', 'E', 'F']
variants = {name: ('pre', const_terms(name), w_ext, False) for name in pre}
for name in ('A', 'B', 'D'):
    variants[f'{name}+free_exp'] = ('post', const_terms(name), w_ext, True)
    variants[f'{name} gap=orig'] = ('post', const_terms(name), w_orig, False)
for name in ('A', 'D'):
    variants[f'{name}+z^j/L'] = ('post', lambda k, n=name: MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+z^j/L^1.5'] = ('post', lambda k, n=name: MODELS[n] + [(1.5, j) for j in range(2, k - 1) if (1.5, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+L^-0.75'] = ('post', lambda k, n=name: MODELS[n] + [(0.75, 0)], w_ext, False)
variants['E+L^-0.5'] = ('extra', lambda k: MODELS['E'] + [(0.5, 0)], w_ext, False)
variants['E+L^-0.5,zL^-0.5'] = ('extra', lambda k: MODELS['E'] + [(0.5, 0), (0.5, 1)], w_ext, False)
# sanity: thermal_fit == ThermalModel on corrected data
for name in ('A', 'E'):
    m = L >= 40
    t1 = ThermalModel(MODELS[name], w_ext).fit(L[m], data['Dconn_full'][m], maxorder=5).lim
    t2, _ = thermal_fit(L[m], data['Dconn_full'][m], w_ext, const_terms(name), maxorder=5)
    assert abs(t1[5] - t2[5]) < 1e-7 * abs(t1[5]), (t1, t2)
rows = []
for lo in (16, 40, 50, 60, 70):
    mm = (L >= lo) & (L <= 118)
    for lab, (cls, tk, w, free) in variants.items():
        r = dict(lo=lo, variant=lab, cls=cls)
        for key, CC in data.items():
            try:
                lim, diag = thermal_fit(L[mm], CC[mm], w, tk, free_exponents=free, maxorder=5)
            except ValueError as e:
                r[key] = None; continue
            r[key] = dict(C4=lim[4], C5=lim[5], res4=diag[4]['max_residual'], res5=diag[5]['max_residual'],
                          cond5=diag[5]['condition'], gain5=diag[5]['intercept_gain_l1'])
        rows.append(r)
json.dump(dict(B5=B5, rows=rows), open(R + '/refit_rc.json', 'w'), indent=1)
keys = list(data)
print('C5 per variant: ' + ' '.join(f'{k:>12s}' for k in keys) + ' | miss(Dconn_MS) miss(Dconn_full) | C4 Dconn_MS / full | res5 raw / Dconn')
for r in rows:
    if r['raw'] is None: continue
    print(f"{r['lo']:3d} {r['variant']:17s} " + ' '.join(f"{r[k]['C5']:12.4f}" for k in keys) +
          f" | {r['Dconn_MS']['C5'] - EX5:+.4f} {r['Dconn_full']['C5'] - EX5:+.4f} | {r['Dconn_MS']['C4']:.5f} {r['Dconn_full']['C4']:.5f} | {r['raw']['res5']:.1e} {r['Dconn_full']['res5']:.1e}")
print()
for lo in (16, 40, 50, 60, 70):
    sel = [r for r in rows if r['lo'] == lo and r['raw'] is not None]
    for cls in ('pre', 'post', 'extra'):
        s = [r for r in sel if r['cls'] == cls]
        out = []
        for k in ('raw', 'g2D_MS', 'g2D3W_MS', 'Dconn_MS', 'Dconn_full', 'Dconn_C5only'):
            v = [r[k]['C5'] for r in s]
            out.append(f"{k} {min(v) - EX5:+.3f}..{max(v) - EX5:+.3f} (spread {max(v) - min(v):.3f})")
        print(f'lo={lo} {cls:5s} miss ' + ' | '.join(out))
    sh = [r['Dconn_full']['C5'] - r['raw']['C5'] for r in sel]
    shm = [r['Dconn_MS']['C5'] - r['raw']['C5'] for r in sel]
    sh1 = [r['Dconn_C5only']['C5'] - r['raw']['C5'] for r in sel]
    c4 = [r['Dconn_full']['C4'] for r in sel if r['cls'] == 'pre']; c4m = [r['Dconn_MS']['C4'] for r in sel if r['cls'] == 'pre']
    fl = [r for r in sel if r['Dconn_full']['res5'] < 1e-10]
    print(f'   shift full-raw {min(sh):.4f}..{max(sh):.4f}; MS-raw {min(shm):.4f}..{max(shm):.4f}; C5only-raw {min(sh1):.4f}..{max(sh1):.4f}; C4 pre full {min(c4):.5f}..{max(c4):.5f} MS {min(c4m):.5f}..{max(c4m):.5f}')
    if fl:
        print(f"   noise-floor (res5<1e-10) n={len(fl)}: Dconn_full miss {min(r['Dconn_full']['C5'] for r in fl) - EX5:+.3f}..{max(r['Dconn_full']['C5'] for r in fl) - EX5:+.3f} [" + ', '.join(r['variant'] for r in fl) + ']')
