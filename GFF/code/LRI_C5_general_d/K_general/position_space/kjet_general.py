#!/usr/bin/env python3
"""Full check of the B-point jet (gs:Bjet) at generic d along arbitrary lines through B, using an exact pole split
of the general-index 2-fold MB.

Kite J_d(a,b,c,f,e) (gs:masterJ) with B-coordinates (gs:Bjet): a = e-p1+p2+z2-z1, b = d+p1-e-p2, c = d+p1-e-z2, f = d-p1.
Star = x (nu1=a/2, nu2=b/2, nu3=e/2; all = q at B), bubble = y (a3=c/2, a4=f/2).  h = d/2, lam = nu1+nu2+nu3-h, eps = h-a4 = p1/2.
   J = P0 MB[ F1(z1) F2(z2) G(z1+z2) ],  F1 = G(-z1)G(nu2-lam-z1)G(h-a3+z1)/G(a3-z1),  F2 = G(-z2)G(nu1-lam-z2)G(h-a4+z2)/G(a4-z2),
   G = G(lam+w)G(nu3+w)G(a3+a4-h-w)/G(d-a3-a4+w),  P0 = G(h)^2/(G(nu1)G(nu2)G(nu3)G(h-lam)).
Moving Re z2 left across z2 = -eps (pole of G(h-a4+z2)) leaves a residue in which the bubble factors cancel and the z1
integral is Barnes' first lemma:
   J_pole^gen = P0 G(eps) G(nu1-lam+eps) G(lam-eps) G(nu2-eps) G(nu3-eps) G(nu2+nu3-lam-eps) / ( G(h) G(nu2+nu3-2 eps) ),
   J_reg^gen  = P0 MB on Re z2 = c2' < -eps : analytic near B.
Prediction of gs:Bjet:  J - [G2+G1-G0+(2/p1)Delta_B] = K z1 z2 + O(3)  along every line (p1,p2,z1,z2,e-d/2) = t v.
usage: kjet_general.py d v1,v2,v3,v4,v5 digits [r M]"""
import sys, time, json
import mpmath as mp
from flint import acb, arb, acb_poly, ctx


def idx_of(d, pt):
    p1, p2, z1, z2, e = pt
    a = e - p1 + p2 + z2 - z1; b = d + p1 - e - p2; c = d + p1 - e - z2; f = d - p1
    return a / 2, b / 2, e / 2, c / 2, f / 2          # nu1, nu2, nu3, a3, a4


def gamma_side(d, pt):
    """J_pole^gen - J^Gamma_jet  (mpmath, complex ok)"""
    G = mp.gamma; rg = mp.rgamma; h = d / 2
    p1, p2, z1, z2, e = pt
    n1, n2, n3, a3, a4 = idx_of(d, pt)
    lam = n1 + n2 + n3 - h; eps = h - a4
    P0 = G(h) ** 2 * rg(n1) * rg(n2) * rg(n3) * rg(h - lam)
    Jp = P0 * G(eps) * G(n1 - lam + eps) * G(lam - eps) * G(n2 - eps) * G(n3 - eps) * G(n2 + n3 - lam - eps) * rg(h) * rg(n2 + n3 - 2 * eps)
    def B(x, y):
        return G(h) * G((d - x) / 2) * G((d - y) / 2) * G((x + y - d) / 2) * rg(x / 2) * rg(y / 2) * rg((2 * d - x - y) / 2)
    G2 = B(d + p1 - e, d - p1) * B(e + p2 - z1, d - p2)
    G1 = B(e - p1 + p2 + z2, d + p1 - e - z2) * B(d + p1 - e - p2, d - p1)
    G0 = B(d + p1 - e, d - p1) * B(e + p2, d - p2)
    DB = B(e + p2 + z2 - z1, d - p2) - B(e + p2 - z1, d - p2) - B(e + p2 + z2, d - p2) + B(e + p2, d - p2)
    return Jp - (G2 + G1 - G0 + 2 / p1 * DB), Jp


class RegMB:
    """J_reg^gen on fixed contours Re z1 = c1, Re z2 = c2 (chosen at B), for complex parameters near B."""
    def __init__(self, d, digits, c1, c2, delta, Ylen=None):
        self.bits = int(digits * 3.33) + 80
        ctx.prec = self.bits
        L = digits * 2.302585 + 25
        self.h = 2 * 3.141592653589793 * delta / L
        Y = (L + 10) / (2 * 3.141592653589793) + 4
        self.N = int(Y / self.h) + 1
        self.d = arb(d); self.c1 = arb(c1); self.c2 = arb(c2)
    def value(self, n1, n2, n3, a3, a4):
        ctx.prec = self.bits
        cv = lambda z: acb(mp.nstr(mp.re(z), 60), mp.nstr(mp.im(z), 60))
        n1, n2, n3, a3, a4 = [cv(x) for x in (n1, n2, n3, a3, a4)]
        d = acb(self.d); h = d / 2; lam = n1 + n2 + n3 - h; cw = a3 + a4 - h
        N = self.N; hh = arb(self.h)
        F1 = []; F2 = []
        for j in range(-N, N + 1):
            z1 = acb(self.c1, hh * j); z2 = acb(self.c2, hh * j)
            F1.append(((-z1).lgamma() + (n2 - lam - z1).lgamma() + (h - a3 + z1).lgamma() - (a3 - z1).lgamma()).exp())
            F2.append(((-z2).lgamma() + (n1 - lam - z2).lgamma() + (h - a4 + z2).lgamma() - (a4 - z2).lgamma()).exp())
        Gw = []
        for s in range(-2 * N, 2 * N + 1):
            w = acb(self.c1 + self.c2, hh * s)
            Gw.append(((lam + w).lgamma() + (n3 + w).lgamma() + (cw - w).lgamma() - (d - a3 - a4 + w).lgamma()).exp())
        PQ = acb_poly([F2[2 * N - k] for k in range(2 * N + 1)]) * acb_poly(Gw)
        S = acb(0)
        for i in range(-N, N + 1):
            S += F1[i + N] * PQ[3 * N + i]
        P0 = (h.lgamma() * 2 - n1.lgamma() - n2.lgamma() - n3.lgamma() - (h - lam).lgamma()).exp()
        v = P0 * S * hh * hh / (4 * arb.pi() ** 2)
        return mp.mpc(v.real.mid().str(40, radius=False), v.imag.mid().str(40, radius=False))


if __name__ == '__main__':
    dstr = sys.argv[1]; v = [mp.mpf(x) for x in sys.argv[2].split(',')]; digits = int(sys.argv[3])
    mp.mp.dps = digits + 20
    d = mp.mpf(dstr); q = d / 4
    r = mp.mpf(sys.argv[4]) if len(sys.argv) > 4 else q / (6 * max(abs(x) for x in v))
    M = int(sys.argv[5]) if len(sys.argv) > 5 else 24
    c1 = -q / 3; c2 = -q / 3
    delta = float(q / 3 - 1.2 * r * max(abs(x) for x in v))
    reg = RegMB(dstr, digits, mp.nstr(c1, 30), mp.nstr(c2, 30), delta)
    print('d=%s v=%s r=%s M=%d delta=%.4f N=%d' % (dstr, [float(x) for x in v], mp.nstr(r, 4), M, delta, reg.N), flush=True)
    coef_g = [mp.mpc(0)] * 7; coef_r = [mp.mpc(0)] * 4
    st = time.time()
    for k in range(M):
        t = r * mp.expj(2 * mp.pi * (k + mp.mpf(1) / 7) / M)
        pt = [t * v[0], t * v[1], t * v[2], t * v[3], d / 2 + t * v[4]]
        gs, _ = gamma_side(d, pt)
        jr = reg.value(*idx_of(d, pt))
        for j in range(-3, 4):
            coef_g[j + 3] += gs * t ** (-j) / M
        for j in range(4):
            coef_r[j] += jr * t ** (-j) / M
    tot = {j: coef_g[j + 3] + (coef_r[j] if j >= 0 else 0) for j in range(-3, 4)}
    print('  Laurent coefficients of J - J^Gamma_jet along the line (%.0f s):' % (time.time() - st))
    for j in range(-3, 3):
        print('   t^%d : %s' % (j, mp.nstr(mp.re(tot[j]), 20)))
    kz = v[2] * v[3]
    print('  [t^2] / (v_z1 v_z2) = %s' % mp.nstr(mp.re(tot[2]) / kz if kz != 0 else mp.nan, digits))
    json.dump(dict(d=dstr, v=[str(x) for x in v], r=str(r), M=M, coef={str(j): mp.nstr(mp.re(tot[j]), digits) for j in range(-3, 3)},
                   K_line=mp.nstr(mp.re(tot[2]) / kz, digits) if kz != 0 else None),
              open('kjet_d%s_v%s.json' % (dstr, '_'.join(sys.argv[2].split(','))), 'w'), indent=1)
