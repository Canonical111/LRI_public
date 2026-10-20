#!/usr/bin/env python3
"""Block-level checks of the two-node data (R, Mh and the zero mode c0hat) against exact or independent values.

 d = 1 :  R(1;b) = 3F2(b,b,b;1,1;1) = Gamma(1+b/2)Gamma(1-3b/2)/(Gamma(1+b)Gamma(1-b/2)^2 Gamma(1-b))   (Dixon; derived)
          c0hat(1;b) = 0 identically (parity, foundation Remark 8)
 d = 2 :  Mh(2;b) = 0 identically;  R(2;b) = sin^2(pi b/2) W3(2;b)/(2 pi^2 (1+2cos(pi b/2))),
          W3(2;b) = gamma_C(b/4)^3/(2 gamma_C(3b/4))  (note gs:W3d2)
 d = 3 :  R(3;b) = S(b) of LRI_C5_d3/wf_Z3 (independent code): S(3/2) = H3(0), S'(3/2), S''(3/2) (250 digits);
          c0hat(3;b) = N_b^3 * (-pi^5 Gamma(3g-2)/Gamma(g)^9), g = (3-b)/2  (C63d, c0 = -a3 b3)
 all d:   u, v and their b-derivatives (closed forms in z_blocks.uv_jets) against numerical differentiation of uv(b).
usage: check_blocks.py results/zj60.json
"""
import json
import os
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import z_blocks as zb  # noqa: E402


def jets_of(f, b0, n=2):
    return [f(b0)] + [mp.diff(f, b0, k) for k in range(1, n + 1)]


def rel(a, b):
    return abs(a - b) / max(abs(b), mp.mpf(10) ** (-mp.mp.dps))


def c0hat_jets(d, Rj, Mj):
    """jets of c0hat = kM(b) Mh + kR(b) R at b = d/2."""
    pi = mp.pi

    def kM(b):
        cg = mp.cos(pi * b / 2)
        return cg * (1 + cg) ** 2 / 8

    def kR(b):
        sg, cg = mp.sin(pi * b / 2), mp.cos(pi * b / 2)
        return -pi ** 3 * sg ** 3 / (1 + cg)
    b0 = mp.mpf(d) / 2
    a, c = jets_of(kM, b0), jets_of(kR, b0)
    return [a[0] * Mj[0] + c[0] * Rj[0],
            a[1] * Mj[0] + a[0] * Mj[1] + c[1] * Rj[0] + c[0] * Rj[1],
            a[2] * Mj[0] + 2 * a[1] * Mj[1] + a[0] * Mj[2] + c[2] * Rj[0] + 2 * c[1] * Rj[1] + c[0] * Rj[2]]


def main(fn):
    res = json.load(open(fn))
    mp.mp.dps = int(res['dps']) + 20
    out = {}
    R = {d: [mp.mpmathify(x) for x in r['R']] for d, r in res['results'].items()}
    M = {d: [mp.mpmathify(x) for x in r['Mh']] for d, r in res['results'].items()}
    lines = []
    if '1' in R:
        dix = lambda b: mp.gamma(1 + b / 2) * mp.gamma(1 - 3 * b / 2) * mp.rgamma(1 + b) * mp.rgamma(1 - b / 2) ** 2 \
            * mp.rgamma(1 - b)
        ex = jets_of(dix, mp.mpf(1) / 2)
        e = [rel(R['1'][k], ex[k]) for k in range(3)]
        c0 = c0hat_jets(1, R['1'], M['1'])
        lines.append('d=1: R^(k)(1/2) vs Dixon closed form: rel err %s' % [mp.nstr(x, 3) for x in e])
        lines.append('d=1: c0hat^(k)(1/2) (must vanish; scale |R| pi^3 s^3 ~ %s): %s' % (
            mp.nstr(abs(R['1'][0]) * mp.pi ** 3 / 2 ** 1.5, 4), [mp.nstr(abs(x), 3) for x in c0]))
        H = 2 * mp.pi ** 2 / 3 + 8 * mp.catalan
        lines.append('d=1: R\'/R - pi = %s ;  R\'\'/R - 3H = %s' % (
            mp.nstr(abs(R['1'][1] / R['1'][0] - mp.pi), 3), mp.nstr(abs(R['1'][2] / R['1'][0] - 3 * H), 3)))
        out['d1'] = dict(R_vs_Dixon=[mp.nstr(x, 3) for x in e], c0hat=[mp.nstr(abs(x), 3) for x in c0])
    if '2' in R:
        gC = lambda x: mp.gamma(x) * mp.rgamma(1 - x)
        Rc = lambda b: mp.sin(mp.pi * b / 2) ** 2 * gC(b / 4) ** 3 / (2 * gC(3 * b / 4)) / (
            2 * mp.pi ** 2 * (1 + 2 * mp.cos(mp.pi * b / 2)))
        ex = jets_of(Rc, mp.mpf(1))
        e = [rel(R['2'][k], ex[k]) for k in range(3)]
        lines.append('d=2: R^(k)(1) vs Selberg closed form: rel err %s' % [mp.nstr(x, 3) for x in e])
        lines.append('d=2: Mh^(k)(1) (must vanish; scale |MC| ~ %s): %s' % (
            mp.nstr(abs(mp.mpmathify(res['results']['2']['blocks']['MC'][0])), 4), [mp.nstr(abs(x), 3) for x in M['2']]))
        out['d2'] = dict(R_vs_Selberg=[mp.nstr(x, 3) for x in e], Mh=[mp.nstr(abs(x), 3) for x in M['2']])
    if '3' in R:
        z3 = json.load(open(os.path.join(HERE, '..', '..', 'LRI_C5_d3', 'wf_Z3', 'Z3_values.json')))['values']
        ex = [mp.mpf(z3['H3_0']), mp.mpf(z3['S1']), mp.mpf(z3['S2'])]
        e = [rel(R['3'][k], ex[k]) for k in range(3)]
        lines.append('d=3: R^(k)(3/2) vs C63d S(3/2)=H3(0), S\', S\'\' (independent code): rel err %s' % [
            mp.nstr(x, 3) for x in e])

        def c0c(b):
            g = (3 - b) / 2
            Nb = mp.gamma(mp.mpf(3) / 2) * mp.gamma(g) * mp.rgamma(b / 2)
            return -Nb ** 3 * mp.pi ** 5 * mp.gamma(3 * g - 2) * mp.rgamma(g) ** 9
        exc = jets_of(c0c, mp.mpf(3) / 2)
        c0 = c0hat_jets(3, R['3'], M['3'])
        e2 = [rel(c0[k], exc[k]) for k in range(3)]
        lines.append('d=3: c0hat^(k)(3/2) vs -N^3 pi^5 Gamma(3g-2)/Gamma(g)^9: rel err %s' % [mp.nstr(x, 3) for x in e2])
        out['d3'] = dict(R_vs_S=[mp.nstr(x, 3) for x in e], c0hat_vs_gamma=[mp.nstr(x, 3) for x in e2])
    # coefficient jets
    worst = mp.mpf(0)
    for d in R:
        q = mp.mpf(zb_parse(d)) / 4
        uj, vj = zb.uv_jets(q)
        un = jets_of(lambda b: zb.uv(b)[0], 2 * q)
        vn = jets_of(lambda b: zb.uv(b)[1], 2 * q)
        worst = max(worst, max(rel(uj[k], un[k]) for k in range(3)), max(rel(vj[k], vn[k]) for k in range(3)))
    lines.append('u, v jets closed forms vs numerical differentiation, worst rel err over all d: %s' % mp.nstr(worst, 3))
    out['uv_worst'] = mp.nstr(worst, 3)
    print('\n'.join(lines))
    return out


def zb_parse(d):
    if '/' in d:
        a, b = d.split('/')
        return mp.mpf(int(a)) / int(b)
    return mp.mpf(d)


if __name__ == '__main__':
    o = main(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(o, open(sys.argv[2], 'w'), indent=1)
