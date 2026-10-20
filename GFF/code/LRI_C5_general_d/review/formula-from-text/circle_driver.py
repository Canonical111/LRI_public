#!/usr/bin/env python3
"""Driver: samples on a Cauchy circle in b around b0=d/2, then the PRINTED formulas of general_d.tex.

usage: circle_driver.py d Mmax [N rho dropF1(0/1) direct(0/1)] -> JSON on stdout-file results/d<d>_M<Mmax>.json
"""
import sys
import json
import time
import mpmath as mp
from kron_samples import setprec, samples, W4_from, W3_from

KEYS = ['XT', 'X0', 'Xh', 'T3', 'M3', 'c0hat']


def s(v, n=60):
    v = mp.mpc(v)
    if abs(v.imag) <= mp.mpf(10) ** (-mp.mp.dps + 5) * max(1, abs(v.real)):
        return mp.nstr(v.real, n)
    return [mp.nstr(v.real, n), mp.nstr(v.imag, n)]


def printed(d, a):
    """Printed formulas gdr:P4, gdr:L, gdr:frozen, gdr:Q, gdr:Z from Taylor coefficients a[key][p]."""
    q = d / 4
    S = mp.sin(mp.pi * q)
    C = mp.cos(mp.pi * q)
    X0, Xh, XT = (a[k][0].real for k in ('X0', 'Xh', 'XT'))
    X0p, Xhp, XTp = (a[k][1].real for k in ('X0', 'Xh', 'XT'))
    P4 = 2 / (mp.pi * S ** 7) * ((1 + C) ** 2 * (1 + 2 * C) * X0 - (1 - C) ** 2 * (1 - 2 * C) * Xh - 2 * C * XT)
    DL = (1 + C) ** 2 * (1 + 2 * C) * X0p - (1 - C) ** 2 * (1 - 2 * C) * Xhp - 2 * C * XTp
    L = (-1 / S ** 8 * ((1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2) * X0 + (1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2) * Xh
                        - 2 * (1 + 6 * C ** 2) * XT) + 2 / (mp.pi * S ** 7) * DL)
    T3 = a['T3'][0].real
    T3pp = 2 * a['T3'][2].real
    c0 = a['c0hat'][0].real
    c0p = a['c0hat'][1].real
    c0pp = 2 * a['c0hat'][2].real
    threeQ = 6 * mp.pi ** 2 / S ** 2 * T3 + 4 / (mp.pi * S ** 3) * c0
    Q = threeQ / 3
    Z = (2 * mp.pi ** 2 / (3 * S ** 2) * T3pp - mp.pi ** 2 * mp.cos(mp.pi * d / 2) * Q / (6 * S ** 2)
         + (mp.pi * (1 + C ** 2) * c0 / S ** 5 - 4 * C * c0p / S ** 4 + 4 * c0pp / (mp.pi * S ** 3)) / 9)
    # u,v form of the second-derivative part (gdr:Z remark)
    M3pp = 2 * a['M3'][2].real
    u = 2 * mp.pi ** 2 * (1 + 2 * C) / S ** 2
    v = C * (1 + C) ** 2 / (2 * mp.pi * S ** 3)
    # C5 block in reduced form (gdr:C5reduced without P5, K and the pure-polygamma tail)
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    R = mp.psi(1, 2 * q) - mp.psi(1, 1)
    k0 = (1 + C) ** 2 * (768 * A * (1 + 2 * C) / (mp.pi * S ** 7) + 576 * (4 + 9 * C + 8 * C ** 2) / S ** 8)
    kh = (1 - C) ** 2 * (-768 * A * (1 - 2 * C) / (mp.pi * S ** 7) + 576 * (4 - 9 * C + 8 * C ** 2) / S ** 8)
    kT = -1536 * A * C / (mp.pi * S ** 7) - 1152 * (1 + 6 * C ** 2) / S ** 8
    Qc5 = 2 * mp.pi ** 2 / S ** 2 * T3 + 4 / (3 * mp.pi * S ** 3) * c0
    block_red = (-1728 * Qc5 ** 2 + (720 * A ** 2 + 1008 * R - 1192 * mp.pi ** 2 * mp.cos(mp.pi * d / 2) / S ** 2) * Qc5
                 + k0 * X0 + kh * Xh + kT * XT - 1152 / (mp.pi * S ** 7) * DL + 4768 * mp.pi ** 2 / S ** 2 * T3pp
                 + mp.mpf(2384) / 3 * (mp.pi * (1 + C ** 2) * c0 / S ** 5 - 4 * C * c0p / S ** 4
                                       + 4 * c0pp / (mp.pi * S ** 3)))
    return dict(P4=P4, L=L, DL=DL, threeQ=threeQ, Q=Q, Z=Z, uvpart=(u * T3pp + v * M3pp) / 9, A=A, R=R,
                block_red=block_red, Qc5=Qc5)


def run(d, Mmax, N=16, rho=mp.mpf('0.002'), dropF1=False, direct=True, offdiag=(), J=(10, 10)):
    b0 = d / 2
    vals = {}
    errs = {}
    t0 = time.time()
    for j in range(N // 2 + 1):
        bj = b0 + rho * mp.expjpi(2 * mp.mpf(j) / N)
        if j == 0 or j == N // 2:
            bj = mp.mpc(bj.real, 0)
        sm = samples(d, bj, Mmax, P=240, J=J, dropF1=dropF1)
        vals[j] = {k: sm[k] for k in KEYS}
        vals[j]['W4'] = W4_from(sm, bj)
        vals[j]['W3'] = W3_from(sm, bj)
        errs[j] = {k: sm['err'][k] for k in sm['err']}
        print('circle point', j, 'done', round(time.time() - t0, 1), 's', flush=True)
    for j in range(N // 2 + 1, N):
        vals[j] = {k: mp.conj(v) for k, v in vals[N - j].items()}
    a = {}
    for k in vals[0]:
        a[k] = []
        for p in range(4):
            acc = mp.mpc(0)
            for j in range(N):
                acc += vals[j][k] * mp.expjpi(-2 * mp.mpf(j * p) / N)
            a[k].append(acc / (N * rho ** p))
    out = dict(d=mp.nstr(d, 20), Mmax=Mmax, N=N, rho=mp.nstr(rho, 10), dropF1=dropF1,
               taylor={k: [s(v) for v in a[k]] for k in a},
               max_extrap_err={k: mp.nstr(max(errs[j].get(k, 0) for j in errs), 3) for k in errs[0]})
    pr = printed(d, a)
    out['printed'] = {k: s(v) for k, v in pr.items()}
    out['direct_from_W'] = dict(P4=s(a['W4'][0]), L=s(a['W4'][1]), threeQ=s(a['W3'][0]), dW3db=s(a['W3'][1]),
                                Z=s(2 * a['W3'][2] / 9))
    if direct:
        sm = samples(d, mp.mpc(b0, 0), Mmax, P=240, J=J, dropF1=dropF1)
        out['center_direct'] = {k: s(sm[k]) for k in KEYS}
        out['center_direct_err'] = {k: mp.nstr(v, 3) for k, v in sm['err'].items()}
        out['raw_center'] = {k: s(v) for k, v in list(sm['raw4'].items()) + list(sm['raw3'].items())}
    od = []
    for bstr in offdiag:
        bb = mp.mpf(bstr)
        sm = samples(d, mp.mpc(bb, 0), Mmax, P=240, J=J, dropF1=dropF1)
        od.append(dict(b=bstr, W3=s(W3_from(sm, bb)), W4=s(W4_from(sm, bb)),
                       err={k: mp.nstr(v, 3) for k, v in sm['err'].items()}))
    out['offdiag'] = od
    out['time_s'] = round(time.time() - t0, 1)
    return out


if __name__ == '__main__':
    setprec(260)
    dstr = sys.argv[1]
    Mmax = int(sys.argv[2])
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    rho = mp.mpf(sys.argv[4]) if len(sys.argv) > 4 else mp.mpf('0.002')
    dropF1 = bool(int(sys.argv[5])) if len(sys.argv) > 5 else False
    direct = bool(int(sys.argv[6])) if len(sys.argv) > 6 else True
    offdiag = sys.argv[7].split(',') if len(sys.argv) > 7 and sys.argv[7] else ()
    J = (int(sys.argv[8]), int(sys.argv[8])) if len(sys.argv) > 8 else (10, 10)
    d = mp.mpf(dstr)
    res = run(d, Mmax, N, rho, dropF1, direct, offdiag, J)
    fn = 'results/d%s_M%d_N%d_J%d.json' % (dstr, Mmax, N, J[0])
    import os
    os.makedirs('results', exist_ok=True)
    with open(fn, 'w') as f:
        json.dump(res, f, indent=1)
    print('wrote', fn, 'time', res['time_s'])
