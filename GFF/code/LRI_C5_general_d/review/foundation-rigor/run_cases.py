#!/usr/bin/env python3
"""Review check C driver (foundation-rigor).  For each case:
  * brute-force double-precision lattice sums (brute_xi.py) at (L,N) and (L/2,N/2): modes, reflection,
    boundary modes (Theorem 4), top mode (Theorem 6), W_r from the residue functional (Prop. 9);
  * reference W_r from spectral.py (independent Barnes/Mellin evaluation) and from the finite-sample code
    wheel_general_b.W (Horn blocks), both at 20 digits;
  * block decomposition (Prop. 10): Wheel.Xi(t) (five blocks) vs brute-force Xi(t) at one node.
Writes results/cases.json.  Usage: python3 run_cases.py [ncpu]"""
import sys
import json
import time
import multiprocessing as mpc
import numpy as np

sys.path.insert(0, '.')
from brute_xi import Brute, summarize

CASES = [
    # (tag, r, d, b, L, N, gprime)
    ('d3.5_b0.2_r4', 4, 3.5, 0.2, 1000, 600, None),
    ('d3.5_b0.2_r3', 3, 3.5, 0.2, 2000, 1000, None),
    ('d3.5_b0.2_r5', 5, 3.5, 0.2, 1000, 600, None),
    ('d3.5_b0.2_r6', 6, 3.5, 0.2, 1000, 600, None),
    ('d3.5_b0.2_r2', 2, 3.5, 0.2, 4000, 2000, None),
    ('d3.5_bc_r4', 4, 3.5, 0.3 + 0.25j, 1000, 600, None),
    ('d3.5_b1.75_r4', 4, 3.5, 1.75, 4000, 3000, None),
    ('d3.5_b1.75_r3', 3, 3.5, 1.75, 4000, 4000, None),
    ('d0.9_b0.1_r4', 4, 0.9, 0.1, 4000, 3000, None),
    ('d0.9_b0.45_r4', 4, 0.9, 0.45, 4000, 4000, None),
    ('d0.9_b0.1_r5', 5, 0.9, 0.1, 4000, 3000, None),
    ('d1.5_b0.75_r3', 3, 1.5, 0.75, 4000, 4000, None),
    ('d2.5_b1.6_r4', 4, 2.5, 1.6, 4000, 4000, None),
    ('d2.75_bc_r3', 3, 2.75, 0.5 + 0.4j, 4000, 3000, None),
    ('d3.9_b1.95_r4', 4, 3.9, 1.95, 4000, 3000, None),
    ('d3.9_b2.3_r4', 4, 3.9, 2.3, 4000, 3000, None),
    ('UNBAL_d1_b0.4_r4_g0.25', 4, 1.0, 0.4, 400, 40000, 0.25),
    ('UNBAL_d3.5_b0.2_r4_g1.75', 4, 3.5, 0.2, 1000, 600, 1.75),
    ('UNBAL_d1.5_b0.5_r3_g0.7', 3, 1.5, 0.5, 4000, 3000, 0.7),
]


def brute_case(c):
    tag, r, d, b, L, N, gp = c
    out = dict(tag=tag, r=r, d=d, b=[complex(b).real, complex(b).imag], L=L, N=N, gprime=gp)
    t0 = time.time()
    for lab, (LL, NN) in (('full', (L, N)), ('half', (L // 2, N // 2))):
        B = Brute(r, d, b, LL, NN, gp)
        gam, X, ts = B.modes()
        s = summarize(r, gam, B.sig)
        s['gamma'] = {str(m): [gam[m].real, gam[m].imag] for m in gam}
        s['max_outer_tail'] = float(max(B.tails))
        if gp is None:
            W = B.W_from_modes(gam)
            s['W'] = [W.real, W.imag]
        s['Xi_node0'] = [X[0].real, X[0].imag]
        s['node0'] = [ts[0].real, ts[0].imag]
        out[lab] = s
    out['time_brute'] = time.time() - t0
    return out


def ref_case(c):
    tag, r, d, b, L, N, gp = c
    out = dict(tag=tag)
    if gp is not None:
        return out
    import mpmath as mp
    import wheel_general_b as wg
    import spectral as sp
    t0 = time.time()
    bc = complex(b)
    dd = mp.mpf(str(d)) if d != int(d) else int(d)
    try:
        mp.mp.dps = 30
        bb = mp.mpc(str(bc.real), str(bc.imag)) if bc.imag else mp.mpf(str(bc.real))
        val = sp.W_spectral(r, dd, bb)
        out['W_spectral'] = [float(mp.re(val)), float(mp.im(val))]
    except Exception as e:
        out['W_spectral_err'] = repr(e)
    out['time_spectral'] = time.time() - t0
    t0 = time.time()
    try:
        mp.mp.dps = 20
        bb = mp.mpc(str(bc.real), str(bc.imag)) if bc.imag else mp.mpf(str(bc.real))
        val = wg.W(r, dd, bb, dps=20)
        out['W_finite'] = [float(mp.re(val)), float(mp.im(val))]
        with mp.workdps(35):
            w = wg.Wheel(r, dd, bb)
            t = mp.mpc('0.0137', '0.06')
            xi = w.Xi(t)
        out['Xi_blocks_node0'] = [float(mp.re(xi)), float(mp.im(xi))]
    except Exception as e:
        out['W_finite_err'] = repr(e)
    out['time_finite'] = time.time() - t0
    return out


if __name__ == '__main__':
    ncpu = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    with mpc.Pool(ncpu) as pool:
        rb = pool.map_async(brute_case, CASES, chunksize=1)
        rr = pool.map_async(ref_case, CASES, chunksize=1)
        res_b = rb.get()
        res_r = rr.get()
    merged = []
    for a, b in zip(res_b, res_r):
        a.update(b)
        merged.append(a)
    json.dump(merged, open('results/cases.json', 'w'), indent=1)
    for m in merged:
        f, h = m['full'], m['half']
        line = '%-26s top=%.1e (half %.1e) bnd=%.1e refl=%.1e tail=%.1e' % (
            m['tag'], f['top'], h['top'], f['boundary'], f['refl'], f['max_outer_tail'])
        if 'W' in f:
            W = complex(*f['W'])
            Wh = complex(*h['W'])
            line += ' W=%.12g dW(half)=%.1e' % (W.real, abs(W - Wh) / abs(W))
            for k in ('W_spectral', 'W_finite'):
                if k in m:
                    ref = complex(*m[k])
                    line += ' vs %s %.1e' % (k[2:], abs(W - ref) / abs(ref))
            if 'Xi_blocks_node0' in m:
                xb = complex(*m['Xi_blocks_node0'])
                xr = complex(*f['Xi_node0'])
                line += ' Xi(blocks vs brute) %.1e' % (abs(xb - xr) / abs(xb))
        print(line, flush=True)
