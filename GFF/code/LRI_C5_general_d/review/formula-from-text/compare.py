#!/usr/bin/env python3
"""Compare the printed-formula values (from circle_driver results) with the independent references."""
import json
import glob
import sys
import mpmath as mp

mp.mp.dps = 60
REF = json.load(open('<PROJECT>/LRI_C5_general_d/references/reference_values.json'))['values']

G = mp.catalan
known = {}
# d = 2
P42 = mp.mpf('250.48731558186728553185175688791140716835571092358')
Q2 = mp.gamma(mp.mpf(1) / 4) ** 8 / (24 * mp.pi ** 4)
known['2'] = dict(P4=P42, L=-2 * mp.log(2) * P42, threeQ=3 * Q2, Z=4 * G * Q2)
# d = 3
known['3'] = dict(P4=mp.mpf('62.0583279434066724664633885840967'), L=mp.mpf('-62.710584968387669347296173433534847460'),
                  threeQ=3 * mp.mpf('5.01710256455385536959085484569018'),
                  Z=mp.mpf('8.82092489306009248553686732817408087436'))
# d = 1 (L_1 from lp:eq:MN with the elliptic integrals, computed in d1_known.py)
Q1 = mp.gamma(mp.mpf(1) / 4) ** 4 / mp.pi
known['1'] = dict(P4=mp.mpf('2229.5220610709419642945251997485'), L=mp.mpf('-5805.301629548802380141179877001378'),
                  threeQ=3 * Q1, Z=Q1 * (2 * mp.pi ** 2 / 3 + 8 * G))


def val(x):
    if isinstance(x, list):
        return mp.mpc(mp.mpf(x[0]), mp.mpf(x[1]))
    return mp.mpf(x)


def digits(a, b):
    a = val(a) if not isinstance(a, (mp.mpf, mp.mpc)) else a
    b = val(b) if not isinstance(b, (mp.mpf, mp.mpc)) else b
    if a == b:
        return 99, mp.mpf(0)
    rel = abs(a - b) / abs(b)
    return float(-mp.log10(rel)), rel


def refdict(dstr):
    if dstr in known:
        return {k: (v, 30) for k, v in known[dstr].items()}
    key = 'd=' + dstr
    if key not in REF:
        return {}
    r = REF[key]
    return {k: (mp.mpf(r[k]['value']), r[k]['digits']) for k in ('P4', 'threeQ', 'L', 'Z')}


files = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else 'results/d*_M*_N*_J*.json'))
for fn in files:
    res = json.load(open(fn))
    dstr = res['d']
    if dstr.endswith('.0'):
        dstr = dstr[:-2]
    refs = refdict(dstr)
    print('=' * 100)
    print(fn, ' time %.0fs' % res['time_s'], ' max extrapolation-spread:', res['max_extrap_err'])
    pr = res['printed']
    dw = res['direct_from_W']
    for k in ('P4', 'L', 'threeQ', 'Z'):
        line = '%-7s printed=%s' % (k, mp.nstr(val(pr[k]), 36))
        if k in refs:
            dg, rel = digits(pr[k], refs[k][0])
            line += '  vs ref: %5.1f digits (rel %s; ref has %s digits)' % (dg, mp.nstr(rel, 3), refs[k][1])
        dg2, rel2 = digits(pr[k], dw[k])
        line += '  | printed vs d/db W: %5.1f' % dg2
        print(line)
    print('dW3/db at b=d/2 (should vanish):', mp.nstr(abs(val(dw['dW3db'])), 3))
    if 'center_direct' in res:
        cd = res['center_direct']
        tay = res['taylor']
        worst = min(digits(tay[k][0], cd[k])[0] for k in cd if abs(val(cd[k])) > 1e-30)
        print('circle mean vs direct centre evaluation of the samples: worst %.1f digits' % worst)
    for od in res.get('offdiag', []):
        key = 'd=' + dstr
        if key in REF:
            for ro in REF[key]['offdiag']:
                if abs(mp.mpf(ro['b']) - mp.mpf(od['b'])) < 1e-12:
                    print('offdiag b=%s: W3 %.1f digits, W4 %.1f digits' % (
                        od['b'], digits(od['W3'], ro['W3'])[0], digits(od['W4'], ro['W4'])[0]))
    # C5 block: reduced (printed gdr:C5reduced, from samples) vs gs:C5 block from reference masters
    if all(k in refs for k in ('P4', 'L', 'threeQ', 'Z')):
        A = val(pr['A'])
        R = val(pr['R'])
        Q = refs['threeQ'][0] / 3
        block_ref = 384 * A * refs['P4'][0] - 576 * refs['L'][0] - 1728 * Q ** 2 + (720 * A ** 2 + 1008 * R) * Q \
            + 7152 * refs['Z'][0]
        dg, rel = digits(pr['block_red'], block_ref)
        print('C5 block (gdr:C5reduced from samples) vs gs:C5 block from reference masters: %.1f digits  [%s]' % (
            dg, mp.nstr(val(pr['block_red']), 30)))

# ---------------- pole-node check (gdr:taylorW / taylorQP and, by b-differentiation, gdr:taylorLZ)
for fn in sorted(glob.glob('results/pole_d*_M30000_N12.json')):
    r = json.load(open(fn))
    refs = refdict(r['d'])
    out = []
    for k, kk in (('P4', 'P4_pole'), ('L', 'L_pole'), ('threeQ', 'threeQ_pole'), ('Z', 'Z_pole')):
        out.append('%s %.1f' % (k, digits(r[kk], refs[k][0])[0]))
    print('pole-node d=%s (M=%d, N=%d): digits vs ref: %s; dW3/db=%s; max imag %s' % (
        r['d'], r['Mmax'], r['Nb'], ', '.join(out), r['dW3db_pole'], r['imag_max']))
