#!/usr/bin/env python3
"""PSLQ on the spectral L2, K2 (this workflow's values, not C62d's) at two precisions.
usage: pslq_d2.py COMBINED.json TARGETS.json DIGITS_L2 DIGITS_K2"""
import sys, json, math
import mpmath as mp
C, TG = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
DD = {'L2': int(sys.argv[3]), 'K2': int(sys.argv[4])}
mp.mp.dps = max(DD.values()) + 10
L2, K2 = mp.mpf(C['L2']), mp.mpf(C['K2'])
Bm, Bp = mp.mpf(TG['Bm']), mp.mpf(TG['Bp'])
pi, l2, G, z3 = mp.pi, mp.log(2), mp.catalan, mp.zeta(3)
li4 = mp.polylog(4, mp.mpf(1) / 2)
bases = {
 'L2': (['pi^3 L2', 'Bm^2', 'Bp^2', 'Bm Bp', 'log2 Bm^2', 'log2 Bp^2', 'log2 Bm Bp', 'pi Bm^2', 'pi Bp^2', 'pi Bm Bp'],
        [pi**3 * L2, Bm**2, Bp**2, Bm * Bp, l2 * Bm**2, l2 * Bp**2, l2 * Bm * Bp, pi * Bm**2, pi * Bp**2, pi * Bm * Bp]),
 'K2': (['K2', 'G^2', 'zeta3 log2', 'pi^4', 'pi^2 log^2 2', 'log^4 2', 'Li4(1/2)', 'pi^2 G', 'pi^3 log2', 'pi zeta3', 'pi G log2', 'G log^2 2'],
        [K2, G**2, z3 * l2, pi**4, pi**2 * l2**2, l2**4, li4, pi**2 * G, pi**3 * l2, pi * z3, pi * G * l2, G * l2**2]),
}
out = {}
for name, (lab, vec) in bases.items():
    n = len(vec); D = DD[name]
    for dig in (max(17, D - 15), D):
        mp.mp.dps = dig
        rel = mp.pslq([+v for v in vec], maxcoeff=10**6, maxsteps=10**6, tol=mp.mpf(10) ** (-(dig - 5)))
        mp.mp.dps = D + 10
        if rel is None:
            line = '%s @%d digits: no relation with max|c| <= 1e6 (hygiene bound n*log10(maxc) = %d*6 = %d)' % (name, dig, n, 6 * n)
        else:
            mc = max(abs(c) for c in rel)
            r = mp.fsum(c * v for c, v in zip(rel, vec))
            ok = n * math.log10(max(mc, 1)) <= D - 10
            line = '%s @%d digits: %s ; residual %s ; n*log10(max|c|) = %.1f vs bound %d -> %s' % (
                name, dig, ' + '.join('%d*[%s]' % (c, l) for c, l in zip(rel, lab) if c), mp.nstr(r, 3),
                n * math.log10(max(mc, 1)), D - 10, 'ACCEPTABLE' if ok else 'CHANCE-LEVEL')
        print(line); out['%s_%d' % (name, dig)] = line
json.dump(out, open(sys.argv[1].replace('.json', '_pslq.json'), 'w'), indent=1)
