"""Cross-check of the Laurent (ser-mode) coefficients against a contour in w = 1 - K (cx mode), as in M2:
the angular integrals A^{(k)}_j(K) (analytic in 0 < |w| < 1/4) are sampled on |w| = r at N points (half computed,
conjugate symmetry) and their Laurent coefficients compared with the ser-mode ones; also J3^{(1)} coefficients.
usage: python m3_contour_check.py CONTOUR_DIR SER_DIR"""
import sys, os, glob
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cluster_assemble import read_out, assemble_cx, assemble_ser, pattern_factors
mp.mp.dps = 40
cdir, sdir = sys.argv[1], sys.argv[2]
fac = pattern_factors(3)
pts = {}
for f in sorted(glob.glob(os.path.join(cdir, '*.out'))):
    hdr, secs = read_out(f)
    if len(secs) != 187: print('incomplete', f, len(secs)); continue
    kd = hdr['Kdd']
    K = mp.mpc(mp.mpf(float.fromhex(kd[0])) + mp.mpf(float.fromhex(kd[1])), mp.mpf(float.fromhex(kd[2])) + mp.mpf(float.fromhex(kd[3])))
    A = {}
    for s in secs.values():
        for key, v in s['A'].items(): A[key] = A.get(key, 0) + fac[s['pat']] * v
    pts[f] = (1 - K, A)
w0 = list(pts.values())
r = abs(w0[0][0]); N = 2 * (len(w0) - 1)
print(f'{len(w0)} contour points, |w| = {mp.nstr(r, 6)}, N = {N}')
vals = []
for w, A in w0:
    vals.append((w, A))
    if abs(mp.im(w)) > 1e-30: vals.append((mp.conj(w), {k: mp.conj(v) for k, v in A.items()}))
assert len(vals) == N, len(vals)
# ser-mode coefficients
files = sorted(glob.glob(os.path.join(sdir, '*.out')))
secs = {}
for f in files:
    _, s = read_out(f); secs.update(s)
_, As, top = assemble_ser(3, secs, 1, elo=-7, ehi=2)
print('A^{(k)}_j Laurent coefficients: contour vs series')
worst = 0
for (k, j) in sorted(top):
    for e in range(-6, top[(k, j)] + 1):
        cont = mp.re(sum(A[(k, j)] * w ** (-e) for w, A in vals) / N)
        ser = mp.re(As.get((k, j, e), 0))
        d = abs(cont - ser); sc = max(abs(ser), 1)
        if e >= -6: worst = max(worst, d / sc) if e <= 1 else worst
        print(f'  k={k} j={j} w^{e:3d}: contour {mp.nstr(cont, 22):>30}  series {mp.nstr(ser, 22):>30}  diff/max(|.|,1) {mp.nstr(d / sc, 3)}')
print('max deviation (w^-6..w^1):', mp.nstr(worst, 3))

# ---------------------------------------------------------------- flow coefficients from the contour data alone
import json
from cluster_assemble import laurent_gamma_derivs
Lg = laurent_gamma_derivs(3, 2, -4, 12)
Acont = {}
for (k, j) in sorted(top):
    for e in range(-6, 8):
        Acont[(k, j, e)] = mp.re(sum(A[(k, j)] * w ** (-e) for w, A in vals) / N)
c3c = {}
for e in range(-7, 1):
    c3c[e] = sum(Lg[j][e - ea] * Acont[(1, j, ea)] for j in range(3) for ea in range(-6, 8) if (e - ea) in Lg[j])
RES = os.path.join(HERE, '..', 'results')
import provenance as pv
resp = {tuple(map(int, k.split(','))): {tuple(map(int, kk.split(','))): mp.mpf(v) for kk, v in dd.items()}
        for k, dd in pv.load_step0('m3_step0_response.json')[0].items()}
base = {tuple(map(int, k.split(','))): mp.mpf(v) for k, v in pv.load_step0('m3_step0_F2base.json')[0].items()}
def F2c(target):
    return base.get(target, 0) + sum(dd[target] * c3c.get(src[1], 0) for src, dd in resp.items() if target in dd and src[0] == 1)
print('\ncontour-only: J3^{(1)} Laurent coefficients and relations')
for e in range(-7, 0): print(f'  c3_1,{e} = {mp.nstr(c3c[e], 22)}')
for jj in range(-5, 0): print(f'  relation [d^1 w^{jj}] = {mp.nstr(F2c((1, jj)), 4)}')
print(f'  f_2_0_1 (contour) = {mp.nstr(F2c((1, 0)), 22)}')
print(f'  f_2_1_1 (contour) = {mp.nstr(-F2c((1, 1)), 22)}')
