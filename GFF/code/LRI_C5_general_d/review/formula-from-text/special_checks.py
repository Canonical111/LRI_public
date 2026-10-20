#!/usr/bin/env python3
"""Checks of the printed integer-d specializations (gdr:special) against my own sample jets."""
import json
import glob
import mpmath as mp

mp.mp.dps = 50


def val(x):
    if isinstance(x, list):
        return mp.mpc(mp.mpf(x[0]), mp.mpf(x[1]))
    return mp.mpf(x)


def load(dstr, M=100000):
    fs = sorted(glob.glob('results/d%s_M%d_N16_J10.json' % (dstr, M)))
    return json.load(open(fs[0])) if fs else None


def dig(a, b):
    if b == 0:
        return float(-mp.log10(abs(a))) if a != 0 else 99.0
    return float(-mp.log10(abs(a - b) / abs(b))) if a != b else 99.0


G = mp.catalan
# ---------------- d = 1
r = load('1')
if r:
    t = r['taylor']
    print('d=1: c0hat jets (should vanish):', [mp.nstr(abs(val(v)), 3) for v in t['c0hat'][:3]])
    print('d=1: X0 - Xh jets (should vanish):', [mp.nstr(abs(val(t['X0'][p]) - val(t['Xh'][p])), 3) for p in range(3)])
    dixon = lambda be: (mp.gamma(1 + be / 2) * mp.gamma(1 - 3 * be / 2)
                        / (mp.gamma(1 + be) * mp.gamma(1 - be / 2) ** 2 * mp.gamma(1 - be)))
    b0 = mp.mpf(1) / 2
    print('d=1: T3 vs Dixon 3F2(b,b,b;1,1;1): %.1f digits; T3\'\' vs Dixon\'\': %.1f digits' % (
        dig(val(t['T3'][0]).real, dixon(b0)), dig(2 * val(t['T3'][2]).real, mp.diff(dixon, b0, 2))))
    Q1 = mp.gamma(mp.mpf(1) / 4) ** 4 / mp.pi
    Z1 = 4 * mp.pi ** 2 / 3 * mp.diff(dixon, b0, 2)
    print('d=1: (4pi^2/3) Dixon\'\'(1/2) vs Q_1 H: %.1f digits' % dig(Z1, Q1 * (2 * mp.pi ** 2 / 3 + 8 * G)))
    # frozen derivative closed form at d=1
    K = lambda k: mp.ellipk(k ** 2)
    Me = mp.quad(lambda k: K(k) ** 2, [0, 0.5, 1])
    Ne = mp.quad(lambda k: K(k) * mp.pi / (2 * mp.agm(1, k)), [0, 0.5, 1])
    A = 8 * Ne / mp.pi
    B = 8 * Me / mp.pi
    DL_closed = mp.sqrt(2) * mp.pi ** 2 / 4 * ((31 * mp.pi / 2 - 8 * mp.log(2)) * A + (19 * mp.pi - 10 * mp.log(2)) * B)
    DL_mine = val(r['printed']['DL'])
    DL_alt = mp.sqrt(2) * (5 * val(t['X0'][1]) - val(t['XT'][1])).real
    print('d=1: D_L (my jets) vs printed closed form: %.1f digits; sqrt2(5X0\'-XT\') vs D_L: %.1f digits' % (
        dig(DL_mine, DL_closed), dig(DL_alt, DL_mine)))
    print('d=1: P4 = 32 pi A + 40 pi B: %.1f digits' % dig(val(r['printed']['P4']), 32 * mp.pi * A + 40 * mp.pi * B))
    L1a = -2 * (mp.pi + mp.log(2)) * (32 * mp.pi * A + 40 * mp.pi * B) + 52 * mp.pi ** 2 * A + 64 * mp.pi ** 2 * B
    print('d=1: L_1 = -2(pi+log2)P4+52pi^2A+64pi^2B vs my printed-formula L: %.1f digits' % dig(L1a, val(r['printed']['L'])))
# ---------------- d = 2
r = load('2')
if r:
    t = r['taylor']
    print('d=2: M3 jets (should vanish):', [mp.nstr(abs(val(v)), 3) for v in t['M3'][:3]])
    XT, X0, Xh = (val(t[k][0]).real for k in ('XT', 'X0', 'Xh'))
    A = mp.sqrt(XT)
    B = (mp.sqrt(X0) - mp.sqrt(Xh)) / 2
    print('d=2: sqrt(X0)+sqrt(Xh) = 2A, i.e. X_T=A^2, X0=(A+B)^2, Xh=(A-B)^2: %.1f digits' % dig(
        (mp.sqrt(X0) + mp.sqrt(Xh)) / 2, A))
    print('d=2: L_2 = -16 log2 AB/pi vs printed-formula L: %.1f digits' % dig(-16 * mp.log(2) * A * B / mp.pi,
                                                                            val(r['printed']['L'])))
# ---------------- d = 3
r = load('3')
if r:
    t = r['taylor']
    d = mp.mpf(3)

    def c0g(b):
        g = (d - b) / 2
        Nb = mp.gamma(d / 2) * mp.gamma(g) / mp.gamma(b / 2)
        return -Nb ** 3 * mp.pi ** 5 * mp.gamma(3 * g - 2) / mp.gamma(g) ** 9

    b0 = mp.mpf(3) / 2
    for p in range(3):
        mine = val(t['c0hat'][p]).real * mp.factorial(p)
        print('d=3: c0hat^(%d) mine vs Gamma form: %.1f digits' % (p, dig(mine, mp.diff(c0g, b0, p))))
    Z3 = 4 * mp.pi ** 2 / 3 * 2 * val(t['T3'][2]).real - (4 * G + mp.pi ** 2 / 2) * mp.gamma(mp.mpf(1) / 4) ** 10 / (
        16 * mp.pi ** mp.mpf(3.5))
    print('d=3: printed Z_3 = (4pi^2/3)S\'\' - (4G+pi^2/2)Gamma(1/4)^10/(16 pi^7/2) vs known: %.1f digits' % dig(
        Z3, mp.mpf('8.82092489306009248553686732817408087436')))
