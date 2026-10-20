"""Per-spin residue sums I_l(q) = sum_n [M^2 S_ln^2/8 - T_ln^2 R_ln/4] for general q (head + asymptotic n-tail), Arb."""
from flint import arb, arb_series, ctx
def spins(qq, ells, prec, N0, KN):
    ctx.prec = prec
    q = arb(qq) if not isinstance(qq, arb) else qq
    one = arb(1)
    def psi(j, x):
        x = arb(x)
        return x.digamma() if j == 0 else (-1) ** (j + 1) * arb.fac_ui(j) * arb(j + 1).zeta(x)
    Mc = -(1 - q).gamma() * (2 * q).gamma() ** 2 / (q * (3 * q).gamma())
    p1 = [psi(j, one) for j in range(5)]; pq = [psi(j, q) for j in range(5)]; p1q = [psi(j, 1 - q) for j in range(5)]
    cstar = p1[0] + psi(0, 2 * q)
    sg = [(-1) ** j for j in range(5)]
    Lmax = max(ells) + 1; Mmax = Lmax + N0
    f = [one]; e = [one]
    for m in range(Mmax):
        f.append(f[-1] * (q + m) / (2 * q + m)); e.append(e[-1] * (2 * q + m) / (3 * q + m))
    g = [one]; h = [one]
    for n in range(N0):
        g.append(g[-1] * (1 - q + n) / (n + 1)); h.append(h[-1] * (n + 1) / (1 + q + n))
    def polyseq(x0, cnt):
        cur = [psi(j, x0) for j in range(4)]; seq = []
        for k in range(cnt):
            seq.append(list(cur)); x = x0 + k
            for j in range(4):
                cur[j] = cur[j] + (-1) ** j * arb.fac_ui(j) / x ** (j + 1)
        return seq
    PA = polyseq(q, Mmax); PB = polyseq(2 * q, Mmax); PN1 = polyseq(one, N0); PNQ = polyseq(1 - q, N0)
    def Rpoly(pa, pb, pn1, pnq, logpart=False):
        chi = [sg[j] * pnq[j] + pq[j] - sg[j] * p1q[j] for j in range(4)]
        lam = [None] + [pa[j - 1] - pb[j - 1] - sg[j] * chi[j - 1] + (1 + sg[j]) * p1[j - 1] - pn1[j - 1] for j in range(1, 5)]
        r = [lam[j + 1] / 2 + pb[j] + pn1[j] - (1 - sg[j]) * p1[j] for j in range(4)]
        l1, l2, l3, l4 = lam[1], lam[2], lam[3], lam[4]
        P3 = l1 ** 3 + 3 * l1 * l2 + l3
        R = ((r[0] - cstar) / 2 * P3 + 3 * r[1] * (l1 ** 2 + l2) / 4 - (l1 * r[2] + r[3]) / 4
             - l1 ** 4 / 12 + l1 ** 2 * l2 / 8 + 7 * l1 * l3 / 24 + l2 ** 2 / 8 + l4 / 12)
        return (R, P3) if logpart else R
    M2 = Mc ** 2
    K1 = KN + 1; ctx.cap = K1
    S = lambda c: arb_series(c, prec=K1)
    Bc = {}
    def bern(k, c):
        key = (k, c.mid().str(60, radius=False))
        if key not in Bc: Bc[key] = arb(c).bernoulli_poly(k)
        return Bc[key]
    def lr(al, be):
        return S([arb(0)] + [(-1) ** (k + 1) * (bern(k + 1, al) - bern(k + 1, be)) / (k * (k + 1)) for k in range(1, K1)])
    def ps(j, c):
        if j == 0: return S([arb(0)] + [-(-1) ** k * bern(k, c) / k for k in range(1, K1)])
        co = [arb(0)] * K1
        for k in range(0, K1 - j): co[k + j] = (-1) ** (j - 1) * (-1) ** k * bern(k, c) * arb.fac_ui(k + j - 1) / arb.fac_ui(k)
        return S(co)
    CT = (2 * q).gamma() / (q.gamma() * (1 - q).gamma()); CS = (3 * q).gamma() * (1 + q).gamma() / (2 * q).gamma()
    half = arb(1) / 2
    cN1, cNQ, cS2 = half, half - q, half + q
    PN1s = [ps(j, cN1) for j in range(4)]; PNQs = [ps(j, cNQ) for j in range(4)]
    a0 = arb(N0) + half
    zt, zd = [], []
    for k in range(K1):
        s = 4 * q + k
        if abs(float(s.mid()) - 1) < 1e-12:
            zt.append(None); zd.append(None); continue
        ser = arb_series.zeta(arb_series([s, 1], prec=2), a0); co = ser.coeffs()
        zt.append(co[0]); zd.append(co[1])
    out = {}
    for l in ells:
        hs = arb(0)
        for n in range(N0):
            m = l + n
            hs += M2 * (e[m] * h[n]) ** 2 / 8 - (f[m] * g[n]) ** 2 * Rpoly(PA[m], PB[m], PN1[n], PNQ[n]) / 4
        ca, cb, c3 = l + q - half, l + 2 * q - half, l + 3 * q - half
        ET = (2 * (lr(ca, cb) + lr(cNQ, cN1))).exp(); ES = (2 * (lr(cb, c3) + lr(cN1, cS2))).exp()
        pa = [ps(j, ca) for j in range(4)]; pb = [ps(j, cb) for j in range(4)]
        Rp, P3 = Rpoly(pa, pb, PN1s, PNQs, logpart=True)
        s0 = (CS ** 2 * M2 / 8) * ES - (CT ** 2 / 4) * ET * Rp
        s1 = -(CT ** 2 / 4) * ET * P3
        c0 = s0.coeffs() + [arb(0)] * K1; c1 = s1.coeffs() + [arb(0)] * K1
        tl = arb(0)
        for k in range(K1):
            if zt[k] is None:
                assert abs(c0[k]) < arb(10) ** (-prec // 4) and abs(c1[k]) < arb(10) ** (-prec // 4), ('zeta(1) coefficient', c0[k], c1[k])
                continue
            tl += c0[k] * zt[k] - c1[k] * zd[k]
        out[l] = hs + tl
    return out
if __name__ == '__main__':
    import sys, mpmath as mp
    mp.mp.dps = 60
    v = spins(arb(1) / 4, [0, 1], 300, 800, 70)
    I0, I1 = [mp.mpf(v[l].mid().str(80, radius=False)) for l in (0, 1)]
    pi, G, z3, l2 = mp.pi, mp.catalan, mp.zeta(3), mp.log(2)
    A = pi + 4 * l2; U = mp.psi(2, mp.mpf(1) / 4)
    print('d=1 check', mp.nstr(-A * U / 4 + I0 + I1 - (128 * G ** 2 + 24 * pi ** 2 * G - 4 * pi ** 3 * l2 - 28 * (pi + 4 * l2) * z3), 3))
    print('I0', I0); print('I1', I1)
