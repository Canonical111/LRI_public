#!/usr/bin/env python3
"""Integer-relation tests for S''(3/2) (equivalently Z3) at the accuracy established by two independent Cauchy runs.
Exact background (derived + verified): Z3 = (4 pi^2/3) S2 - 3 g (4G + pi^2/2),  Q3 = 4 pi^2 H - g,  S'(3/2) = (3/4)(g/pi) - pi H,
with H = H3(0) = S(3/2), g = Gamma(1/4)^10/(48 pi^(7/2)).  So the target is S2 = S''(3/2).
Hygiene: a hit counts only if n*log10(max|c|) <= digits-10, residual at noise level, and the relation reappears at a lower
second precision.  usage: pslq_z3.py derivedA.json derivedB.json perB.json"""
import sys, json
import mpmath as mp
DA, DB = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
mp.mp.dps = min(DA['dps'], DB['dps'])
S2a, S2b = mp.mpf(DA['S2']), mp.mpf(DB['S2'])
Ha, Hb = mp.mpf(DA['H30']), mp.mpf(DB['H30'])
err = max(abs(S2a - S2b) / abs(S2b), abs(Ha - Hb) / abs(Hb))
digits = int(-mp.log10(err)) - 2
print('S2 run difference %s, H difference %s -> established relative digits %d' % (mp.nstr(abs(S2a - S2b), 3), mp.nstr(abs(Ha - Hb), 3), digits))
S2, H = S2b, Hb
PB = {k: mp.re(mp.mpmathify(v.replace(' ', ''))) for k, v in json.load(open(sys.argv[3]))['values'].items()}
pi, G, s2, l2 = mp.pi, mp.catalan, mp.sqrt(2), mp.log(2)
lr = mp.log(1 + s2)
L8 = mp.dirichlet(2, [0, 1, 0, 1, 0, -1, 0, -1])      # L(2, chi_-8)
g = mp.gamma(mp.mpf(1) / 4) ** 10 / (48 * pi ** mp.mpf(3.5))
gp = g / pi
print('H - (-x30/(2 sqrt2 pi^1.5)) =', mp.nstr(H + PB['x30'] / (2 * s2 * pi ** mp.mpf(1.5)), 3))
Z3 = 4 * pi ** 2 / 3 * S2 - 3 * g * (4 * G + pi ** 2 / 2)
X0, Xh, a4b4 = PB['x40'], PB['x4h'], PB['a4'] * PB['b4']
P4 = 2 * pi * X0 - 10 * pi * Xh + (14 * s2 - 20) * pi * a4b4
print('P4(3) =', mp.nstr(P4, 50))
results = []

def test(name, target, basis, prec_digits=None):
    dg = digits if prec_digits is None else prec_digits
    with mp.workdps(dg + 10):
        names = [n for n, _ in basis]
        vec = [+target] + [+v for _, v in basis]
        n = len(vec)
        cmax = int(mp.floor(mp.mpf(10) ** (mp.mpf(dg - 10) / n)))
        rel = mp.pslq(vec, tol=mp.mpf(10) ** (-(dg - 3)), maxcoeff=cmax, maxsteps=10 ** 7)
        if rel is None or rel[0] == 0:
            line = '%-6s no relation with |coefficients| <= %d (n=%d, %d digits)' % (name, cmax, n, dg)
        else:
            resid = abs(mp.fsum(r * v for r, v in zip(rel, vec))) / max(abs(r * v) for r, v in zip(rel, vec))
            line = '%-6s RELATION(resid %s): %s*T + %s' % (name, mp.nstr(resid, 3), rel[0], ' + '.join('%s*%s' % (r, nm) for r, nm in zip(rel[1:], names) if r))
    print(line, flush=True); results.append(line)
    open('pslq_z3.log', 'a').write(line + '\n')
    return rel

W4 = [('pi^2', pi ** 2), ('G', G)]
W8 = [('pi^2', pi ** 2), ('sqrt2 pi^2', s2 * pi ** 2), ('G', G), ('L8', L8), ('pi log2', pi * l2),
      ('sqrt2 pi logr', s2 * pi * lr), ('log2^2', l2 ** 2), ('log2 logr', l2 * lr), ('logr^2', lr ** 2)]
W8x = W8 + [('sqrt2 G', s2 * G), ('sqrt2 L8', s2 * L8), ('sqrt2 pi log2', s2 * pi * l2), ('pi logr', pi * lr)]
low = [('1', 1), ('pi', pi), ('sqrt2 pi', s2 * pi), ('log2', l2), ('sqrt2 logr', s2 * lr)]
prod = lambda P, W: [('%s*%s' % (pn, wn), pv * wv) for pn, pv in P for wn, wv in W]
pieces = [('H', H), ('g/pi', gp)]
Q3 = 4 * pi ** 2 * H - g
P4p = [('pi X0', pi * X0), ('pi Xh', pi * Xh), ('pi a4b4', pi * a4b4), ('sqrt2 pi a4b4', s2 * pi * a4b4)]
QP = [('4pi^2 H', 4 * pi ** 2 * H), ('g', g)]
TESTS = [
    ('T1', 'S2', prod(pieces, W4 + [('1', 1)]), None),                 # level-4 weight-2 (d=1,2 analogues)
    ('T2', 'S2', prod(pieces, W8), None),                              # requested level-8 weight-2 basis x pieces of Q3
    ('T3', 'S2', prod(pieces, W8x), None),                             # extended level-8 (sqrt2 multiples)
    ('T4', 'S2', prod(pieces, W8 + low), None),                        # inhomogeneous weight <= 2
    ('T5', 'Z3', P4p + prod(QP, W4 + [('1', 1)]), 180),               # (P4 pieces known to ~188 digits) d=4 analogue: Z4 = P4(4)/8 exactly
    ('T6', 'Z3', P4p + [('P4/pi', P4 / pi), ('P4/pi^2', P4 / pi ** 2)] + prod(QP, W8), 180),
    ('T7', 'Z3', [('P4', P4)] + prod([('Q3', Q3), ('g', g)], W8 + [('1', 1)]), 180),
    ('T2lo', 'S2', prod(pieces, W8), int(digits * 2 / 3)),
    ('T5lo', 'Z3', P4p + prod(QP, W4 + [('1', 1)]), 120),
]
GEN = [('1', 1), ('pi', pi), ('log2', l2), ('pi^2', pi ** 2), ('G', G), ('pi log2', pi * l2), ('log2^2', l2 ** 2),
       ('zeta3/pi', mp.zeta(3) / pi), ('L8', L8), ('logr', lr), ('pi logr', pi * lr), ('log2 logr', l2 * lr), ('logr^2', lr ** 2)]
GEN = GEN + [('sqrt2 ' + n, s2 * v) for n, v in GEN]
TESTS += [('T8', 'S2', prod(pieces, GEN), None)]
GEN2 = [('1', 1), ('pi', pi), ('log2', l2), ('logr', lr), ('zeta3/pi', mp.zeta(3) / pi), ('pi^2', pi ** 2), ('G', G), ('L8', L8)]
GEN2 = GEN2 + [('sqrt2 ' + n, s2 * v) for n, v in GEN2]
TESTS += [('T8a', 'S2', prod(pieces, GEN2), None)]
TGT = {'S2': S2, 'Z3': Z3}

def run(i):
    nm, t, basis, pd = TESTS[i]
    return test(nm, TGT[t], basis, pd)

if __name__ == '__main__':
    import os
    from multiprocessing import Pool
    sel = os.environ.get('TESTS')
    idx = [i for i, T in enumerate(TESTS) if not sel or T[0] in sel.split(',')]
    with Pool(len(idx)) as pool:
        pool.map(run, idx, chunksize=1)
    results = [l for l in open('pslq_z3.log').read().splitlines()] if os.path.exists('pslq_z3.log') else []
    json.dump(dict(digits=digits, S2=str(S2), H30=str(H), Z3=str(Z3), P4=str(P4), results=results), open('pslq_z3_results.json', 'w'), indent=1)
    