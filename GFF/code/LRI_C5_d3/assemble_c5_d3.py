#!/usr/bin/env python3
"""C5(3) assembled from the general-d formula (condensed note gs:C5, gs:psiBasis) at d=3 (q=3/4).

Symbolic part: the polygamma constants A, R, U, V, X in closed form and the scalar polynomial.
Numerical part: masters Q3, P4(3), P5(3) from the archived d=3 period values (lri_d3_reduction_update,
period_values.json, 55-digit formula run) and K3, L3, Z3 from the archived spectral runs
(lri_d3_matrix_update, coefficient_values_new.json; about 11-12 digits)."""
import json, sys
import sympy as sp
import mpmath as mp

q = sp.Rational(3, 4)
A = sp.simplify(sp.expand_func(sp.polygamma(0, 2*q) + sp.polygamma(0, 1) - 2*sp.polygamma(0, q)))
R = sp.simplify(sp.expand_func(sp.polygamma(1, 2*q) - sp.polygamma(1, 1)))
U = sp.simplify(sp.expand_func(sp.polygamma(2, q)))
V = sp.simplify(sp.expand_func(sp.polygamma(2, 1) + sp.polygamma(2, 2*q)))
X = sp.simplify(sp.expand_func(sp.polygamma(3, 2*q) - sp.polygamma(3, 1)))
Q, P4, P5, K, L, Z = sp.symbols('Q_3 P_4 P_5 K_3 L_3 Z_3')
N = sp.Symbol('N_3')            # N_3 = K_3 + 3/8 L_3 - 149/32 Z_3

C5 = (-1536*(P5 + K) + 384*A*P4 - 576*L - 1728*Q**2 + 720*A**2*Q + 1008*Q*R + 7152*Z
      - 15*A**4 - 90*A**2*R + 414*A*U - 108*A*V - 117*R**2 - 75*X) / 46656
scalar = sp.expand(-15*A**4 - 90*A**2*R + 414*A*U - 108*A*V - 117*R**2 - 75*X)
C5N = sp.expand(C5.subs(K, N - sp.Rational(3, 8)*L + sp.Rational(149, 32)*Z))
assert sp.simplify(C5N.coeff(L)) == 0 and sp.simplify(C5N.coeff(Z)) == 0

print('A =', A, '  R =', R, '  U =', U, '  V =', V, '  X =', X)
print('46656 C5(3) = -1536 (P5 + N3) + 384 A P4 - 1728 Q^2 + (720 A^2 + 1008 R) Q + S')
print('  720A^2+1008R =', sp.expand(720*A**2 + 1008*R))
print('  S =', scalar)

bundle = sys.argv[1]
pv = json.load(open(bundle + '/lri_d3_reduction_update/verification/general_d3/period_values.json'))['runs'][0]['values']
cv = [r for r in json.load(open(bundle + '/lri_d3_matrix_update/code/general_special/coefficient_values_new.json'))
      if r['d'] == 3]
mp.mp.dps = 50
num = lambda s: mp.mpf(s.strip('()').split('+')[0]) if s.startswith('(') else mp.mpf(s)
vals = {Q: num(pv['Q3']), P4: num(pv['P4_3']), P5: num(pv['P5_3'])}
last = cv[-1]
vals.update({K: mp.mpf(last['K']), L: mp.mpf(last['L']), Z: mp.mpf(last['Z'])})
print('archived d=3 nonprimitive runs (spins, K, L, Z):', [(r['spins'], r['K'], r['L'], r['Z']) for r in cv])
Nval = vals[K] + mp.mpf(3)/8*vals[L] - mp.mpf(149)/32*vals[Z]
sub = {s: sp.Float(str(v), 45) for s, v in vals.items()}
c5 = sp.N(C5.subs(sub), 30)
print('N3 =', mp.nstr(Nval, 15))
print('C5(3) =', c5, ' (archived coefficient:', last['coefficients'][5], ')')
parts = {'scalar S/46656': sp.N(scalar/46656, 20), 'Q terms': sp.N(((-1728*Q**2 + (720*A**2 + 1008*R)*Q)/46656).subs(sub), 20),
         '384 A P4/46656': sp.N((384*A*P4/46656).subs(sub), 20), '-1536 P5/46656': sp.N((-1536*P5/46656).subs(sub), 20),
         '-1536 N3/46656': sp.N(-1536*sp.Float(str(Nval), 30)/46656, 15)}
for k, v in parts.items():
    print('  ', k, '=', v)
