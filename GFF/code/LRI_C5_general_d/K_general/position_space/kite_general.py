#!/usr/bin/env python3
"""General-index d-dimensional kite J_d(a,b,c,f,e) (gs:masterJ, h_d-normalized):
   star vertex S with indices nu1 = S-0, nu2 = S-e, nu3 = S-B; bubble vertex B with alpha3 = B-0, alpha4 = B-e
   (index = distance exponent / 2).  h = d/2, lam = nu1+nu2+nu3-h, c_w = alpha3+alpha4-h.
   2-fold MB:  J = P0 (2 pi i)^-2 int int F1(z1) F2(z2) G(z1+z2) x1^z1 x2^z2  (x1 = x2 = 1 for the kite),
      F1 = G(-z1) G(nu2-lam-z1) G(h-a3+z1)/G(a3-z1),  F2 = G(-z2) G(nu1-lam-z2) G(h-a4+z2)/G(a4-z2),
      G  = G(lam+w) G(nu3+w) G(c_w-w)/G(d-a3-a4+w),     P0 = G(h)^2/(G(nu1)G(nu2)G(nu3)G(d-nu1-nu2-nu3)).
   Six residue families (z1 closed right, then z2 closed right; the z1-line x w-line points cancel pairwise):
      (m, n), (m, nu1-lam+n), (nu2-lam+m, n), (nu2-lam+m, nu1-lam+n), (c_w+k-n, n), (c_w+k-nu1+lam-n, nu1-lam+n),
   each term = (-1)^{i+j}/(i! j!) * (remaining Gamma factors at the point) * x1^z1 x2^z2."""
import sys, time
import mpmath as mp
from flint import acb, arb, acb_poly, ctx


def mb_value(d, nu1, nu2, nu3, a3, a4, c1, c2, digits=20, x1=1, x2=1):
    """direct 2-D trapezoid of the MB integral (correlation trick), straight contours Re z = c."""
    ctx.prec = int(digits * 3.33) + 80
    d, nu1, nu2, nu3, a3, a4 = [arb(str(v)) for v in (d, nu1, nu2, nu3, a3, a4)]
    h = d / 2; lam = nu1 + nu2 + nu3 - h; cw = a3 + a4 - h
    lx1 = arb(str(x1)).log(); lx2 = arb(str(x2)).log()
    # distance of contour to singular lines
    cf1, cf2 = float(c1), float(c2)
    dist = [abs(cf1), abs(cf1 - float(nu2 - lam)), abs(cf1 - float(a3 - h)), abs(cf2), abs(cf2 - float(nu1 - lam)), abs(cf2 - float(a4 - h)),
            abs(cf1 + cf2 + float(lam)), abs(cf1 + cf2 + float(nu3)), abs(cf1 + cf2 - float(cw))]
    delta = min(dist)
    L = digits * 2.302585 + 25
    hs = 2 * 3.141592653589793 * delta / L
    Y = (L + 10) / (2 * 3.141592653589793) + 4
    N = int(Y / hs) + 1
    hh = arb(hs); c1 = arb(str(c1)); c2 = arb(str(c2))
    F1 = []; F2 = []
    for j in range(-N, N + 1):
        z1 = acb(c1, hh * j); z2 = acb(c2, hh * j)
        F1.append(((-z1).lgamma() + (nu2 - lam - z1).lgamma() + (h - a3 + z1).lgamma() - (a3 - z1).lgamma() + z1 * lx1).exp())
        F2.append(((-z2).lgamma() + (nu1 - lam - z2).lgamma() + (h - a4 + z2).lgamma() - (a4 - z2).lgamma() + z2 * lx2).exp())
    Gw = []
    for s in range(-2 * N, 2 * N + 1):
        w = acb(c1 + c2, hh * s)
        Gw.append(((lam + w).lgamma() + (nu3 + w).lgamma() + (cw - w).lgamma() - (d - a3 - a4 + w).lgamma()).exp())
    P = acb_poly([F2[2 * N - k] for k in range(2 * N + 1)])
    PQ = P * acb_poly(Gw)
    S = acb(0)
    for i in range(-N, N + 1):
        S += F1[i + N] * PQ[3 * N + i]
    P0 = ((h).lgamma() * 2 - nu1.lgamma() - nu2.lgamma() - nu3.lgamma() - (d - nu1 - nu2 - nu3).lgamma()).exp()
    return P0 * S * hh * hh / (4 * arb.pi() ** 2), dict(delta=delta, h=hs, N=N)


def family_sums(d, nu1, nu2, nu3, a3, a4, x1, x2, M, dps=30):
    """partial sums of the six residue families, indices < M (geometric convergence for |x2|<|x1|<1)."""
    mp.mp.dps = dps
    d, nu1, nu2, nu3, a3, a4, x1, x2 = [mp.mpf(str(v)) for v in (d, nu1, nu2, nu3, a3, a4, x1, x2)]
    h = d / 2; lam = nu1 + nu2 + nu3 - h; cw = a3 + a4 - h
    lg = mp.loggamma; rg = mp.rgamma; G = mp.gamma
    def f1(z, skip=None):        # F1 without the Gamma that produced the residue
        v = mp.mpf(1)
        if skip != 'a': v *= G(-z)
        if skip != 'b': v *= G(nu2 - lam - z)
        return v * G(h - a3 + z) * rg(a3 - z)
    def f2(z, skip=None):
        v = mp.mpf(1)
        if skip != 'a': v *= G(-z)
        if skip != 'b': v *= G(nu1 - lam - z)
        return v * G(h - a4 + z) * rg(a4 - z)
    def g(w, skip=False):
        v = G(lam + w) * G(nu3 + w) * rg(d - a3 - a4 + w)
        if not skip: v *= G(cw - w)
        return v
    P0 = G(h) ** 2 * rg(nu1) * rg(nu2) * rg(nu3) * rg(d - nu1 - nu2 - nu3)
    fam = {}
    for name, (o1, s1), (o2, s2) in [('00', (0, 'a'), (0, 'a')), ('01', (0, 'a'), (nu1 - lam, 'b')),
                                     ('10', (nu2 - lam, 'b'), (0, 'a')), ('11', (nu2 - lam, 'b'), (nu1 - lam, 'b'))]:
        tot = 0
        for m in range(M):
            for n in range(M):
                z1 = o1 + m; z2 = o2 + n
                tot += (-1) ** (m + n) / (mp.factorial(m) * mp.factorial(n)) * f1(z1, s1) * f2(z2, s2) * g(z1 + z2) * x1 ** z1 * x2 ** z2
        fam[name] = P0 * tot
    for name, (o2, s2) in [('w0', (0, 'a')), ('w1', (nu1 - lam, 'b'))]:
        tot = 0
        for k in range(M):
            for n in range(M):
                z2 = o2 + n; w = cw + k; z1 = w - z2
                tot += (-1) ** (k + n) / (mp.factorial(k) * mp.factorial(n)) * f1(z1) * f2(z2, s2) * g(w, skip=True) * x1 ** z1 * x2 ** z2
        fam[name] = P0 * tot
    return fam


if __name__ == '__main__':
    d, nu1, nu2, nu3, a3, a4 = '1.7', '0.395', '0.387', '0.380', '0.159', '0.620'
    c1, c2 = '-0.104', '-0.104'
    for (x1, x2) in [('0.6', '0.35'), ('0.8', '0.5')]:
        st = time.time()
        v, info = mb_value(d, nu1, nu2, nu3, a3, a4, c1, c2, digits=22, x1=x1, x2=x2)
        print('x=(%s,%s) MB = %s   %s  (%.1f s)' % (x1, x2, v.real.str(20), info, time.time() - st), flush=True)
        for M in (60, 90):
            st = time.time()
            fam = family_sums(d, nu1, nu2, nu3, a3, a4, x1, x2, M)
            tot = sum(fam.values())
            print('   M=%d  sum of 6 families = %s   (%.1f s)' % (M, mp.nstr(tot, 20), time.time() - st), {k: mp.nstr(v_, 8) for k, v_ in fam.items()}, flush=True)
