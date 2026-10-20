#!/usr/bin/env python3
"""spectral <t_l^2 R_tau>_d (real tau, convergent) with the frozen copy of C63d's hp_general_d.py"""
import sys, time
import mpmath as mp
import hp_general_d_copy as hp

def tR_spec(d, tau, L=24, K=30):
    q = d / 4
    a, bb = q / 2, 3 * q / 2
    t2 = [(a, bb, 2)]
    pref = mp.gamma(2 * q) ** 2
    Rx, Rxb = t2 + [(a, a + tau, 1)], t2 + [(bb - tau, bb, 1)]
    br = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, 40, mp.inf]
    return hp.spectral(pref, Rx, Rxb, L, K, d, br)

if __name__ == '__main__':
    mp.mp.dps = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    d = mp.mpf(sys.argv[1]); tau = mp.mpf(sys.argv[2])
    for L, K in ((16, 24), (24, 30)):
        st = time.time()
        v = tR_spec(d, tau, L, K)
        print('spectral d', d, 'tau', tau, 'L', L, 'K', K, mp.nstr(v, 25), '%.0fs' % (time.time() - st), flush=True)
