#!/usr/bin/env python3
"""C63d, OPE review 2026-10-16: the two four-vertex kites at d=2 and finite eps from the note's two-dimensional kite
formula (done:kite, done:ordered, done:mixed, done:kiteFactorization), against the package's finite-eps Mellin-Barnes
representation full(2, eps, kind) (code/a4/full_kite_checks.py, the object under test). Slowly convergent 3F2(1) are
evaluated after Thomae's transformation. Usage: python3 check_kx_d2.py PACKAGE_CODE_A4_DIR OUT.json"""
import json, sys
import mpmath as mp
mp.mp.dps = 30
def f32(a1, a2, a3, b1, b2):
    s = b1 + b2 - a1 - a2 - a3
    if mp.re(s) > 0.6:
        return mp.hyp3f2(a1, a2, a3, b1, b2, 1)
    up = sorted([a1, a2, a3], key=lambda x: -mp.re(x)); a, b, c = up
    # Thomae: 3F2(a,b,c;d,e;1) = G(d)G(e)G(s)/(G(a)G(s+b)G(s+c)) 3F2(d-a,e-a,s;s+b,s+c;1), new excess = a
    return (mp.gamma(b1) * mp.gamma(b2) * mp.gamma(s) / (mp.gamma(a) * mp.gamma(s + b) * mp.gamma(s + c))
            * mp.hyp3f2(b1 - a, b2 - a, s, s + b, s + c, 1))
B = mp.beta
def O(a, b, A, Bp, c): return B(a + 1, c + 1) * B(a + A + c + 2, Bp + 1) * f32(-b, a + 1, a + A + c + 2, a + c + 2, a + A + Bp + c + 3)
def Mm(a, b, A, Bp, c): return B(a + 1, -a - b - c - 1) * B(Bp + 1, -A - Bp - c - 1) * f32(-c, a + 1, Bp + 1, -b - c, -A - c)
def J(p):
    a, b, A, Bp, c = [-x / 2 for x in p]
    return (mp.sin(mp.pi * a) * mp.sin(mp.pi * Bp) * O(a, b, A, Bp, c) * Mm(a, b, A, Bp, c)
            + mp.sin(mp.pi * A) * mp.sin(mp.pi * b) * O(A, Bp, a, b, c) * Mm(A, Bp, a, b, c)) / mp.pi**2
sys.path.insert(0, sys.argv[1])
from full_kite_checks import full
res = {}
for e in ('0.15', '0.1', '0.06', '0.04', '0.02'):
    em = mp.mpf(e); u = mp.mpf(1) / 2 - em / 4
    kx = J([2 * u, 4 * u, 4 * u, 2 * u, 2 * u]); kp = J([2 * u, 2 * u, 2 * u, 2 * u, 4 * u])
    fx = full(2, float(e), 2); fp = full(2, float(e), 4)
    mp.mp.dps = 30
    res[e] = {'K_x_KLT': mp.nstr(kx, 16), 'K_x_package_MB': mp.nstr(fx, 16), 'rel_x': mp.nstr(abs(kx - fx) / abs(kx), 3),
              'K_par_KLT': mp.nstr(kp, 16), 'K_par_package_MB': mp.nstr(fp, 16), 'rel_par': mp.nstr(abs(kp - fp) / abs(kp), 3)}
    print(e, res[e], flush=True)
json.dump(res, open(sys.argv[2], 'w'), indent=1)
ok = all(mp.mpf(v['rel_x']) < mp.mpf('1e-12') and mp.mpf(v['rel_par']) < mp.mpf('1e-12') for v in res.values())
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
