#!/usr/bin/env python3
"""Repair round 2 of the joint-review fixes (finding on gdk:special): print r3(1), r3(2), r3(3) of gdk:special to
34 significant digits, as in the values table of gdk:numerics, and check that the strings typeset there are the
correctly rounded values of the formulas typeset in gdk:special:
  r3(1) = s3(1) + 4K - 2(pi^3+28zeta(3))(3gamma_E+7log2+pi),  K = eq:KprovedFinal = 128G^2+24pi^2G-4pi^3log2-28(pi+4log2)zeta(3)
  r3(2) = s3(2) + 128G^2 - 168zeta(3)log2 - 42gamma_E zeta(3)
  r3(3) = s3(3) + 4[K_3 - (U/8)(psi(1)+psi(2q)+4psi(q))] with the 430-digit K_3 of LRI_C5_d3/wf_K3/K3_value.json.
Also: the d = 1 prefactor identity (U/8)[psi(1)+psi(1/2)+4psi(1/4)] = (1/2)(pi^3+28zeta(3))(3gamma_E+7log2+pi), the
two closed forms of K at d = 1, 2 against the 100-digit position-space values, and each r3 against the r3 from the
100-digit MB K_d.  s3 is the Bell polynomial of gdk:sk.  mpmath only, 120 digits.
usage: python3 check_r3_special.py"""
import json, os
import mpmath as mp

mp.mp.dps = 120
HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.abspath(os.path.join(HERE, '..', '..'))
mb = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']
K3 = mp.mpf(json.load(open(os.path.join(KG, '..', '..', 'LRI_C5_d3', 'wf_K3', 'K3_value.json')))['K3'])

# strings to be typeset in gdk:special (34 significant digits, as in the values table)
typeset = {'1': '767.2452094446567860904798157376224', '2': '35.63714944308140680727039972168179',
           '3': '4.511759358236005780256620897961575'}


def xh(q, h):
    return mp.polygamma(h - 1, 1) - (-1) ** h * mp.polygamma(h - 1, 2 * q) - (2 ** (3 - h) * mp.polygamma(h - 1, q) if h % 2 else 0)


def s3(q):
    x1, x2, x3, x4 = (xh(q, h) for h in (1, 2, 3, 4))
    return (x1 ** 4 + 6 * x1 ** 2 * x2 + 4 * x1 * x3 + 3 * x2 ** 2 + x4) / 24


def pref(q):
    return mp.polygamma(2, q) / 8 * (mp.digamma(1) + mp.digamma(2 * q) + 4 * mp.digamma(q))


def rnd(x, n=34):
    return mp.nstr(x, n, min_fixed=-mp.inf, max_fixed=mp.inf, strip_zeros=False)


G, z3, gE, l2, pi = mp.catalan, mp.zeta(3), mp.euler, mp.log(2), mp.pi
K1 = 128 * G ** 2 + 24 * pi ** 2 * G - 4 * pi ** 3 * l2 - 28 * (pi + 4 * l2) * z3
K2 = 32 * G ** 2 - 28 * z3 * l2
print('K(1) eq:KprovedFinal vs MB: %s;  K(2) gc:K2closed vs MB: %s;  K3 (430 digits) vs MB: %s' % (
    mp.nstr((K1 - mp.mpf(mb['1']['K'])) / K1, 3), mp.nstr((K2 - mp.mpf(mb['2']['K'])) / K2, 3),
    mp.nstr((K3 - mp.mpf(mb['3']['K'])) / K3, 3)))
q = mp.mpf(1) / 4
print('d=1 prefactor identity: %s' % mp.nstr(pref(q) - (pi ** 3 + 28 * z3) * (3 * gE + 7 * l2 + pi) / 2, 3))

r3 = {'1': s3(mp.mpf(1) / 4) + 4 * K1 - 2 * (pi ** 3 + 28 * z3) * (3 * gE + 7 * l2 + pi),
      '2': s3(mp.mpf(1) / 2) + 128 * G ** 2 - 168 * z3 * l2 - 42 * gE * z3,
      '3': s3(mp.mpf(3) / 4) + 4 * (K3 - pref(mp.mpf(3) / 4))}
ok = True
for d in ('1', '2', '3'):
    qd = mp.mpf(d) / 4
    r3mb = s3(qd) + 4 * (mp.mpf(mb[d]['K']) - pref(qd))
    ulp = mp.mpf(10) ** (mp.floor(mp.log10(abs(r3[d]))) - 33)
    err = abs(mp.mpf(typeset[d]) - r3[d]) / ulp
    match = rnd(r3[d]) == typeset[d]
    ok = ok and match and err <= mp.mpf('0.5')
    print('d=%s  r3 (formula of gdk:special) = %s' % (d, mp.nstr(r3[d], 45)))
    print('      rounded to 34 digits %s  typeset %s  match=%s  |typeset - r3| = %.3f ulp  r3(MB K) - r3 = %s' % (
        rnd(r3[d]), typeset[d], match, float(err), mp.nstr(r3mb - r3[d], 3)))
print('ALL OK' if ok else 'MISMATCH')
