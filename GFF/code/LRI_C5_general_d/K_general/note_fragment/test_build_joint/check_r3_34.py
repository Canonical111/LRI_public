#!/usr/bin/env python3
"""Joint-review fix K6: recompute the r3 column of gdk:numerics to 34 significant digits from the 100-digit
Mellin--Barnes K_d (position_space/K_d_values_mb_D100.json) through the boxed gdk:Kr3, check correct rounding,
check that the printed 34-digit r3 reproduces the printed 32-digit K column through gdk:Kr3, and check s3 of gdk:sk
against a direct Taylor expansion of the closed form gdk:Sclosed.  mpmath only (no Hurwitz zeta at complex s).
usage: python3 check_r3_34.py"""
import json, os
import mpmath as mp

mp.mp.dps = 110
HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.abspath(os.path.join(HERE, '..', '..'))
mb = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']

# the 34-digit values proposed in JOINT_REVIEW.md K6 and the 32-digit K column as printed in the fragment
proposed = {'0.8': '1894.360867513991151448939858484147', '1': '767.2452094446567860904798157376224',
            '1.25': '302.1379775430212297584696879029900', '1.5': '136.5685443212260369206603722998423',
            '2': '35.63714944308140680727039972168179', '2.5': '11.46731776044183878576775168950130',
            '2.75': '6.984719816576732523926795215898772', '3': '4.511759358236005780256620897961575'}
Kprinted = {'0.8': '92.372770239922771632645391899036', '1': '39.331569128259039057503187151598',
            '1.25': '17.203345729921688327085720106549', '1.5': '9.0182974015948205470847431046793',
            '2': '3.5181091385902522416490901703077', '2.5': '1.8405012954285880307301818602723',
            '2.75': '1.4292491886603120000991755368839', '3': '1.1485946495271793365566463108107'}


def xh(q, h):
    return mp.polygamma(h - 1, 1) - (-1) ** h * mp.polygamma(h - 1, 2 * q) - (2 ** (3 - h) * mp.polygamma(h - 1, q) if h % 2 else 0)


def s3_bell(q):
    x1, x2, x3, x4 = (xh(q, h) for h in (1, 2, 3, 4))
    return (x1 ** 4 + 6 * x1 ** 2 * x2 + 4 * x1 * x3 + 3 * x2 ** 2 + x4) / 24


def s3_taylor(q):
    # tau <t^2 S_tau> = tau Gamma(2q) Gamma(tau) Gamma(q-tau/2)^4 / (Gamma(2q-tau) Gamma(q+tau/2)^4); s3 = [tau^4]
    f = lambda t: mp.gamma(2 * q) * mp.gamma(1 + t) * mp.gamma(q - t / 2) ** 4 / (mp.gamma(2 * q - t) * mp.gamma(q + t / 2) ** 4)
    return mp.taylor(f, 0, 4)[4]


def kr3_pref(q):
    return mp.polygamma(2, q) / 8 * (mp.digamma(1) + mp.digamma(2 * q) + 4 * mp.digamma(q))


def round_sig(x, n):
    return mp.nstr(x, n, min_fixed=-mp.inf, max_fixed=mp.inf, strip_zeros=False)


worst = 0
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    q = mp.mpf(dk) / 4
    K = mp.mpf(mb[dk]['K'])
    s3 = s3_bell(q)
    st = s3_taylor(q)
    r3 = s3 + 4 * (K - kr3_pref(q))
    r34 = round_sig(r3, 34)
    p = mp.mpf(proposed[dk])
    ulp = mp.mpf(10) ** (mp.floor(mp.log10(abs(r3))) - 33)
    err_ulp = abs(p - r3) / ulp
    Kback = kr3_pref(q) + (p - s3) / 4
    relK = abs(Kback - mp.mpf(Kprinted[dk])) / K
    relKmb = abs(Kback - K) / K
    worst = max(worst, relK)
    print('d=%-4s r3(34)=%s proposed=%s match=%s err=%.3f ulp | s3 Bell-Taylor %s | Kr3(printed r3) vs printed K %s, vs MB %s'
          % (dk, r34, proposed[dk], r34 == proposed[dk], float(err_ulp), mp.nstr(abs(s3 - st), 3), mp.nstr(relK, 3),
             mp.nstr(relKmb, 3)))
print('max relative deviation of Kr3(printed 34-digit r3) from the printed 32-digit K column:', mp.nstr(worst, 3))
