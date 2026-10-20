#!/usr/bin/env python3
"""Replay of the d = 1 blind-solver check (HT note, Section "Independent checks"; macro HTnpDoneIndep).

Run from HT/code/lri_dressed_phi4_independent_check (or `make -f public.mk replay`); about 10 s, one core, numpy only.

  1. Rebuild results/indep_results.json from the shipped per-task outputs (results/raw_runs/) with the shipped
     analyze.py, run unchanged in a work copy, and compare (exact, except 'host', which may carry a placeholder).
  2. Rebuild the production reference of the 38 compared points from the shipped production records
     (HT/data/HT_1d: prod1-7 for raw/consistent/literal at every nz, dens16 of dens_v1 for consistent) and compare it
     with the reference the comparison was made against (../lri_dressed_phi4_hpc_analysis/indepcheck/
     production_reference.json; exact).
  3. Recompute the agreement: max |Delta_eps(blind) - Delta_eps(production)| against the largest-nz production record,
     split into points where production used nz 48 (or Ds >= 0.2) and points where it used nz 24/32 at strong
     coupling; quoted bound 5e-9 (1 significant figure of the larger) and the note's 1.3e-9 / 4.8e-9.
  4. C2(N): max |C2 fit - exact rational C2(N)| over N = 0..16, raw and consistent (fixed 1/2 - eps/6, order 6,
     eps <= 0.008): the note's <= 3e-7.
Writes <work>/replay_indep.txt (PASS/FAIL) and exits 1 on any FAIL.
"""
import argparse, json, math, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; PKG = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument('--data', default=str(PKG / '../../data/HT_1d'))
ap.add_argument('--reference', default=str(PKG / '../lri_dressed_phi4_hpc_analysis/indepcheck/production_reference.json'))
ap.add_argument('--work', default=str(PKG / '.work'))
a = ap.parse_args()
DATA, REF, WORK = Path(a.data).resolve(), Path(a.reference).resolve(), Path(a.work).resolve()
WORK.mkdir(parents=True, exist_ok=True)
ROWS = []
def row(i, what, quoted, computed, ok): ROWS.append((i, what, str(quoted), str(computed), 'PASS' if ok else 'FAIL'))
def sig1(x): return round(x, -int(math.floor(math.log10(abs(x)))))

# 1. rebuild indep_results.json
W = WORK / 'pkg'
if W.exists(): shutil.rmtree(W)
W.mkdir(parents=True)
shutil.copy2(PKG / 'analyze.py', W / 'analyze.py')
shutil.copytree(PKG / 'results/raw_runs', W / 'results/raw_runs')
shutil.copytree(PKG / 'results/retune_check', W / 'results/retune_check')
pr = subprocess.run([sys.executable, 'analyze.py', 'results/raw_runs'], cwd=W, capture_output=True, text=True,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1'))
(WORK / 'analyze.out').write_text(pr.stdout + pr.stderr)
# Everything except the C2 least-squares fits must be identical (NaN equal to NaN; 'host' ignored, it may carry a
# placeholder). The C2 fits (numpy lstsq) depend on the numpy/LAPACK build: measured on symmetry vs the analysis machine,
# C2 agrees to 1e-10 relative, the C3 of the exactly determined 4-point fits to 1e-8 relative, and the high-order
# coefficients and rms to 1e-4 relative. Tolerances: C2, c0, c1, C2_minus_exact to 1e-10 absolute; C3 and coefs to
# 1e-3 relative (or 1e-6 absolute); rms to 1e-2 relative (or 1e-16).
def cmp(x, y, path, bad):
    if isinstance(x, dict):
        if set(x) - {'host'} != set(y) - {'host'}: bad.append(path + ' keys'); return
        for k in x:
            if k != 'host': cmp(x[k], y[k], path + '/' + k, bad)
    elif isinstance(x, list):
        if len(x) != len(y): bad.append(path + ' len'); return
        for u, v in zip(x, y): cmp(u, v, path, bad)
    elif isinstance(x, float) and isinstance(y, float):
        if math.isnan(x) and math.isnan(y): return
        if path.startswith('/C2_fits'):
            k = path.rsplit('/', 1)[-1]
            if k in ('C2', 'c0', 'c1', 'C2_minus_exact'): ok = abs(x - y) <= 1e-10
            elif k in ('coefs', 'C3'): ok = abs(x - y) <= max(1e-3 * abs(y), 1e-6)
            elif k == 'rms': ok = abs(x - y) <= max(1e-2 * abs(y), 1e-16)
            else: ok = x == y
        else: ok = x == y
        if not ok: bad.append(f'{path}: {x!r} vs {y!r}')
    elif x != y: bad.append(f'{path}: {x!r} vs {y!r}')
new = json.loads((W / 'results/indep_results.json').read_text()); old = json.loads((PKG / 'results/indep_results.json').read_text())
bad = []; cmp(new, old, '', bad)
(WORK / 'indep_rebuild_diffs.txt').write_text('\n'.join(bad) + '\n')
row('B1', 'analyze.py rebuilds results/indep_results.json from results/raw_runs (exact; C2 lstsq fits within tolerance)', 'equal',
    f"rc {pr.returncode}, {len(bad)} differences", pr.returncode == 0 and not bad)
row('B2', 'points computed / failed', '38 / 0', f"{len(old['points'])} / {len(old['failed'])}", len(old['points']) == 38 and not old['failed'])

# 2. production reference from the records
recs = []
for f in sorted((DATA / 'prod_window/campaigns').glob('prod*/results/*.json')):
    d = json.loads(f.read_text()); c, p = d['config'], d['payload']
    recs.append(dict(delta=p['delta'], N=p['bath_cut'], window=c.get('window', 'none'), mode=c.get('window_mode') if c.get('window') == 'vacuum' else None,
                     nz=p['nz_per_parity'], osc=c['osc'], D=p['Delta_thermal'], g=p['g'], r=p['r'], even=p['even_gaps'], odd=p['odd_gaps'],
                     campaign=f.parts[-3]))
dens = {}
for f in sorted((DATA / 'dens_v1/campaigns').glob('dens16_*/results/*.json')):
    p = json.loads(f.read_text())['payload']
    dens[(p['delta'], p['bath_cut'])] = dict(D=p['Delta_thermal'], even=p['even_gaps'], odd=p['odd_gaps'], theta=p['theta'])
ref = json.loads(REF.read_text())
same = True
for x in ref:
    pp = sorted([{k: v for k, v in r.items() if k not in ('delta', 'N', 'window', 'mode')} for r in recs
                 if r['delta'] == x['delta'] and r['N'] == x['N'] and r['window'] == x['window'] and r['mode'] == x['mode']],
                key=lambda r: (-r['nz'], -r['osc']))
    same &= pp == sorted(x['prod'], key=lambda r: (-r['nz'], -r['osc']))
    if 'dens16' in x: same &= [dens.get((x['delta'], x['N']))] == x['dens16']
row('B3', 'production reference of the 38 points rebuilt from the shipped records (prod1-7, dens16)', 'equal', 'equal' if same else 'DIFFERENT', same)

# 3. agreement
pts = {(p['delta'], p['N'], p['prescription']): p for p in old['points']}
key = lambda x: (x['delta'], x['N'], 'raw' if x['window'] == 'none' else x['mode'])
hi, lo, dmax16 = [], [], 0.
for x in ref:
    p = pts[key(x)]; best = max(x['prod'], key=lambda r: (r['nz'], r['osc']))
    d = abs(p['Delta_eps'] - best['D'])
    (hi if (best['nz'] >= 48 or x['delta'] >= 0.2) else lo).append(d)
    if x.get('dens16'): dmax16 = max(dmax16, abs(p['Delta_eps'] - x['dens16'][0]['D']))
row('B4', 'max |blind - production|, nz 48 or Ds >= 0.2 (note: 1.3e-9)', '1.3e-9', f'{max(hi):.3g} ({len(hi)} points)', round(max(hi), 10) <= 1.3e-9)
row('B5', 'max |blind - production|, nz 24/32 at strong coupling (note: 4.8e-9)', '4.8e-9', f'{max(lo):.3g} ({len(lo)} points)', round(max(lo), 10) <= 4.8e-9)
row('B6', 'HTnpDoneIndep: max over all 38 points, 1 significant figure', '5e-9', f'{sig1(max(hi + lo)):.0e}', sig1(max(hi + lo)) == 5e-9)
row('B7', 'max |blind - dens16| (consistent, N <= 20): span error of the density basis, <= HTnpBasisErr', '1e-6', f'{dmax16:.3g}', dmax16 <= 1e-6)

# 4. C2(N)
c2 = [abs(r['small_eps_fixed_o6']['C2_minus_exact']) for r in old['C2_fits']]
Ns = sorted({r['N'] for r in old['C2_fits']})
row('B8', 'C2(N) fit - exact, N = 0..16, raw and consistent (order-6 fixed fit): max', '3e-7', f'{max(c2):.3g} (N = {Ns})', max(c2) <= 3e-7)

# 5. the window enters only at O(eps^4): exponent of |Delta(consistent) - Delta(raw)| in eps, 0.008 <= eps <= 0.04
import numpy as np
wk = {}
for x in old['weak_coupling_points']:
    wk.setdefault((x['N'], round(x['delta'], 10)), {})[x['prescription']] = x['Delta_eps']
expo = []
for N in sorted({k[0] for k in wk if k[0] > 0}):
    pts = [(1 - 4 * d, abs(v['consistent'] - v['raw'])) for (n, d), v in wk.items() if n == N and 'raw' in v and 'consistent' in v
           and 0.0079 <= 1 - 4 * d <= 0.0401 and abs(v['consistent'] - v['raw']) > 0]
    if len(pts) >= 3:
        e, y = map(np.array, zip(*sorted(pts))); expo.append((N, float(np.polyfit(np.log(e), np.log(y), 1)[0])))
row('B9', 'window changes Delta_eps only at O(eps^4): fitted exponent of |consistent - raw|, eps = 0.008..0.04, each N', '3.8-4.3',
    ', '.join(f'N={n}: {v:.2f}' for n, v in expo), bool(expo) and all(3.8 <= v <= 4.3 for n, v in expo))

w = max(len(r[1]) for r in ROWS)
lines = [f"{'id':4} {'verdict':7} {'check':{w}}  quoted | computed"] + [f'{i:4} {v:7} {t:{w}}  {q} | {c}' for i, t, q, c, v in ROWS]
nf = sum(r[4] == 'FAIL' for r in ROWS); lines.append(f'\n{len(ROWS) - nf} PASS, {nf} FAIL')
(WORK / 'replay_indep.txt').write_text('\n'.join(lines) + '\n'); print('\n'.join(lines))
sys.exit(1 if nf else 0)
