#!/usr/bin/env python3
"""Combine hp_part.py outputs (b-circle and tau-circle) into K3, L3, Z3.  usage: hp_combine.py B.json T.json OUT.json"""
import sys, json
import mpmath as mp
B, T = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
mp.mp.dps = max(B['dps'], T['dps']) + 10
def circle(d, idx):
    M = d['M']; half = M // 2
    v = {int(k): mp.mpmathify(x[idx].replace(' ', '')) for k, x in d['values'].items()}
    return [v[k] if k <= half else mp.conj(v[M - k]) for k in range(M)], mp.mpf(d['rho']), M
def coef(f, j, rho, M):
    return mp.fsum(f[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
W3, rb, Mb = circle(B, 0); W4, _, _ = circle(B, 1); F, rt, Mt = circle(T, 0)
L3 = coef(W4, 1, rb, Mb); Z3 = 2 * coef(W3, 2, rb, Mb) / 9
Fk = [coef(F, j, rt, Mt) for j in range(5)]
A = 2 + 4 * mp.log(2) - mp.pi; U = 2 * mp.pi ** 3 - 56 * mp.zeta(3); cs = mp.digamma(1) + mp.digamma(mp.mpf(3) / 2)
K3 = -A * U / 4 + (Fk[3] + cs * Fk[2]) / 4
rec = dict(dps=min(B['dps'], T['dps']), M=[Mb, Mt], rho=[str(rb), str(rt)], W3_center=str(coef(W3, 0, rb, Mb)), W4_center=str(coef(W4, 0, rb, Mb)),
           L3=str(L3), Z3=str(Z3), K3=str(K3), F=[str(x) for x in Fk], imag_parts=[str(mp.im(x)) for x in (L3, Z3, K3)])
json.dump(rec, open(sys.argv[3], 'w'), indent=1)
for k in ('W3_center', 'W4_center', 'L3', 'Z3', 'K3'): print(k, rec[k])
