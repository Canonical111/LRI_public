#!/usr/bin/env python3
"""N4a: cross-validation of the two evaluators of the three parts of S_R at complex t.

 (i)  direct.py   : truncated lattice sums in ball arithmetic, Richardson-extrapolated in the cutoff N
                    (leading truncation error ~ N^(2q-1-tau), common to all three parts);
 (ii) rblocks.py  : R_part's regularized Horn blocks (P_R H_R, P_M H_M, P_L H_L), two (K, M) settings.
Used to validate (ii) at complex t before it is used for small Re tau (n5_parts.py, n6_jetdisc.py).
"""
import sys, time
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/K_general/R_part')
import mpmath as mp
import rblocks as rb
from flint import arb, acb, ctx
import direct

ctx.prec = 260
mp.mp.dps = 40


def to_mp(z):
    return mp.mpc(mp.mpf(z.real.mid().str(40, radius=False)), mp.mpf(z.imag.mid().str(40, radius=False)))


def direct_rich(ds, taus, x, y, N):
    q = arb(ds) / 4
    tau = acb(arb(taus[0]), arb(taus[1]))
    t = acb(arb(x), arb(y))
    P1 = direct.parts(q, tau, t, N)
    P2 = direct.parts(q, tau, t, 2 * N)
    P4 = direct.parts(q, tau, t, 4 * N)
    qm = mp.mpf(ds) / 4; taum = mp.mpc(taus[0], taus[1])
    f = mp.mpf(2) ** (1 + taum - 2 * qm)          # truncation error ~ N^{2q-1-tau}
    out = {}
    for k in ('right', 'middle', 'left'):
        a, b, c = to_mp(P1[k]), to_mp(P2[k]), to_mp(P4[k])
        r1 = (f * b - a) / (f - 1)
        r2 = (f * c - b) / (f - 1)
        out[k] = (r2, abs(r2 - r1), abs(c - b))
    return out


def rblocks_parts(ds, taus, x, y, K, M):
    q = mp.mpf(ds) / 4; tau = mp.mpc(taus[0], taus[1]); t = mp.mpc(x, y)
    Xi, p = rb.sample(q, t, tau, K, M, parts=True)
    g2 = mp.gamma(2 * q) ** 2
    return dict(right=g2 * p['PR'] * p['HR'], middle=g2 * p['PM'] * p['HM'], left=g2 * p['PL'] * p['HL'])


for ds, taus in (('1.5', ('2.37', '0')), ('0.8', ('2.37', '0.4')), ('2.5', ('2.37', '0')), ('3.4', ('2.6', '-0.3'))):
    for (x, y) in (('0.13', '1'), ('0.61', '2.5'), ('0.37', '-4')):
        st = time.time()
        D = direct_rich(ds, taus, x, y, 4000)
        R1 = rblocks_parts(ds, taus, mp.mpf(x), mp.mpf(y), 18, 260)
        R2 = rblocks_parts(ds, taus, mp.mpf(x), mp.mpf(y), 24, 400)
        line = []
        for k in ('right', 'middle', 'left'):
            ref, rich_err, _ = D[k]
            line.append('%s: |val|=%s  rich.err=%s  |rb(18,260)-ref|=%s  |rb(24,400)-ref|=%s' % (
                k[0], mp.nstr(abs(ref), 6), mp.nstr(rich_err / abs(ref), 2), mp.nstr(abs(R1[k] - ref) / abs(ref), 2),
                mp.nstr(abs(R2[k] - ref) / abs(ref), 2)))
        print('d=%s tau=%s+%si t=%s+%si (%.0fs)\n    ' % (ds, taus[0], taus[1], x, y, time.time() - st) + '\n    '.join(line), flush=True)
