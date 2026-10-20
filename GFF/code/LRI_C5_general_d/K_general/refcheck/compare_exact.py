#!/usr/bin/env python3
"""compare a route-A/B output json with exact/known values at d=1,2,3 (validation)"""
import sys, json
import mpmath as mp
mp.mp.dps = 60
G = mp.catalan; z3 = mp.zeta(3); l2 = mp.log(2)
P4_2 = mp.mpf('250.487315581867285531851756887911407168355710923583666540539307636224826')
Q2 = mp.gamma(mp.mpf(1)/4)**8/(24*mp.pi**4)
EX = {
 '2': dict(Q=Q2, P4=P4_2, L=-2*l2*P4_2, Z=4*G*Q2, K=32*G**2-28*z3*l2),
 # d=3: Q3 = W3_center/3, P4(3) = W4_center of LRI_C5_d3/run_C_combined.json (dps 110); the 90-digit formula run
 # (inputs/general_d3/period_values.json, dps 55) agrees with these to ~53 digits
 '3': dict(Q=mp.mpf('15.0513076936615661087725645370705510986934747805015269348877567401422822982761048666485750628762354760154827156388888889')/3,
           P4=mp.mpf('62.0583279434066724664633885840967369182686384706117573441491501766188713247020243698768399388940309344888554680277777778'),
           # L3, Z3: LRI_C5_d3/run_C_combined.json (dps 110 spectral run; agrees with masters_d3.json to its 43 digits)
           L=mp.mpf('-62.7105849683876693472961734335348474600014697352518163896150217947496042860433131091729840559691265107246054200941180772'),
           Z=mp.mpf('8.8209248930600924855368673281740808743649007375933604355253732733890466167588987395355248838479616723800354201617821904'),
           K=mp.mpf('1.1485946495271793365566463108106731876338481012643178421117015121184545900277289889983896689063188035835547868671729294605')),
 '1': dict(K=128*G**2+24*mp.pi**2*G-4*mp.pi**3*l2-28*(mp.pi+4*l2)*z3),
}
J = json.load(open(sys.argv[1]))
d = J['d']; F = J['final']
print('d =', d, ' dps =', J['dps'], ' L =', J.get('L'))
for k in ('Q', 'P4', 'L', 'Z', 'K', 'chk'):
    v = mp.mpf(F[k]) if k in F else None
    if v is None: continue
    if d in EX and k in EX[d]:
        e = EX[d][k]; diff = v - e
        dig = -mp.log10(abs(diff/e)) if diff != 0 else mp.inf
        print('  %-4s %s  exact-diff %s  (%.1f digits)' % (k, mp.nstr(v, 30), mp.nstr(diff, 3), float(dig) if dig != mp.inf else 99))
    else:
        print('  %-4s %s' % (k, mp.nstr(v, 30)))
