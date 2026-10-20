"""Enumerate kite orientations of the completed K5 at the K-path and classify their 2-fold MB integrands:
   double divisors, exponents E1,E2,E3 (power of the integrand along e1, e2, e1-e2)."""
import itertools, sympy as sp
q, t = sp.symbols('q t', positive=True)
E = {(0,1): t/2, (0,2): q, (0,3): q, (0,4): 2*q - t/2, (1,2): q, (1,3): 2*q - t/2, (1,4): q, (2,3): q, (2,4): q, (3,4): t/2}
def e(a, b): return E[(min(a,b), max(a,b))]
seen = {}
for inf, E1, E2, S, B in itertools.permutations(range(5)):
    if E1 > E2: continue
    n1, n2, n3 = e(S,E1), e(S,E2), e(S,B); a3, a4 = e(B,E1), e(B,E2)
    lam = sp.simplify(n1+n2+n3-2*q)
    # lines: (direction, side, constant c) meaning Gamma(c + s*z) with s=+1 (left poles at z=-c-k) or s=-1 (right poles at z=c+k)
    num = [('z1',-1,0), ('z2',-1,0), ('w',+1,lam), ('z2',-1,n1-lam), ('z1',-1,n2-lam), ('w',+1,n3),
           ('z1',+1,2*q-a3), ('z2',+1,2*q-a4), ('w',-1,a3+a4-2*q)]
    den = [('z1',-1,a3), ('z2',-1,a4), ('w',+1,4*q-a3-a4)]
    # pole multiplicity per (dir, side, class of c mod Z) : count numerator minus denominator overlaps (only exact equal-mod-Z)
    from collections import defaultdict
    cnt = defaultdict(int)
    for d_, s_, c_ in num:
        cnt[(d_, s_, sp.simplify(c_))] += 1
    dbl = [k for k, v in cnt.items() if v > 1]
    # integer-offset coincidences between same-direction same-side lines
    offs = []
    keys = list(cnt.keys())
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            if keys[i][0] == keys[j][0] and keys[i][1] == keys[j][1]:
                diff = sp.simplify(keys[i][2]-keys[j][2])
                if diff.is_integer: offs.append((keys[i], keys[j]))
    E1x = sp.simplify(-2 + n2 + n3 + 2*a4 - 4*q)
    E2x = sp.simplify(-2 + n1 + n3 + 2*a3 - 4*q)
    E3x = sp.simplify(-6 - E1x - E2x)
    key = (str(sorted([(str(k), cnt[k]) for k in dbl])), str(E1x), str(E2x))
    print('inf=%d E=(%d,%d) S=%d B=%d | star nu=(%s,%s,%s) bubble a=(%s,%s) | double: %s | offsets: %d | E1=%s E2=%s E3=%s' % (
        inf, E1, E2, S, B, n1, n2, n3, a3, a4, [(k[0], k[1], k[2]) for k in dbl], len(offs), E1x, E2x, E3x))
