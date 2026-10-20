#!/usr/bin/env python3
"""Pointwise check of the mixed-trace identity behind gs:Kspectral at generic d and finite complex tau:
     J_{2 tau} = C(tau)^2 [G(q-tau/2)/G(q+tau/2)]^4 + C(tau) F(tau),   C = G(2q)G(tau)/G(2q-tau),
   F(tau) = <t_l^2 (R_tau - S_tau)>_d taken from the spectral reference runs (refvals/ref2_t_<d>.json, tau-circle),
   J_t from the position-space MB:  J_t = J_pole(t) + J_reg(t)  (kmb_flint.py conventions), t = 2 tau complex."""
import sys, json
import mpmath as mp
from flint import acb, arb, acb_poly, ctx

def J_full(dstr, t, digits, c1, c2):
    bits = int(digits * 3.33) + 80; ctx.prec = bits
    q = arb(dstr) / 4; qf = float(dstr) / 4
    ta = acb(mp.nstr(mp.re(t), 50), mp.nstr(mp.im(t), 50))
    tf = abs(complex(t))
    delta = min(abs(c1) - tf / 2, abs(c1 + 1) - tf / 2, abs(c1 + c2 + qf), abs(qf - c1 - c2) - tf / 2, abs(c2), abs(c2 + qf))
    L = digits * 2.302585 + 25; hs = 2 * 3.141592653589793 * delta / L
    Y = (L + 10) / (2 * 3.141592653589793) + 4; N = int(Y / hs) + 1
    hh = arb(hs); C1 = arb(repr(c1)); C2 = arb(repr(c2))
    F1 = []; F2 = []
    for j in range(-N, N + 1):
        z1 = acb(C1, hh * j); z2 = acb(C2, hh * j)
        F1.append((2 * (-z1).lgamma() + (ta / 2 + z1).lgamma() - (2 * q - ta / 2 - z1).lgamma()).exp())
        F2.append((2 * (-z2).lgamma() + (q + z2).lgamma() - (q - z2).lgamma()).exp())
    Gw = []
    for s in range(-2 * N, 2 * N + 1):
        w = acb(C1 + C2, hh * s)
        Gw.append((2 * (q + w).lgamma() + (q - ta / 2 - w).lgamma() - (q + ta / 2 + w).lgamma()).exp())
    PQ = acb_poly([F2[2 * N - k] for k in range(2 * N + 1)]) * acb_poly(Gw)
    S = acb(0)
    for i in range(-N, N + 1):
        S += F1[i + N] * PQ[3 * N + i]
    Nn = ((2 * q).lgamma() * 2 - q.lgamma() * 4).exp()
    Jreg = Nn * S * hh * hh / (4 * arb.pi() ** 2)
    Jpole = ((2 * q).lgamma() + 2 * (ta / 2).lgamma() + 4 * (q - ta / 2).lgamma() - 4 * q.lgamma() - (2 * q - ta).lgamma()).exp()
    v = Jreg + Jpole
    return mp.mpc(v.real.mid().str(digits + 5, radius=False), v.imag.mid().str(digits + 5, radius=False)), N

if __name__ == '__main__':
    dstr = sys.argv[1]; digits = int(sys.argv[2]); c1 = float(sys.argv[3]); c2 = float(sys.argv[4])
    ks = [int(x) for x in sys.argv[5].split(',')]
    mp.mp.dps = digits + 10
    R = json.load(open('<PROJECT>/LRI_C5_general_d/refvals/ref2_t_%s.json' % dstr))
    rho = mp.mpf(R['rho']); M = R['M']
    d = mp.mpf(dstr); q = d / 4
    for k in ks:
        tau = rho * mp.expj(2 * mp.pi * k / M)
        F = mp.mpmathify(R['values'][str(k)][0].replace(' ', ''))
        C = mp.gamma(2 * q) * mp.gamma(tau) / mp.gamma(2 * q - tau)
        rhs = C ** 2 * (mp.gamma(q - tau / 2) / mp.gamma(q + tau / 2)) ** 4 + C * F
        lhs, N = J_full(dstr, 2 * tau, digits, c1, c2)
        print('d=%s k=%d tau=%s  J_MB=%s  spectral=%s  |diff|=%s  (N=%d)' % (dstr, k, mp.nstr(tau, 6), mp.nstr(lhs, 22), mp.nstr(rhs, 22), mp.nstr(abs(lhs - rhs), 3), N), flush=True)
