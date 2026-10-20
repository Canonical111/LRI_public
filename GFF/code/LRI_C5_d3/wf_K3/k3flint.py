#!/usr/bin/env python3
"""K_3 = K_{d=3} from the residue series gs:Kseries (q = 3/4), in Arb ball arithmetic (python-flint).

  K_3 = -A U/4 + sum_{l>=0} (2l+1) I_l,      I_l = sum_{n>=0} [ M^2 S_{ln}^2/8 - T_{ln}^2 R_{ln}/4 ]   (n inside, l outside)

  * head   : l < L, n < N0, exact Pochhammer / polygamma recurrences (no special-function calls per term);
  * n-tail : for each l < L, the summand is expanded in u = 1/X, X = n + 1/2 (Bernoulli-polynomial forms of the
             Gamma-ratio and polygamma asymptotics, exact shifts), u^3 (s0(u) + s1(u) log X); summed with Hurwitz
             zeta and its s-derivative at a = N0 + 1/2;
  * l-tail : sum_{l>=L} from the centered Stirling expansion in x = (l+1/2)/2 + i nu of the spectral integrand
             <t^2 (R_tau - S_tau)> (gs:Kspectral / gs:Ksubtraction), with tau carried as an exact power series
             (the k+kb = 0 terms of R and S are identical and cancel, so no 1/tau pole is ever formed);
             K-tail = (F_3 + c* F_2)/4,  F_0 = F_1 = 0 is a check.
usage: k3flint.py PRECBITS L N0 KN KL [out.json]
"""
import sys, json, time
from flint import arb, acb, arb_series, ctx, fmpq

def main(prec, L, N0, KN, KL, out=None):
    ctx.prec = prec
    t0 = time.time()
    q = arb(3) / 4
    one = arb(1)
    def psi(j, x):
        x = arb(x)
        if j == 0:
            return x.digamma()
        return (-1) ** (j + 1) * arb.fac_ui(j) * arb(j + 1).zeta(x)
    Mc = -(1 - q).gamma() * (2 * q).gamma() ** 2 / (q * (3 * q).gamma())
    p1 = [psi(j, one) for j in range(5)]
    pq = [psi(j, q) for j in range(5)]
    p1q = [psi(j, 1 - q) for j in range(5)]
    cstar = p1[0] + psi(0, 2 * q)
    A = psi(0, 2 * q) + p1[0] - 2 * pq[0]
    U = pq[2]
    # ---------------- head sequences ----------------
    Mmax = L + N0
    f = [one]; e = [one]
    for m in range(Mmax):
        f.append(f[-1] * (q + m) / (2 * q + m)); e.append(e[-1] * (2 * q + m) / (3 * q + m))
    g = [one]; h = [one]
    for n in range(N0):
        g.append(g[-1] * (1 - q + n) / (n + 1)); h.append(h[-1] * (n + 1) / (1 + q + n))
    def polyseq(x0, cnt):
        """psi_j(x0 + k), k < cnt, j = 0..3 by upward recurrence"""
        cur = [psi(j, x0) for j in range(4)]
        seq = []
        for k in range(cnt):
            seq.append(list(cur))
            x = x0 + k
            for j in range(4):
                cur[j] = cur[j] + (-1) ** j * arb.fac_ui(j) / x ** (j + 1)
        return seq
    PA = polyseq(q, Mmax); PB = polyseq(2 * q, Mmax)
    PN1 = polyseq(one, N0); PNQ = polyseq(1 - q, N0)
    sg = [(-1) ** j for j in range(5)]
    def R_of(pa, pb, pn1, pnq):
        chi = [sg[j] * pnq[j] + pq[j] - sg[j] * p1q[j] for j in range(4)]
        lam = [None] + [pa[j - 1] - pb[j - 1] - sg[j] * chi[j - 1] + (1 + sg[j]) * p1[j - 1] - pn1[j - 1] for j in range(1, 5)]
        r = [lam[j + 1] / 2 + pb[j] + pn1[j] - (1 - sg[j]) * p1[j] for j in range(4)]
        l1, l2, l3, l4 = lam[1], lam[2], lam[3], lam[4]
        return ((r[0] - cstar) / 2 * (l1 ** 3 + 3 * l1 * l2 + l3) + 3 * r[1] * (l1 ** 2 + l2) / 4 - (l1 * r[2] + r[3]) / 4
                - l1 ** 4 / 12 + l1 ** 2 * l2 / 8 + 7 * l1 * l3 / 24 + l2 ** 2 / 8 + l4 / 12)
    M2 = Mc ** 2
    heads = []
    for l in range(L):
        s = arb(0)
        for n in range(N0):
            m = l + n
            T2 = (f[m] * g[n]) ** 2; S2 = (e[m] * h[n]) ** 2
            s += M2 * S2 / 8 - T2 * R_of(PA[m], PB[m], PN1[n], PNQ[n]) / 4
        heads.append(s)
    t1 = time.time()
    # ---------------- n-tail, per spin ----------------
    K1 = KN + 1
    ctx.cap = K1
    S = lambda c: arb_series(c, prec=K1)
    zero = S([0])
    Bcache = {}
    def bern(k, c):
        key = (k, str(c))
        if key not in Bcache:
            Bcache[key] = arb(c).bernoulli_poly(k)
        return Bcache[key]
    def lr(al, be):     # log Gamma(X+al) - log Gamma(X+be) - (al-be) log X, as series in u
        co = [arb(0)] + [(-1) ** (k + 1) * (bern(k + 1, al) - bern(k + 1, be)) / (k * (k + 1)) for k in range(1, K1)]
        return S(co)
    def ps(j, c):       # psi_j(X+c) minus (j==0) log X
        if j == 0:
            return S([arb(0)] + [-(-1) ** k * bern(k, c) / k for k in range(1, K1)])
        co = [arb(0)] * K1
        for k in range(0, K1 - j):
            co[k + j] = (-1) ** (j - 1) * (-1) ** k * bern(k, c) * arb.fac_ui(k + j - 1) / arb.fac_ui(k)
        return S(co)
    CT = (2 * q).gamma() / (q.gamma() * (1 - q).gamma())
    CS = (3 * q).gamma() * (1 + q).gamma() / (2 * q).gamma()
    cN1, cNQ, cS2 = arb(1) / 2, arb(-1) / 4, arb(5) / 4
    PN1s = [ps(j, cN1) for j in range(4)]; PNQs = [ps(j, cNQ) for j in range(4)]
    a0 = arb(N0) + arb(1) / 2
    zt = [arb(3 + k).zeta(a0) for k in range(K1)]
    zd = []
    for k in range(K1):
        ser = arb_series.zeta(arb_series([arb(3 + k), 1], prec=2), a0)
        zd.append(ser.coeffs()[1] if len(ser.coeffs()) > 1 else arb(0))
    ntails = []
    for l in range(L):
        ca, cb, c3 = l + q - arb(1) / 2, arb(l + 1), l + arb(7) / 4
        ET = (2 * (lr(ca, cb) + lr(cNQ, cN1))).exp()
        ES = (2 * (lr(cb, c3) + lr(cN1, cS2))).exp()
        pa = [ps(j, ca) for j in range(4)]; pb = [ps(j, cb) for j in range(4)]
        chi = [sg[j] * PNQs[j] + pq[j] - sg[j] * p1q[j] for j in range(4)]
        lam = [None] + [pa[j - 1] - pb[j - 1] - sg[j] * chi[j - 1] + (1 + sg[j]) * p1[j - 1] - PN1s[j - 1] for j in range(1, 5)]
        r = [lam[j + 1] / 2 + pb[j] + PN1s[j] - (1 - sg[j]) * p1[j] for j in range(4)]   # r0 without its 2 log X
        l1, l2, l3, l4 = lam[1], lam[2], lam[3], lam[4]
        P3 = l1 ** 3 + 3 * l1 * l2 + l3
        Rp = ((r[0] - cstar) / 2 * P3 + 3 * r[1] * (l1 ** 2 + l2) / 4 - (l1 * r[2] + r[3]) / 4
              - l1 ** 4 / 12 + l1 ** 2 * l2 / 8 + 7 * l1 * l3 / 24 + l2 ** 2 / 8 + l4 / 12)
        s0 = (CS ** 2 * M2 / 8) * ES - (CT ** 2 / 4) * ET * Rp
        s1 = -(CT ** 2 / 4) * ET * P3
        c0, c1 = s0.coeffs(), s1.coeffs()
        c0 += [arb(0)] * (K1 - len(c0)); c1 += [arb(0)] * (K1 - len(c1))
        ntails.append(sum((c0[k] * zt[k] - c1[k] * zd[k] for k in range(K1)), arb(0)))
    t2 = time.time()
    # ---------------- l-tail (tau series) ----------------
    ctx.cap = 4
    TS = lambda c: arb_series(c, prec=4)
    a8, b8 = arb(1) / 8, arb(7) / 8
    def bpoly_tau(k, c, slope):   # B_k(c + slope*tau) as tau-series
        co = []
        for j in range(4):
            if j > k:
                co.append(arb(0))
            else:
                co.append(arb.bin_uiui(k, j) * bern(k - j, c) * slope ** j)
        return TS(co)
    def Eseries(factors):
        cs = [TS([0])]
        for k in range(1, KL + 1):
            acc = TS([0])
            for (ac, asl), (bc, bsl), mult in factors:
                acc = acc + mult * (bpoly_tau(k + 1, ac, asl) - bpoly_tau(k + 1, bc, bsl))
            cs.append(acc * ((-1) ** (k + 1)) / (k * (k + 1)))
        E = [TS([1])]
        for k in range(1, KL + 1):
            acc = TS([0])
            for j in range(1, k + 1):
                acc = acc + j * cs[j] * E[k - j]
            E.append(acc / k)
        return E
    z0 = arb(0)
    t2f = [((a8, z0), (b8, z0), 2)]
    Rx = t2f + [((a8, z0), (a8, arb(1)), 1)]
    Rxb = t2f + [((b8, arb(-1)), (b8, z0), 1)]
    Sx = t2f + [((a8, arb(-1) / 4), (a8, z0), 2), ((b8, z0), (b8, arb(1) / 4), 2)]
    ER, ERb, ES_ = Eseries(Rx), Eseries(Rxb), Eseries(Sx)
    P = TS([arb(3) / 2, 1])
    G = [(P + k).rgamma() for k in range(KL + 1)]
    aL = arb(L) + arb(1) / 2
    Ft = TS([0])
    for s in range(1, KL + 1):
        Zs = (2 * P + (s - 1)).gamma() * arb_series.zeta(2 * P + (s - 2), aL)
        conv = TS([0])
        for k in range(0, s + 1):
            kb = s - k
            conv = conv + G[k] * G[kb] * (ER[k] * ERb[kb] - ES_[k] * ES_[kb])
        Ft = Ft + Zs * conv
    pref = (arb(3) / 2).gamma() ** 2
    Ft = 2 * pref * Ft
    Fc = Ft.coeffs() + [arb(0)] * 4
    ltail = (Fc[3] + cstar * Fc[2]) / 4
    t3 = time.time()
    body = sum(((2 * l + 1) * (heads[l] + ntails[l]) for l in range(L)), arb(0))
    K3 = -A * U / 4 + body + ltail
    rec = dict(prec=prec, L=L, N0=N0, KN=KN, KL=KL, K3=K3.str(radius=True, more=True) if False else K3.mid().str(int(prec * 0.30103) + 5, radius=False),
               K3_rad=K3.rad().str(5, radius=False), ltail=ltail.mid().str(40, radius=False), F0=Fc[0].mid().str(5, radius=False), F1=Fc[1].mid().str(5, radius=False),
               last_ntail_spin=ntails[-1].mid().str(10, radius=False), seconds=dict(head=t1 - t0, ntail=t2 - t1, ltail=t3 - t2))
    if out:
        json.dump(rec, open(out, 'w'), indent=1)
    return K3, rec

if __name__ == '__main__':
    a = sys.argv[1:]
    prec, L, N0, KN, KL = map(int, a[:5])
    K3, rec = main(prec, L, N0, KN, KL, a[5] if len(a) > 5 else None)
    for k, v in rec.items():
        print(k, v)
