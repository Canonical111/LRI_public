#!/usr/bin/env python3
"""Compare the five-Horn values of P4(d), L_d (and the r=3 by-product 3Q_d, dW_3/db) with references (session L).

References:
  d=1: proved closed forms, P4 = 13B_- - 3B_+, L = -((3A-D)/6)P4 - (2D/3)B_- (eq:KLpsiReflected), 3Q_1 = 3Gamma(1/4)^4/pi
  d=2: P4(2) = (B_-^2 - B_+^2)/(4 pi^3) (fp:P4two), L_2 = -2 log2 P4(2) (gc:L2closed, proved),
       W_3(2;b) = gamma_C(b/4)^3/(2 gamma_C(3b/4)) (gs:W3d2), W_4(2;b)/W_4(2;2-b) = 2^(4-4b) gamma_C(b/2)^2/gamma_C(b-1/2)
       (gc:L2second, proved)
  d=3: LRI_C5_d3 values (L3, P4(3) to ~160 digits, Q3 to ~100 digits)
  d noninteger: C63d spectral references (LRI_C5_general_d/references/reference_values.json), independent code
usage: analyze.py results/val50.json [results/val70.json ...]
"""
import sys
import os
import json
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from hypsums_jet import GammaSeq, single_sum  # noqa: E402

mp.mp.dps = 120


def d1_refs():
    q = mp.mpf(1) / 4
    with mp.workdps(130):
        Fm = single_sum(GammaSeq([(q, mp.mpf(3) / 4, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 200, 140)
        Fp = single_sum(GammaSeq([(mp.mpf(3) / 4, mp.mpf(5) / 4, 2), (mp.mpf(1) / 2, 1, 2)]), 0, 200, 140)
        Bm = mp.re(mp.gamma(q) ** 4 * Fm)
        Bp = mp.re(64 * mp.pi ** 4 / mp.gamma(q) ** 4 * Fp)
        P4 = 13 * Bm - 3 * Bp
        A = mp.psi(0, mp.mpf(1) / 2) + mp.psi(0, 1) - 2 * mp.psi(0, q)
        L = -(3 * A - mp.pi) / 6 * P4 - 2 * mp.pi / 3 * Bm
        P4_2 = (Bm ** 2 - Bp ** 2) / (4 * mp.pi ** 3)
    return dict(P4=P4, L=L, threeQ=3 * mp.gamma(q) ** 4 / mp.pi), dict(P4=P4_2, L=-2 * mp.log(2) * P4_2,
                                                                       threeQ=(mp.gamma(q) / mp.gamma(3 * q)) ** 4 / 2)


def gC(z):
    return mp.gamma(z) / mp.gamma(1 - z)


def refs():
    R = {}
    R['1'], R['2'] = d1_refs()
    v3 = json.load(open(os.path.join(HERE, '../../LRI_C5_d3/wf_L3/L3_final_values.json')))['values']
    z3 = json.load(open(os.path.join(HERE, '../../LRI_C5_d3/wf_Z3/Z3_values.json')))['values']
    R['3'] = dict(P4=mp.mpf(v3['P4']), L=mp.mpf(v3['L3']), threeQ=3 * mp.mpf(z3['Q3']))
    rv = json.load(open(os.path.join(HERE, '../references/reference_values.json')))['values']
    import glob
    for fn in sorted(glob.glob(os.path.join(HERE, 'results', 'ref_d*.json'))):
        c = json.load(open(fn))      # session-L runs of C63d's spectral code (refcheck_r4.py), r = 4 only
        R[c['d']] = dict(P4=mp.mpf(c['P4']), L=mp.mpf(c['L']), threeQ=None, source='refcheck_r4 dps %d' % c['dps'])
    for k, v in rv.items():
        dstr = k.split('=')[1]
        R[dstr] = dict(P4=mp.mpf(v['P4']['value']), L=mp.mpf(v['L']['value']), threeQ=mp.mpf(v['threeQ']['value']),
                       digits=dict(P4=v['P4']['digits'], L=v['L']['digits'], threeQ=v['threeQ']['digits']),
                       offdiag={o['b']: (mp.mpf(o['W3']), mp.mpf(o['W4'])) for o in v['offdiag']})
    return R


def rel(a, b):
    a, b = mp.mpf(a), mp.mpf(b)
    return abs(a - b) / abs(b)


def main(files):
    R = refs()
    rows = []
    for fn in files:
        res = json.load(open(fn))
        dps = res['dps']
        rr = res['results']
        ds = sorted({k.split('_d')[1].split('_')[0] for k in rr}, key=lambda z: float(mp.mpmathify(z)))
        print('==== %s (dps %d, %.0f s wall)' % (os.path.basename(fn), dps, res['seconds']))
        for dstr in ds:
            ref = R.get(dstr)
            c4 = rr.get('center_r4_d%s' % dstr)
            cv = rr.get('conv_r4_d%s' % dstr)
            c3 = rr.get('center_r3_d%s' % dstr)
            line = dict(d=dstr, dps=dps)
            line['P4'] = c4['W']
            line['L'] = c4['dW']
            line['conv_P4'] = rel(c4['W'], cv['W'])
            line['conv_L'] = rel(c4['dW'], cv['dW'])
            if ref:
                line['ref_P4'] = rel(c4['W'], ref['P4'])
                line['ref_L'] = rel(c4['dW'], ref['L'])
                if c3 and ref.get('threeQ') is not None:
                    line['ref_3Q'] = rel(c3['W'], ref['threeQ'])
            if c3:
                line['dW3'] = abs(mp.mpf(c3['dW'])) / mp.mpf(c3['W'])
                line['refdigits'] = ref.get('digits')
            # off-diagonal
            od = {}
            for k, o in rr.items():
                if k.startswith('offdiag_') and ('_d%s_' % dstr) in k:
                    r = int(k.split('_r')[1][0])
                    bstr = k.split('_b')[1]
                    od.setdefault(bstr, {})[r] = mp.mpf(o['W'])
            ods = []
            for bstr, wv in sorted(od.items()):
                bb = mp.mpf(bstr)
                ent = dict(b=bstr)
                if ref and 'offdiag' in ref and bstr in ref['offdiag']:
                    W3r, W4r = ref['offdiag'][bstr]
                    ent['W4_vs_C63d'] = rel(wv[4], W4r)
                    ent['W3_vs_C63d'] = rel(wv[3], W3r)
                if dstr == '2':
                    ent['W3_vs_exact'] = rel(wv[3], gC(bb / 4) ** 3 / (2 * gC(3 * bb / 4)))
                ods.append(ent)
            if dstr == '2' and '1.05' in od and '0.95' in od:
                bb = mp.mpf('1.05')
                ratio = od['1.05'][4] / od['0.95'][4]
                exact = 2 ** (4 - 4 * bb) * gC(bb / 2) ** 2 / gC(bb - mp.mpf(1) / 2)
                line['W4_reflection_d2'] = rel(ratio, exact)
            line['offdiag'] = ods
            rows.append(line)
            def f(x):
                return mp.nstr(x, 2) if x is not None else '-'
            print('d=%-5s P4 ref %-8s conv %-8s | L ref %-8s conv %-8s | 3Q ref %-8s dW3/W3 %-8s %s' % (
                dstr, f(line.get('ref_P4')), f(line['conv_P4']), f(line.get('ref_L')), f(line['conv_L']),
                f(line.get('ref_3Q')), f(line.get('dW3')), ('refdig ' + str(line['refdigits'])) if line.get('refdigits') else ''))
            for ent in ods:
                print('        b=%-6s ' % ent['b'] + '  '.join('%s %s' % (k, mp.nstr(v, 2)) for k, v in ent.items() if k != 'b'))
            if 'W4_reflection_d2' in line:
                print('        d=2 rim-spoke reflection W4(2;1.05)/W4(2;0.95): rel dev', mp.nstr(line['W4_reflection_d2'], 2))
    return rows


if __name__ == '__main__':
    rows = main(sys.argv[1:])
    out = os.path.join(HERE, 'results', 'analysis.json')
    def conv_(x):
        if isinstance(x, mp.mpf):
            return mp.nstr(x, 3)
        if isinstance(x, dict):
            return {k: conv_(v) for k, v in x.items()}
        if isinstance(x, list):
            return [conv_(v) for v in x]
        return x
    json.dump(conv_(rows), open(out, 'w'), indent=1)
    print('wrote', out)
