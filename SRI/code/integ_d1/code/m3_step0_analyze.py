import json, mpmath as mp
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import provenance as _pv
mp.mp.dps = 40
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in d.items()}
        for k, d in _pv.load_step0('m3_step0_response.json')[0].items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in _pv.load_step0('m3_step0_F2base.json')[0].items()}
def expr(target):
    terms = {src: d[target] for src, d in resp.items() if target in d}
    return base.get(target, 0), terms
print('Analyticity relations (F1 delta^k w^j, j<0, must vanish) and targets f_2_n_k = (-1)^n [delta^k w^n] F1:')
needed = set()
for k in (1, 2):
    jmin = min(j for (kk, j) in base if kk == k)
    for j in range(jmin, 3 - k + 1):
        c0, terms = expr((k, j))
        kind = 'RELATION' if j < 0 else f'TARGET f_2_{j}_{k}'
        if j >= 0 and j + k > 2: continue
        srcs = sorted(terms)
        needed |= set(srcs)
        print(f'  {kind:14s} [d^{k} w^{j}]: const {mp.nstr(c0, 8):>12}  + J2 coeffs {[(s, mp.nstr(terms[s], 6)) for s in srcs]}')
print('\nraw J2 Laurent coefficients needed (k, j):', sorted(needed))
