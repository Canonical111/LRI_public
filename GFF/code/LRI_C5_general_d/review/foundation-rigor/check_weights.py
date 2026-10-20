#!/usr/bin/env python3
"""Review check A (foundation-rigor): residue functional weights of Prop. 9.
Independent re-derivation: the residue of e^{2 pi i m t}/D_b(t)^r at t=0 is computed by mpmath Taylor
expansion of t^r e^{2 pi i m t}/D_b(t)^r (no Bell polynomials, no polygamma formulas), then compared with
  (a) the Bell-polynomial weights E_{r-1}(u_1+2 pi i m, u_2, ...)/(pi sin pi sigma)^r of eq:weights,
  (b) the elementary forms eq:elementary, the quoted B_{4,k}, and the boxed eq:explicit.
Also prints B_{3,2}, B_{4,3} (nonzero: the top-mode theorem is load-bearing for eq:explicit)."""
import mpmath as mp

mp.mp.dps = 30


def res_direct(r, sig, m):
    # coefficient of t^{r-1} in t^r e^{2 pi i m t} / D_b(t)^r
    f = lambda t: (t / (mp.sin(mp.pi * t) * mp.sin(mp.pi * (t + sig)))) ** r * mp.exp(2j * mp.pi * m * t)
    co = mp.taylor(f, mp.mpf('1e-40'), r - 1, method='quad', radius=mp.mpf('0.05'))
    return co[r - 1]


def bellE(xs):
    E = [mp.mpc(1)]
    for m in range(1, len(xs) + 1):
        E.append(mp.fsum(xs[h - 1] / mp.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m)
    return E


def u_weights(r, s):
    out = []
    for h in range(1, r):
        out.append(r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - (-1) ** (h + 1) * mp.psi(h - 1, 1 - s)
                        + mp.psi(h - 1, s)))
    return out


worst = 0
for r in (2, 3, 4, 5):
    for sig in (mp.mpf('0.137'), mp.mpf('0.41'), mp.mpf('0.77'), mp.mpc('0.3', '0.2')):
        u = u_weights(r, sig)
        for m in range(-(r - 1), r):
            a = res_direct(r, sig, m)
            b = bellE([u[0] + 2j * mp.pi * m] + u[1:])[r - 1] / (mp.pi * mp.sin(mp.pi * sig)) ** r
            worst = max(worst, abs(a - b) / abs(b))
print('max rel dev  direct Taylor residue vs Bell weights (r=2..5, 4 sigmas incl. complex, all m):', mp.nstr(worst, 3))

# elementary forms
for sig in (mp.mpf('0.137'), mp.mpf('0.41'), mp.mpf('0.77')):
    c = mp.cot(mp.pi * sig)
    s, co = mp.sin(mp.pi * sig), mp.cos(mp.pi * sig)
    for r in (3, 4):
        u = u_weights(r, sig)
        print('sigma=%s r=%d  u1/(r pi)+c=%s  u2/(r pi^2)-(c^2+4/3)=%s' % (
            sig, r, mp.nstr(u[0] / (r * mp.pi) + c, 3), mp.nstr(u[1] / (r * mp.pi ** 2) - (c ** 2 + mp.mpf(4) / 3), 3)),
            end='')
        if r == 4:
            print('  u3/(r pi^3)+2c(1+c^2)=%s' % mp.nstr(u[2] / (r * mp.pi ** 3) + 2 * c * (1 + c ** 2), 3))
        else:
            print()
    # B_{r,k}
    for r in (3, 4):
        u = u_weights(r, sig)
        B = []
        for k in range(r):
            Ep = bellE([u[0] + 2j * mp.pi * k] + u[1:])[r - 1]
            Em = bellE([u[0] - 2j * mp.pi * k] + u[1:])[r - 1]
            B.append((mp.expjpi(k * sig) * Ep + mp.expjpi(-k * sig) * Em) / 2)
        if r == 4:
            print('  B40 dev', mp.nstr(B[0] - (-4 * mp.pi ** 3 * c * (5 * c ** 2 + 3)), 3),
                  ' B41 dev', mp.nstr(B[1] - (-4 * mp.pi ** 3 * (5 * c ** 2 + 1) / s), 3),
                  ' B42 dev', mp.nstr(B[2] - (-20 * mp.pi ** 3 * co / s ** 3), 3),
                  ' B43 =', mp.nstr(B[3], 8))
            # eq:explicit: -[1/(pi s)]^4 sum B_k c_k  vs  4/(pi s^7)[co(3+2co^2)c0+(1+4co^2)c1+5co c2]
            cs = [mp.mpf('0.31'), mp.mpf('-1.7'), mp.mpf('0.53')]
            lhs = -(1 / (mp.pi * s)) ** 4 * mp.fsum(B[k] * cs[k] for k in range(3))
            rhs = 4 / (mp.pi * s ** 7) * (co * (3 + 2 * co ** 2) * cs[0] + (1 + 4 * co ** 2) * cs[1] + 5 * co * cs[2])
            print('  eq:explicit r=4 dev', mp.nstr(abs(lhs - rhs) / abs(rhs), 3))
        else:
            cs = [mp.mpf('0.31'), mp.mpf('-1.7')]
            lhs = -(1 / (mp.pi * s)) ** 3 * mp.fsum(B[k] * cs[k] for k in range(2))
            rhs = -2 / (mp.pi * s ** 5) * ((1 + 2 * co ** 2) * cs[0] + 3 * co * cs[1])
            print('  eq:explicit r=3 dev', mp.nstr(abs(lhs - rhs) / abs(rhs), 3), '  B32 =', mp.nstr(B[2], 8),
                  ' (6 pi^2/s^2 =', mp.nstr(6 * mp.pi ** 2 / s ** 2, 8), ')')
