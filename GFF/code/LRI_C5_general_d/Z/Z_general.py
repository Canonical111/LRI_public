#!/usr/bin/env python3
"""Z_d = (1/9) d^2/db^2 W_3(d;b) at b = d/2 for generic dimension 2/3 < d < 4, from the TWO-NODE finite formula

    W_3(d;b) = u(b) R(b) + v(b) Mh(b)                                      (Z_general_d.tex, Thm. 1)
    u = 2 pi^2 (1 + 2 cos(pi b/2)) / sin^2(pi b/2),   v = cos(pi b/2) (1 + cos(pi b/2))^2 / (2 pi sin^3(pi b/2)),
    R(b)  = sum_{l,n>=0} d_l T_ln(b)^3,  T_ln = (b/2)_{l+n} (1-g)_n / ((d/2)_{l+n} n!),  g = (d-b)/2
          = 7F6(1; (b/2)^3, (1-g)^3; (d/2)^3, 1^3; 1) + d (b/d)^3 H[U+;V+](t=0)        [node t = 0]
    Mh(b) = sum_l d_l sum_{n in Z} [N_b g_l(n + (l+1)/2; b)]^3                         [node t_b = (1 - b/2)/2]
          = N_b^3 [2 A0(t_b) + 2 A+(t_b) + C(t_b)]       (one 7F6(1), two two-variable Horn values)
and its rim jets (Thm. 2):
    9 Z_d = u'' R + 2 u' R' + u R'' + v'' Mh + 2 v' Mh' + v Mh''          at b = d/2,
with the first-derivative identity  u' R + u R' + v' Mh + v Mh' = 0  (dW_3/db = 0 at b = d/2).
Equivalent zero-mode form, R' eliminated (uniform in d):
    Z_d = 2 pi^2 R''/(3 s^2) - pi^4 cos(pi d/2) R/(3 s^4) + [3 pi c0 /s^3 - 4 c c0'/s^4 + 4 c0''/(pi s^3)]/9,
    c0 = N_b^3 c_{3,0}(q,b) = (cos(pi b/2)(1+cos(pi b/2))^2/8) Mh - pi^3 sin^3(pi b/2) R/(1 + cos(pi b/2)),
    s = sin(pi d/4), c = cos(pi d/4).

The b-derivatives of the five blocks are computed EXACTLY (truncated Taylor arithmetic through the accelerated Horn
evaluation of the foundation: engine 'jets', z_jets.py), or by Cauchy circles in b (engine 'cauchy', z_cauchy.py;
automatic at the resonant dimensions where 3d/4 is an integer, e.g. d = 4/3, 8/3).

usage:  python3 Z_general.py d [dps] [engine]          e.g.  python3 Z_general.py 1.5 30
        d = 1, 2, 3 are treated exactly (polynomial multiplicities); 'a/b' gives an exact rational d.
"""
import os
import sys
import time

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import z_blocks as zb  # noqa: E402
import z_jets as zj    # noqa: E402

GUARD = 15


def parse_d(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        x = str(x)
    if isinstance(x, str):
        return zj.parse_d(x)
    return x


def resonant(d):
    """True when 3(d - b)/2 is an integer at b = d/2 (removable resonance of the accelerated sums), noninteger d."""
    if isinstance(d, int):
        return False
    x = 3 * mp.mpf(d) / 4
    return abs(x - mp.nint(x)) < mp.mpf(10) ** (-mp.mp.dps // 3)


def block_jets(d, dps=30, engine='auto', M=48):
    """{block: [f, f', f'']} at b = d/2 for the five blocks R0, R1, M0, M1, MC."""
    d = parse_d(d)
    if engine == 'auto':
        engine = 'cauchy' if resonant(d) else 'jets'
    with mp.workdps(dps + GUARD):
        if engine == 'jets':
            zj.DEG = 2
            return zj.block_jets(d), engine
        import z_cauchy as zc
        rho = zc.radius(d)
        vals = {n: [] for n in zb.BLOCKS}
        for k in range(M // 2):
            b = mp.mpf(d) / 2 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / M)
            bl = zb.blocks(d, b)
            for n in zb.BLOCKS:
                vals[n].append(bl[n])
        out = {}
        for n in zb.BLOCKS:
            half = vals[n]
            full = half + [mp.conj(half[M - 1 - k]) for k in range(M // 2, M)]
            a = zc.taylor(full, M, rho)
            out[n] = [a[0], a[1], 2 * a[2]]
        return out, engine


def Z(d, dps=30, engine='auto', full=False):
    """Z_d from the two-node formula.  full=True returns a dict with all jets and the three equivalent assemblies."""
    d = parse_d(d)
    bj, used = block_jets(d, dps, engine)
    with mp.workdps(dps + GUARD):
        q = mp.mpf(d) / 4
        Rj = [bj['R0'][j] + bj['R1'][j] for j in range(3)]
        Mj = [bj['M0'][j] + bj['M1'][j] + bj['MC'][j] for j in range(3)]
        W0, W1, Zv = zb.assemble(q, Rj, Mj)
        Zred, elim = zb.assemble_reduced(q, Rj, Mj)
        Zc0, c0j = zb.zero_mode_form(q, Rj, Mj)
    with mp.workdps(dps):
        if not full:
            return +mp.re(Zv)
        return dict(Z=+mp.re(Zv), Q=+mp.re(W0) / 3, dW=+W1, Z_reduced=+mp.re(Zred), eliminated=elim,
                    Z_zero_mode=+mp.re(Zc0), R=[+x for x in Rj], Mh=[+x for x in Mj], c0hat=[+x for x in c0j],
                    blocks={k: [+x for x in v] for k, v in bj.items()}, engine=used)


def W3_two_node(d, b, dps=30):
    """W_3(d;b) = u R + v Mh at a general rim exponent b (0 < Re b < b_max(3,d))."""
    d = parse_d(d)
    with mp.workdps(dps + GUARD):
        b = mp.mpmathify(b)
        R, Mh, _ = zb.RM(d, b)
        u, v = zb.uv(b)
        val = u * R + v * Mh
    with mp.workdps(dps):
        return +val


if __name__ == '__main__':
    dstr = sys.argv[1]
    dps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    eng = sys.argv[3] if len(sys.argv) > 3 else 'auto'
    mp.mp.dps = dps
    st = time.time()
    r = Z(dstr, dps, eng, full=True)
    print('d = %s   (engine %s, %d digits, %.1f s)' % (dstr, r['engine'], dps, time.time() - st))
    print('  Z_d          =', mp.nstr(r['Z'], dps))
    print('  Q_d = W/3    =', mp.nstr(r['Q'], dps))
    print('  dW_3/db      =', mp.nstr(r['dW'], 5), '  (must vanish)')
    print('  Z (R\' or Mh\' eliminated by W\'=0: %s) =' % r['eliminated'], mp.nstr(r['Z_reduced'], dps))
    print('  Z (zero-mode form)        =', mp.nstr(r['Z_zero_mode'], dps))
    print('  R, R\', R\'\'    =', [mp.nstr(mp.re(x), 20) for x in r['R']])
    print('  Mh, Mh\', Mh\'\' =', [mp.nstr(mp.re(x), 20) for x in r['Mh']])
    print('  c0, c0\', c0\'\' =', [mp.nstr(mp.re(x), 20) for x in r['c0hat']])
