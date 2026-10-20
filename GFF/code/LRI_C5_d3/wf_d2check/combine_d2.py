#!/usr/bin/env python3
"""Combine hp_masters_d2.py circle outputs (part=b, part=t) into L2, Z2, K2 and compare with exact targets.
usage: combine_d2.py B.json T.json TARGETS.json OUT.json"""
import sys, json
import mpmath as mp
B, T, TG = (json.load(open(f)) for f in sys.argv[1:4])
mp.mp.dps = max(int(B['dps']), int(T['dps'])) + 10

def circle(d, idx):
    M = int(d['M']); half = M // 2
    v = {int(k): mp.mpmathify(x[idx].replace(' ', '')) for k, x in d['values'].items()}
    return [v[k] if k <= half else mp.conj(v[M - k]) for k in range(M)], mp.mpf(d['rho']), M

def coef(f, j, rho, M):
    return mp.fsum(f[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j

W3, rb, Mb = circle(B, 0); W4, _, _ = circle(B, 1); F, rt, Mt = circle(T, 0)
c3 = [coef(W3, j, rb, Mb) for j in range(4)]
c4 = [coef(W4, j, rb, Mb) for j in range(3)]
Fk = [coef(F, j, rt, Mt) for j in range(5)]
L2, Z2 = c4[1], 2 * c3[2] / 9
A, U, cs = 4 * mp.log(2), -14 * mp.zeta(3), -2 * mp.euler
K2 = -A * U / 4 + (Fk[3] + cs * Fk[2]) / 4
tg = {k: mp.mpf(v) for k, v in TG.items() if k in ('P4', 'W3', 'Q2', 'L2_claim', 'K2_claim', 'Z2')}
res = dict(
    W3_center_minus_3Q2=c3[0] - tg['W3'], W4_center_minus_P4=c4[0] - tg['P4'],
    dW3db_should_vanish=c3[1],
    L2_minus_claim=L2 - tg['L2_claim'], K2_minus_claim=K2 - tg['K2_claim'], Z2_minus_4GQ2=Z2 - tg['Z2'],
    F0_should_vanish=Fk[0], F1_should_vanish=Fk[1])
rec = dict(B_cfg={k: B[k] for k in B if k != 'values'}, T_cfg={k: T[k] for k in T if k != 'values'},
           L2=str(mp.re(L2)), K2=str(mp.re(K2)), Z2=str(mp.re(Z2)), W3_center=str(mp.re(c3[0])), W4_center=str(mp.re(c4[0])),
           F=[str(mp.re(x)) for x in Fk], imag=[mp.nstr(mp.im(x), 3) for x in (L2, K2, Z2)],
           residuals={k: mp.nstr(mp.re(v), 3) for k, v in res.items()})
json.dump(rec, open(sys.argv[4], 'w'), indent=1)
print(json.dumps(rec, indent=1))
