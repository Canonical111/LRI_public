#!/usr/bin/env python3
"""High-precision K_d from the position-space 2-fold Mellin-Barnes representation of the K-path master (symmetric-star form).

Exact representation (derived in this directory; J_t is gs:Kdefinition's path master, normalized with h_d per vertex):
   J_t = N (2 pi i)^-2 int int Phi_t(z1,z2) dz1 dz2,   N = Gamma(2q)^2 / Gamma(q)^4,  q = d/4,  w = z1+z2,
   Phi_t = G(-z1)^2 G(-z2)^2 G(q+w)^2 G(q+z2)/G(q-z2) * G(t/2+z1) G(q-t/2-w) / ( G(2q-t/2-z1) G(q+t/2+w) ),
   straight contours  -t/2 < Re z1 < 0,  -q < Re z2 < 0,  Re w > -q.
Pole split (move Re z1 left of -t/2; the crossed residue is Barnes' first lemma):
   J_t = J_pole(t) + J_reg(t),   J_pole(t) = Gamma(2q) Gamma(t/2)^2 Gamma(q-t/2)^4 / ( Gamma(q)^4 Gamma(2q-t) ),
   J_reg(t) = same double integral on  -q < Re z1 < -|t|/2 ,  Re w > -q :  analytic at t = 0.
Hence  K_d = [t^2](J_t - J_t^Gamma) = [t^2](J_pole - J^Gamma) + N (2 pi i)^-2 int int Phi_0 (l1^2 + l2)/2 ,
   l1 = (psi(z1) + psi(2q-z1) - psi(q-w) - psi(q+w))/2,   l2 = (psi1(z1) - psi1(2q-z1) + psi1(q-w) - psi1(q+w))/4,
   Phi_0 = G(-z1)^2 G(z1)/G(2q-z1) * G(-z2)^2 G(q+z2)/G(q-z2) * G(q+w) G(q-w).
Checks: [t^0] and [t^1] of (J_pole - J^Gamma) + J_reg must vanish.

Numerics: trapezoid rule on Re z1 = c1, Re z2 = c2 (exponentially convergent; error ~ exp(-2 pi delta / h)).
The integrand factorizes as F1(z1) F2(z2) G(w) x (polynomial in z1- and w-functions); with equal steps the w-grid is
1-D, so every 2-D sum is a correlation  sum_j F2_j H_{i+j}, done by exact-ball acb_poly multiplication.

usage: kmb_flint.py d DIGITS [c1 c2]   (d as decimal string; default c1 = c2 = -q/3)
"""
import sys, json, time
from flint import acb, arb, acb_poly, ctx
import mpmath as mp


def gamma_part(dstr, dps):
    """[t^k](J_pole - J^Gamma), k = -2..2, by a Cauchy circle (exponentially accurate)."""
    mp.mp.dps = dps
    d = mp.mpf(dstr); q = d / 4; h = d / 2
    G = mp.gamma; rg = mp.rgamma
    def Bd(a, b):
        return G(h) * G((d - a) / 2) * G((d - b) / 2) * G((a + b - d) / 2) * rg(a / 2) * rg(b / 2) * rg((2 * d - a - b) / 2)
    def f(t):
        Jp = G(2 * q) * G(t / 2) ** 2 * G(q - t / 2) ** 4 * rg(q) ** 4 * rg(2 * q - t)
        JG = Bd(h, d - t) ** 2 + 2 / t * (Bd(h, d - t) - Bd(h + 2 * t, d - t))
        return Jp - JG
    R = min(q, mp.mpf(2)); r = R / 4
    M = int(2 * (dps + 10) * mp.log(10) / mp.log(4)) + 16
    out = {k: mp.mpc(0) for k in range(-2, 5)}
    for j in range(M):
        tt = r * mp.expj(2 * mp.pi * (j + mp.mpf(1) / 3) / M)
        v = f(tt)
        for k in out:
            out[k] += v * tt ** (-k) / M
    return {k: mp.re(v) for k, v in out.items()}, {k: mp.im(v) for k, v in out.items()}


def reg_coeffs(dstr, digits, c1=None, c2=None, verbose=True):
    bits = int(digits * 3.33) + 80
    ctx.prec = bits
    d = arb(dstr); q = d / 4
    qf = float(dstr) / 4
    if c1 is None: c1 = -qf / 3
    if c2 is None: c2 = -qf / 3
    c1 = arb(c1); c2 = arb(c2)
    c1f, c2f = float(c1), float(c2)
    delta = min(abs(c1f), abs(c1f + 1), abs(c1f + c2f + qf), abs(qf - c1f - c2f), abs(c2f), abs(c2f + qf))
    L = digits * 2.302585 + 25
    hstep = 2 * 3.141592653589793 * delta / L
    Y = (L + 10) / (2 * 3.141592653589793) + 3
    N = int(Y / hstep) + 1
    hh = arb(hstep)
    if verbose:
        print('d=%s digits=%d prec=%d c1=%g c2=%g delta=%.4f h=%.5f Y=%.1f N=%d' % (dstr, digits, bits, c1f, c2f, delta, hstep, Y, N), flush=True)
    t0 = time.time()
    two_q = 2 * q
    F1 = []; A1 = []; A2 = []; F2 = []
    for j in range(-N, N + 1):
        z1 = acb(c1, hh * j)
        lg = 2 * (-z1).lgamma() + z1.lgamma() - (two_q - z1).lgamma()
        F1.append(lg.exp())
        A1.append((z1.digamma() + (two_q - z1).digamma()) / 2)
        A2.append((z1.polygamma(1) - (two_q - z1).polygamma(1)) / 4)
        z2 = acb(c2, hh * j)
        lg2 = 2 * (-z2).lgamma() + (q + z2).lgamma() - (q - z2).lgamma()
        F2.append(lg2.exp())
    G = []; B1 = []; B2 = []
    cw = c1 + c2
    for s in range(-2 * N, 2 * N + 1):
        w = acb(cw, hh * s)
        G.append(((q + w).lgamma() + (q - w).lgamma()).exp())
        B1.append(-((q - w).digamma() + (q + w).digamma()) / 2)
        B2.append(((q - w).polygamma(1) - (q + w).polygamma(1)) / 4)
    if verbose:
        print('  special functions: %.1f s' % (time.time() - t0), flush=True)
    # correlation C_i = sum_j F2_j H_{i+j}, i,j in [-N,N], s = i+j in [-2N,2N]
    P = acb_poly([F2[2 * N - k] for k in range(2 * N + 1)])  # coefficient x^k <-> F2 at j = N - k (list index j+N)
    def corr(H):
        Q = acb_poly(H)                                       # x^m <-> H at s = m - 2N
        PQ = P * Q                                            # x^{N-j+s+2N}, s=i+j -> x^{3N+i}
        return [PQ[3 * N + i] for i in range(-N, N + 1)]
    H0 = G
    H1 = [G[k] * B1[k] for k in range(4 * N + 1)]
    H2 = [G[k] * (B1[k] * B1[k] + B2[k]) for k in range(4 * N + 1)]
    C0, C1, C2 = corr(H0), corr(H1), corr(H2)
    if verbose:
        print('  correlations: %.1f s' % (time.time() - t0), flush=True)
    S0 = acb(0); S1 = acb(0); S2 = acb(0)
    for i in range(2 * N + 1):
        f = F1[i]; a1 = A1[i]; a2 = A2[i]
        S0 += f * C0[i]
        S1 += f * (a1 * C0[i] + C1[i])
        S2 += f * ((a1 * a1 + a2) * C0[i] + 2 * a1 * C1[i] + C2[i]) / 2
    pi = arb.pi()
    Nn = ((two_q).lgamma() * 2 - q.lgamma() * 4).exp()
    fac = Nn * hh * hh / (4 * pi * pi)
    return [S0 * fac, S1 * fac, S2 * fac], dict(delta=delta, h=hstep, Y=Y, N=N, prec=bits, c1=c1f, c2=c2f)


if __name__ == '__main__':
    dstr = sys.argv[1]; digits = int(sys.argv[2])
    c1 = sys.argv[3] if len(sys.argv) > 3 else None
    c2 = sys.argv[4] if len(sys.argv) > 4 else None
    st = time.time()
    R, info = reg_coeffs(dstr, digits, c1, c2)
    gp, gpi = gamma_part(dstr, digits + 25)
    mp.mp.dps = digits + 10
    Rre = [mp.mpf(x.real.mid().str(digits + 15, radius=False)) for x in R]
    Rim = [float(x.imag.mid()) for x in R]
    chk0 = Rre[0] + gp[0]; chk1 = Rre[1] + gp[1]
    K = Rre[2] + gp[2]
    print('  Jreg[t^0..2] =', [mp.nstr(x, 25) for x in Rre], ' imag', Rim)
    print('  Gamma part [t^-2..2] =', [mp.nstr(gp[k], 25) for k in range(-2, 3)])
    print('  check t^0: %s   t^1: %s' % (mp.nstr(chk0, 5), mp.nstr(chk1, 5)))
    print('K_d =', mp.nstr(K, digits))
    out = dict(d=dstr, digits_target=digits, K=mp.nstr(K, digits + 5), check_t0=mp.nstr(chk0, 5), check_t1=mp.nstr(chk1, 5),
               Jreg=[mp.nstr(x, digits + 5) for x in Rre], gamma_part={str(k): mp.nstr(gp[k], digits + 5) for k in range(-2, 3)},
               info=info, seconds=time.time() - st)
    fn = 'K_mb_d%s_D%d%s.json' % (dstr, digits, '' if c1 is None else '_c%s_%s' % (c1, c2))
    json.dump(out, open(fn, 'w'), indent=1)
    print('  wrote', fn, ' %.1f s' % (time.time() - st))
