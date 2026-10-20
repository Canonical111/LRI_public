#!/usr/bin/env python3
"""C5(3) from eq. (C5) of C5_d3.tex with the archived 55/90-digit Q3, P4(3), P5(3) and the new N3."""
import json, sys
import mpmath as mp
mp.mp.dps = 60
bundle = sys.argv[1]
pv = json.load(open(bundle + '/lri_d3_reduction_update/verification/general_d3/period_values.json'))['runs'][-1]['values']
c = lambda s: mp.mpf(str(s).strip('()').split(' ')[0])
Q, P4, P5 = c(pv['Q3']), c(pv['P4_3']), c(pv['P5_3'])
m = json.load(open('masters_d3.json'))
N = mp.mpf(m['N3'])
pi, z3 = mp.pi, mp.zeta(3)
A = 2 + 4 * mp.log(2) - pi
S = -15 * A**4 + (360 - 30 * pi**2) * A**2 + (828 * pi**3 - 1728) * A - 21456 * z3 * A - 83 * pi**4 + 312 * pi**2 + 5328
terms = {'P5': -1536 * P5, 'N3': -1536 * N, 'P4': 384 * A * P4, 'Q': -1728 * Q**2 + (720 * A**2 + 336 * pi**2 - 4032) * Q, 'scalar': S}
C5 = mp.fsum(terms.values()) / 46656
# cross-check against the general formula with the polygamma constants
R, U, V, X = pi**2 / 3 - 4, 2 * pi**3 - 56 * z3, 16 - 16 * z3, mp.mpf(14) / 15 * pi**4 - 96
K, L, Z = mp.mpf(m['K3']), mp.mpf(m['L3']), mp.mpf(m['Z3'])
C5g = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q**2 + 720 * A**2 * Q + 1008 * Q * R + 7152 * Z
       - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * X) / 46656
d = m['accuracy_digits']
print('C5(3) =', mp.nstr(C5, d), '  general-formula check:', mp.nstr(C5 - C5g, 3))
parts = {'$P_5(3)$': mp.nstr(terms['P5'] / 46656, 12), '$\\mathcal N_3$': mp.nstr(terms['N3'] / 46656, 12),
         '$P_4(3)$': mp.nstr(terms['P4'] / 46656, 12), '$Q_3$': mp.nstr(terms['Q'] / 46656, 12), 'scalar': mp.nstr(terms['scalar'] / 46656, 12)}
json.dump(dict(C5=str(C5), parts=parts), open('c5_value.json', 'w'), indent=1)
print(parts)
