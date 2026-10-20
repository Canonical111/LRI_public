#!/usr/bin/env python3
"""CB3 GFF-only curves for Figure 06 (2026-10-13, author's request). Run from anywhere, local, a few seconds:
    python3 combined/make_cb3_gff_only.py
CB3 = the release's 'direct' conformal-Borel prescription truncated at order n=3, i.e. only C_0..C_3 (the published
three-loop order), with each panel's GFF-only CB8 prescription:
  2d: 2d/code/calculate.py cb('direct', 3, b=3.5, alpha=0), A = 9/8
  3d: 3d/code/calculate.py cb('direct', 3, b=4,   alpha=0), A = (9/4)[Gamma(9/4)/Gamma(3/4)]^2 = 1.92343...
evaluated on the x grid of the stored curves (2d/results/curves.csv, 3d/results/curves.csv). The release code and its
results are only read (modules imported without writing bytecode; their module-level OUT.mkdir(exist_ok=True) is a
no-op). It does not depend on C8. Checks: the same imported code reproduces the stored direct_CB8 columns; the
coordinator's check values; GL-240 vs adaptive quadrature at the check points.
Outputs: combined/cb3_gff_only.csv (d, Delta_sigma, CB3_direct) and combined/cb3_gff_only.json (code hashes,
parameters, checks).
"""
import csv, hashlib, importlib.util, json, math, sys
from pathlib import Path
import numpy as np
import mpmath as mp
from scipy.integrate import quad

sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parent.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CHECK = {2: {.13: .91398, .2: .92192, .3: .93659, .4: .95842, .49: .99378},
         3: {.52: 1.4111, .55: 1.41892, .6: 1.43356, .65: 1.45084, .7: 1.47204}}
B = {2: 3.5, 3: 4}
rows, meta = [], {'created': '2026-10-13', 'generator': 'combined/make_cb3_gff_only.py',
                  'definition': "release 'direct' CB truncated at n=3 (C_0..C_3 only), alpha=0, candidate action A of the dimension; "
                                'same prescription as the GFF-only CB8 of Figure 06', 'panels': {}}
for d in (2, 3):
    code = PKG/f'{d}d'/'code'/'calculate.py'
    tracked = [code, PKG/f'{d}d'/'inputs'/'protocol.json', PKG/f'{d}d'/'inputs'/'sri_summary.json', PKG/f'{d}d'/'results'/'curves.csv']
    before = {str(p.relative_to(PKG)): sha(p) for p in tracked}
    spec = importlib.util.spec_from_file_location(f'release_calculate_{d}d', code)
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    stored = list(csv.DictReader((PKG/f'{d}d'/'results'/'curves.csv').open()))
    x = np.array([float(r['Delta_sigma']) for r in stored])
    assert np.array_equal(x, np.asarray(M.X, dtype=float)), 'stored grid differs from the release grid'
    cb3 = M.cb('direct', 3, b=B[d], alpha=0, x=x)
    cb8 = M.cb('direct', 8, b=B[d], alpha=0, x=x)
    dev8 = float(np.max(np.abs(cb8-np.array([float(r['direct_CB8']) for r in stored]))))
    assert dev8 < 1e-12, (d, dev8)
    chk = {str(xx): float(cb3[int(np.argmin(abs(x-xx)))]) for xx in CHECK[d]}
    assert all(abs(x[int(np.argmin(abs(x-xx)))]-xx) < 1e-12 for xx in CHECK[d])
    assert all(abs(chk[str(xx)]-v) < 5*10**-(len(repr(v).split('.')[1])+0) for xx, v in CHECK[d].items()), (d, chk)
    # independent adaptive quadrature of the same Borel integral at the check points
    p = M.pol(M.series('direct', 3), B[d], 0, M.A); pf = [float(v) for v in p]; A0 = float(M.A)
    quadchk = []
    for xx in list(CHECK[d])+[float(x[0]), float(x[-1])]:
        arg = (d-4*xx)
        f = lambda t: math.exp(-t+B[d]*math.log(t))*np.polynomial.polynomial.polyval((arg*t/A0)/(math.sqrt(1+arg*t/A0)+1)**2, pf) if t > 0 else 0.
        ad = quad(f, 0, np.inf, epsabs=1e-13, epsrel=1e-13, limit=400)[0]
        gl = float(M.cb('direct', 3, b=B[d], alpha=0, x=np.array([xx]))[0])
        quadchk.append({'Delta_sigma': xx, 'GL240': gl, 'adaptive': ad, 'diff': gl-ad})
    assert max(abs(q['diff']) for q in quadchk) < 1e-10
    after = {str(p.relative_to(PKG)): sha(p) for p in tracked}
    assert after == before, 'release file changed'
    i0 = int(np.argmin(cb3))
    meta['panels'][f'{d}d'] = {'code': f'{d}d/code/calculate.py', 'function': f"cb('direct', 3, b={B[d]}, alpha=0, x=stored grid)",
                               'b_L': B[d], 'alpha': 0, 'A': mp.nstr(M.A, 20), 'C0_C3': [mp.nstr(c, 20) for c in M.C[:4]],
                               'grid': f'{d}d/results/curves.csv Delta_sigma ({len(x)} points)', 'release_files_sha256': before,
                               'check_values': {'expected': {str(k): v for k, v in CHECK[d].items()}, 'computed': chk},
                               'direct_CB8_recomputed_vs_stored_max_abs': dev8, 'quadrature_checks': quadchk,
                               'min': {'Delta_sigma': float(x[i0]), 'value': float(cb3[i0])}, 'max': float(np.max(cb3))}
    rows += [{'d': d, 'Delta_sigma': repr(float(xx)), 'CB3_direct': repr(float(v))} for xx, v in zip(x, cb3)]
    print(f'{d}d CB3:', {k: round(v, 5) for k, v in chk.items()}, '| min %.6f at %.4f | CB8 recomputation %.1e' % (cb3[i0], x[i0], dev8))
with (PKG/'combined'/'cb3_gff_only.csv').open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['d', 'Delta_sigma', 'CB3_direct']); w.writeheader(); w.writerows(rows)
meta['csv_sha256'] = sha(PKG/'combined'/'cb3_gff_only.csv')
(PKG/'combined'/'cb3_gff_only.json').write_text(json.dumps(meta, indent=1)+'\n')
print('wrote combined/cb3_gff_only.csv (%d rows) and combined/cb3_gff_only.json' % len(rows))
