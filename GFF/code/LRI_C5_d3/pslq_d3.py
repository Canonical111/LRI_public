#!/usr/bin/env python3
"""Integer-relation tests for the d=3 nonprimitive masters, at the accuracy actually established by two independent
high-precision runs (the PSLQ tolerance is set from their difference, never from the working precision).

Hypotheses, each modelled on what is proved at d=1 (condensed note eq. KLpsiReflected, gs:d1Dictionary):
  HK  K_3 is a weight-4 polygamma/zeta combination (as K at d=1).
  HL  L_3 lies in the span of the pieces of P_4(3) (pi X0, pi X_h, pi a4 b4, sqrt2 pi a4 b4) with coefficients in
      Q{1, pi, log 2} (as L = -(3A-pi)/6 P_4 - (2 pi/3) B_- at d=1).
  HZ  Z_3 lies in the span of the two pieces of Q_3 (pi^2 H_3(0), sqrt(pi) a3 b3) with weight <= 2 coefficients
      (as Z = Q H at d=1, Z = 4 G Q at d=2).
  HN  N_3 = K_3 + 3/8 L_3 - 149/32 Z_3 in the union of the HK/HL/HZ bases.
"""
import json, sys
import mpmath as mp

runs = [json.load(open(f)) for f in sys.argv[1:3]]
bundle = sys.argv[3]
mp.mp.dps = 60
num = lambda s: mp.mpf(str(s).strip('()').split('+')[0].split(' -')[0]) if str(s).startswith('(') else mp.mpf(s)
def val(run, k):
    return mp.re(mp.mpmathify(run[k].replace(' ', '')))
masters = {}
for k in ('K3', 'L3', 'Z3'):
    v1, v2 = val(runs[0], k), val(runs[1], k)
    masters[k] = (v2, abs(v1 - v2))
    print('%s = %s   (run difference %s)' % (k, mp.nstr(v2, 45), mp.nstr(abs(v1 - v2), 3)))
K3, L3, Z3 = (masters[k][0] for k in ('K3', 'L3', 'Z3'))
err = max(masters[k][1] for k in masters)
N3 = K3 + mp.mpf(3) / 8 * L3 - mp.mpf(149) / 32 * Z3
print('N3 =', mp.nstr(N3, 45))
digits = int(-mp.log10(err / abs(L3))) - 2 if err > 0 else 40
print('established relative accuracy ~1e-%d; PSLQ tolerance set accordingly' % digits)

pv = json.load(open(bundle + '/lri_d3_reduction_update/verification/general_d3/period_values.json'))['runs'][-1]['values']
c = lambda s: mp.mpf(str(s).strip('()').split(' ')[0])
Q3, P4, X0, Xh = c(pv['Q3']), c(pv['P4_3']), c(pv['Xi4_0']), c(pv['Xi4_1_8'])
am = pv['amplitudes']
a3, b3, a4, b4 = c(am['a3']), c(am['b3']), c(am['a4']), c(am['b4'])
pi, G, z3, l2, s2 = mp.pi, mp.catalan, mp.zeta(3), mp.log(2), mp.sqrt(2)
H30 = (Q3 + mp.gamma(mp.mpf(1) / 4) ** 10 / (48 * pi ** mp.mpf(3.5))) / (4 * pi ** 2)
print('checks: P4 formula', mp.nstr(P4 - (2 * pi * X0 - 10 * pi * Xh + (14 * s2 - 20) * pi * a4 * b4), 3),
      ' Q3 formula', mp.nstr(Q3 - (4 * pi ** 2 * H30 - s2 / 3 * mp.sqrt(pi) * a3 * b3), 3))

def test(name, target, basis):
    """Meaningful only if n*log10(maxcoeff) stays ~10 digits below the established accuracy; a relation is accepted
    only if its residual is at the noise level of the masters."""
    names = [n for n, _ in basis]
    vec = [target] + [v for _, v in basis]
    n = len(vec)
    cmax = int(mp.floor(mp.mpf(10) ** (mp.mpf(digits - 10) / n)))
    rel = mp.pslq(vec, tol=mp.mpf(10) ** (-(digits - 3)), maxcoeff=cmax, maxsteps=10 ** 6)
    if rel is None or rel[0] == 0:
        print('%-4s no relation with |coefficients| <= %d (n=%d, %d established digits)' % (name, cmax, n, digits))
        return None
    resid = abs(mp.fsum(r * v for r, v in zip(rel, vec))) / max(abs(r * v) for r, v in zip(rel, vec))
    tag = 'RELATION' if resid < mp.mpf(10) ** (-(digits - 5)) else 'rejected (residual above noise)'
    print('%-4s %s: %s * target + %s   (relative residual %s)' % (name, tag, rel[0], ' + '.join('%s*%s' % (r, nm) for r, nm in zip(rel[1:], names) if r), mp.nstr(resid, 3)))
    return rel

w = [('1', 1), ('pi', pi), ('log2', l2)]
HK = [('pi^4', pi ** 4), ('pi^2 G', pi ** 2 * G), ('G^2', G ** 2), ('pi^3', pi ** 3), ('zeta3', z3),
      ('pi^3 log2', pi ** 3 * l2), ('zeta3 log2', z3 * l2), ('pi zeta3', pi * z3), ('beta4', mp.dirichlet(4, [0, 1, 0, -1]))]
HL = [('%s*%s' % (m, p), mv * pv_) for m, mv in w for p, pv_ in
      (('pi X0', pi * X0), ('pi Xh', pi * Xh), ('pi a4b4', pi * a4 * b4), ('sqrt2 pi a4b4', s2 * pi * a4 * b4))]
w2 = [('1', 1), ('pi', pi), ('pi^2', pi ** 2), ('G', G), ('log2', l2), ('pi log2', pi * l2), ('log2^2', l2 ** 2)]
HZ = [('%s*%s' % (m, p), mv * pv_) for m, mv in w2 for p, pv_ in (('pi^2 H3(0)', pi ** 2 * H30), ('sqrtpi a3b3', mp.sqrt(pi) * a3 * b3))]
test('HK', K3, HK)
test('HL', L3, HL)
test('HZ', Z3, HZ)
test('HZq', Z3, [('Q3*' + m, Q3 * mv) for m, mv in w2])
A = 2 + 4 * l2 - pi
test('HL1', L3 + (3 * A - pi) / 6 * P4, [('pi*' + p, pi * v) for p, v in (('pi X0', pi * X0), ('pi Xh', pi * Xh), ('pi a4b4', pi * a4 * b4), ('sqrt2 pi a4b4', s2 * pi * a4 * b4))])
test('HL2', L3, [('P4', P4), ('A P4', A * P4), ('pi P4', pi * P4), ('log2 P4', l2 * P4)] + [('pi*' + p, pi * v) for p, v in (('pi X0', pi * X0), ('pi Xh', pi * Xh), ('pi a4b4', pi * a4 * b4), ('sqrt2 pi a4b4', s2 * pi * a4 * b4))])
test('HK1', K3 + A * (2 * pi**3 - 56 * z3) / 4, [('pi^4', pi ** 4), ('pi^2 G', pi ** 2 * G), ('G^2', G ** 2), ('A pi^3', A * pi ** 3), ('A zeta3', A * z3)])
out = dict(K3=str(K3), L3=str(L3), Z3=str(Z3), N3=str(N3), accuracy_digits=digits)
json.dump(out, open('masters_d3.json', 'w'), indent=1)
