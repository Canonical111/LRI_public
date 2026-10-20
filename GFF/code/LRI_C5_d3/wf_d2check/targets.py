#!/usr/bin/env python3
"""Exact-form targets at d=2, computed independently of C62d's code.
F+- (4F3 at 1) by direct partial sum + Stirling-Hurwitz tail (same asymptotic machinery, x = n).
B- = Gamma(1/4)^4 F-,  B+ = 64 pi^4 F+/Gamma(1/4)^4,  P4(2) = (B-^2 - B+^2)/(4 pi^3)  (note fp:P4two),
Q2 = Gamma(1/4)^8/(24 pi^4),  claimed L2 = -2 log2 P4(2),  claimed K2 = 32 G^2 - 28 zeta3 log2,  Z2 = 4 G Q2 (proved).
usage: targets.py DPS N K OUT.json"""
import sys, json
import mpmath as mp
DPS, N, K = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
mp.mp.dps = DPS + 15
sys.path.insert(0, __import__('os').path.dirname(__file__))
from hp_masters_d2 import stirling_series

def f43(u, v):
    """4F3(u,u,1/2,1/2; v,v,1; 1) = C sum_n [G(n+u)/G(n+v)]^2 [G(n+1/2)/G(n+1)]^2, C = (G(v)/G(u))^2/pi."""
    C = (mp.gamma(v) / mp.gamma(u)) ** 2 / mp.pi
    t = mp.mpf(1); s = mp.mpf(0)
    for n in range(N):
        s += t
        t *= ((n + u) / (n + v)) ** 2 * ((n + mp.mpf(1) / 2) / (n + 1)) ** 2
    fac = [(u, v, 2), (mp.mpf(1) / 2, mp.mpf(1), 2)]
    P, E = stirling_series(fac, K)
    tl = C * mp.fsum(E[k] * mp.zeta(P + k, N) for k in range(K + 1))
    return s + tl, abs(C * E[K] * mp.zeta(P + K, N))

Fm, em = f43(mp.mpf(1) / 4, mp.mpf(3) / 4)
Fp, ep = f43(mp.mpf(3) / 4, mp.mpf(5) / 4)
g4 = mp.gamma(mp.mpf(1) / 4)
Bm, Bp = g4 ** 4 * Fm, 64 * mp.pi ** 4 / g4 ** 4 * Fp
P4 = (Bm ** 2 - Bp ** 2) / (4 * mp.pi ** 3)
Q2 = g4 ** 8 / (24 * mp.pi ** 4)
G, z3, l2 = mp.catalan, mp.zeta(3), mp.log(2)
rec = dict(dps=DPS, N=N, K=K, last_tail_term=[mp.nstr(em, 3), mp.nstr(ep, 3)],
           Fm=mp.nstr(Fm, DPS), Fp=mp.nstr(Fp, DPS), Bm=mp.nstr(Bm, DPS), Bp=mp.nstr(Bp, DPS),
           P4=mp.nstr(P4, DPS), Q2=mp.nstr(Q2, DPS), W3=mp.nstr(3 * Q2, DPS),
           L2_claim=mp.nstr(-2 * l2 * P4, DPS), K2_claim=mp.nstr(32 * G ** 2 - 28 * z3 * l2, DPS), Z2=mp.nstr(4 * G * Q2, DPS))
json.dump(rec, open(sys.argv[4], 'w'), indent=1)
print(json.dumps(rec, indent=1))
