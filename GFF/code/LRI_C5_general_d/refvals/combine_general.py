#!/usr/bin/env python3
"""Combine b-circle and tau-circle runs of hp_general_d.py at one d into P4, 3Q, L, Z, K (+ off-diagonal W3, W4)."""
import sys, json
import mpmath as mp
def load(f):
    return json.load(open(f))
def combine(fb, ft):
    B, T = load(fb), load(ft)
    mp.mp.dps = int(B['dps']) + 10
    d = mp.mpf(B['d']); q = d / 4
    def circ(D, idx):
        M = D['M']; h = M // 2
        v = {int(k): mp.mpmathify(x[idx].replace(' ', '')) for k, x in D['values'].items() if int(k) >= 0}
        return [v[k] if k <= h else mp.conj(v[M - k]) for k in range(M)], mp.mpf(D['rho']), M
    def coef(f, j, rho, M):
        return mp.fsum(f[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
    W3, rb, Mb = circ(B, 0); W4, _, _ = circ(B, 1); F, rt, Mt = circ(T, 0)
    A = mp.digamma(2 * q) + mp.digamma(1) - 2 * mp.digamma(q); U = mp.polygamma(2, q); cs = mp.digamma(1) + mp.digamma(2 * q)
    Fk = [coef(F, j, rt, Mt) for j in range(5)]
    r = dict(d=str(d), P4=coef(W4, 0, rb, Mb), threeQ=coef(W3, 0, rb, Mb), L=coef(W4, 1, rb, Mb), Z=2 * coef(W3, 2, rb, Mb) / 9,
             dW3db=coef(W3, 1, rb, Mb), K=-A * U / 4 + (Fk[3] + cs * Fk[2]) / 4, F0=Fk[0], F1=Fk[1])
    off = {k: v for k, v in B['values'].items() if int(k) < 0}
    return r, off
if __name__ == '__main__':
    r, off = combine(sys.argv[1], sys.argv[2])
    for k, v in r.items():
        print(k, v if isinstance(v, str) else mp.nstr(v, 30))
    for k, v in off.items():
        print('offdiag b =', v[2][:12], ' W3 =', v[0][:34], ' W4 =', v[1][:34])
