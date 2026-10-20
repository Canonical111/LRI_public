#!/usr/bin/env python3
"""Independent numerical probe of Lemma G (review key: lemmaG-numeric).

Nothing is imported from foundation/, K_general/, specialize/, L/, Z/ or the other review folders.
Only mpmath.  No mpmath.zeta(s, a) anywhere.

Object (lemmaG_statement.md):
    f_g(w) = Gamma(w)/Gamma(w+g)
    T_l(z) = prod_i f_{g_i}(l+sigma+alpha_i+z) f_{g_i}(beta_i-z)
    S(t)   = sum_{l>=0} d_l sum_{n in Z} T_l(n+t),      sum_l d_l x^l = (1+x)(1-x)^{1-d}
    D(t)   = prod_i sin pi(t+sigma+alpha_i) sin pi(t-beta_i),   Xi = D S = sum_k c_k e^{2 pi i k t}.

Method (own design).  Put m = l+n (left index).  The (l,n) lattice splits into
    right  n>=0            : S_R = rho_B * sum_{n,l>=0} U_R(n) A(n+l) d_l
    middle n<=-1, m>=0     : S_M = sum_{j,k>=0} B(-1-j) d_{j+k+1} A(k)
    left   m<=-1           : S_L = rho_A * sum_{p,l>=0} U_L(p) B(-1-p-l) d_l
with A(m)=prod f_{g_i}(m+a_i), a_i=sigma+alpha_i+t, B(n)=prod f_{g_i}(beta_i-t-n), and the reflected
sequences U_R(n)=prod f_{g_i}(n+1-beta_i-g_i+t), U_L(p)=prod f_{g_i}(p+2-a_i-g_i),
rho_B=prod sin pi(beta_i+g_i-t)/sin pi(beta_i-t), rho_A=prod sin pi(a_i+g_i)/sin pi(a_i).
Every part is a quadrant sum Q=sum_{p,q>=0} U(p)V(p+q)W(q) of three sequences that are analytic for
Re >= K.  Q = head (p,q<K, exact) + two lines (one index <K, exact; other by Abel-Plana) + corner
(tensor Abel-Plana in both indices).  Abel-Plana is exact (no Bernoulli remainder, no derivatives):
    sum_{n>=0} f(K+n) = int_K^inf f + f(K)/2 + i int_0^inf [f(K+iy)-f(K-iy)]/(e^{2 pi y}-1) dy.
The corner double integral over [K,inf)^2 is split along the diagonal so every inner integral has
one scale; [K,inf) integrals use x=K/u and a tanh-sinh rule whose left truncation is set by the known
endpoint exponent; the y-integrals use composite Gauss-Legendre panels.
"""
import bisect
import math
import mpmath as mp
from mpmath.libmp import mpc_add, mpc_mul, mpf_add, mpf_mul, round_nearest, fzero

# ======================================================================================
# log of products of Gamma ratios and linear factors
# ======================================================================================


class LogProd:
    """L(z) = const + sum_i [logGamma(z+a_i) - logGamma(z+b_i)] + sum_j e_j log(z+c_j)   (mod 2 pi i).
    Only exp(L) is ever used.  Large |z|: asymptotic series
        logG(z+a)-logG(z+b) = (a-b) log z + sum_k (-1)^{k+1} (B_{k+1}(a)-B_{k+1}(b)) / (k(k+1)) z^{-k},
        log(z+c) = log z + sum_k (-1)^{k+1} c^k/(k z^k)."""

    NK = 64

    def __init__(self, pairs, lins=(), const=0):
        self.pairs = [(mp.mpmathify(a), mp.mpmathify(b)) for a, b in pairs]
        self.lins = [(mp.mpmathify(c), int(e)) for c, e in lins]
        self.const = mp.mpmathify(const)
        self.lead = mp.fsum([a - b for a, b in self.pairs]) + sum(e for _, e in self.lins)
        dps = mp.mp.dps
        with mp.extradps(30):
            C = []
            for k in range(1, self.NK + 4):
                s = mp.mpf(0)
                sg = (-1) ** (k + 1)
                for a, b in self.pairs:
                    s += sg * (mp.bernpoly(k + 1, a) - mp.bernpoly(k + 1, b)) / (k * (k + 1))
                for c, e in self.lins:
                    s += e * sg * c ** k / k
                C.append(s)
        self.C = [+c for c in C[:self.NK]]
        # adaptive truncation: use the first n terms when |z| > thr[n] (first omitted terms below 10^-(dps+4))
        eps = 10.0 ** (-(dps + 4))
        self.thr = []
        for n in range(4, self.NK + 1):
            big = max(float(abs(c)) for c in C[n:n + 3])
            zt = (big / eps) ** (1.0 / (n + 1)) if big > 0 else 1.0
            self.thr.append((zt, n))
        self.thr.sort(key=lambda x: x[0])        # increasing threshold
        self.ZA = max(self.thr[0][0], 12.0)
        self._zts = [zt for zt, n in self.thr]
        pm, cur = [], self.NK
        for zt, n in self.thr:
            cur = min(cur, n)
            pm.append(cur)                       # smallest admissible n among thresholds <= this one
        self._nmin = pm
        self.dps = dps
        self._Cc = [(c._mpc_ if isinstance(c, mp.mpc) else (c._mpf_, fzero)) for c in self.C]
        self._real = all(isinstance(c, mp.mpf) for c in self.C)
        self._Cr = [c._mpf_ for c in self.C] if self._real else None

    def __call__(self, z):
        az = abs(z)
        azf = float(az)
        if azf > self.ZA:
            n = self._nmin[bisect.bisect_left(self._zts, azf) - 1]
            zi = 1 / z
            prec = mp.mp.prec + 10
            if self._real and isinstance(z, mp.mpf):
                zr = zi._mpf_
                acc = fzero
                for c in reversed(self._Cr[:n]):
                    acc = mpf_mul(mpf_add(acc, c, prec, round_nearest), zr, prec, round_nearest)
                s = mp.make_mpf(acc)
            else:
                zc = zi._mpc_ if isinstance(zi, mp.mpc) else (zi._mpf_, fzero)
                acc = (fzero, fzero)
                for c in reversed(self._Cc[:n]):
                    acc = mpc_mul(mpc_add(acc, c, prec, round_nearest), zc, prec, round_nearest)
                s = mp.make_mpc(acc)
            return self.const + self.lead * mp.log(z) + s
        ex = int(math.log10(float(az) + 2.0)) + 6
        with mp.extradps(ex):
            s = 0
            for a, b in self.pairs:
                s += mp.loggamma(z + a) - mp.loggamma(z + b)
            for c, e in self.lins:
                s += e * mp.log(z + c)
        return s + self.const

    def val(self, z):
        return mp.exp(self(z))

    def ratio(self, x):
        """exp(L(x+1)-L(x)) exactly (rational)."""
        r = 1
        for a, b in self.pairs:
            r *= (x + a) / (x + b)
        for c, e in self.lins:
            r *= ((x + 1 + c) / (x + c)) ** e
        return r


def dseq_log(dm, shift=0):
    """log d(x+shift), d(x) = Gamma(x+dm-2)(2x+dm-2)/(Gamma(dm-1)Gamma(x+1)): the analytic continuation of the
    coefficients of (1+z)(1-z)^{1-dm}  (d_x = e_x + e_{x-1}, e_x=(dm-1)_x/x!)."""
    dm = mp.mpmathify(dm)
    return LogProd([(dm - 2 + shift, 1 + shift)], [((dm - 2) / 2 + shift, 1)], mp.log(2) - mp.loggamma(dm - 1))


# ======================================================================================
# quadrature rules
# ======================================================================================
_RULES = {}


def ts01(cp1, D, h):
    """tanh-sinh nodes for int_0^1 F(u) du with F ~ u^{cp1-1} (possibly x oscillating powers) at u->0 and F
    regular at u=1.  Left truncation chosen so that u_min^{cp1} < 10^{-D}."""
    cp1 = max(float(cp1), 0.02)
    key = ('ts', mp.mp.dps, round(cp1, 8), D, str(h))
    if key in _RULES:
        return _RULES[key]
    h = mp.mpf(h)
    L = D * math.log(10.0)
    tmin = -math.asinh(L / (math.pi * cp1)) - 2 * float(h)
    tmax = math.asinh(L / math.pi) + 2 * float(h)
    out = []
    for k in range(int(math.floor(tmin / float(h))), int(math.ceil(tmax / float(h))) + 1):
        tau = k * h
        s = mp.pi * mp.sinh(tau)
        e = mp.exp(-s)
        u = 1 / (1 + e)
        w = h * mp.pi * mp.cosh(tau) * e / (1 + e) ** 2
        out.append((u, w))
    _RULES[key] = out
    return out


def gauss_legendre(n):
    key = ('gl', n, mp.mp.dps)
    if key in _RULES:
        return _RULES[key]
    out = []
    with mp.extradps(20):
        eps = mp.mpf(10) ** (-mp.mp.dps - 5)
        for i in range(1, n + 1):
            x = mp.cos(mp.pi * (i - mp.mpf(1) / 4) / (n + mp.mpf(1) / 2))
            for _ in range(200):
                p0, p1 = mp.mpf(1), x
                for k in range(2, n + 1):
                    p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
                dp = n * (x * p1 - p0) / (x * x - 1)
                dx = p1 / dp
                x -= dx
                if abs(dx) < eps:
                    break
            p0, p1 = mp.mpf(1), x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            out.append((x, 2 / ((1 - x * x) * dp * dp)))
    out = [(+x, +w) for x, w in out]
    _RULES[key] = out
    return out


def jrule(D, ngl):
    """nodes y_j>0 and weights omega_j = w_j/(e^{2 pi y_j}-1) for int_0^inf g(y) dy/(e^{2 pi y}-1)."""
    key = ('j', mp.mp.dps, D, ngl)
    if key in _RULES:
        return _RULES[key]
    ymax = (D * math.log(10.0) + 12) / (2 * math.pi)
    edges = [0, 0.4, 1.0, 1.9, 3.2, 5.0, 7.5, 11.0]
    edges = [e for e in edges if e < ymax - 0.5] + [ymax]
    gl = gauss_legendre(ngl)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        a, b = mp.mpf(a), mp.mpf(b)
        c, hw = (a + b) / 2, (b - a) / 2
        for x, w in gl:
            y = c + hw * x
            out.append((y, hw * w / mp.expm1(2 * mp.pi * y)))
    _RULES[key] = out
    return out


# ======================================================================================
# Abel-Plana and the quadrant sum
# ======================================================================================


class Cfg:
    def __init__(self, K=12, D=44, hden=32, ngl=28):
        self.K, self.D, self.hden, self.ngl = K, D, hden, ngl
        self.h = mp.mpf(1) / hden

    def __repr__(self):
        return 'Cfg(K=%d,D=%d,h=1/%d,ngl=%d)' % (self.K, self.D, self.hden, self.ngl)


def _re(x):
    return x.real if isinstance(x, mp.mpc) else x


def J_apply(f, K, JR, real):
    if real:
        return -2 * mp.fsum(w * mp.im(f(mp.mpc(K, y))) for y, w in JR)
    return mp.mpc(0, 1) * mp.fsum(w * (f(mp.mpc(K, y)) - f(mp.mpc(K, -y))) for y, w in JR)


def I_apply(f, K, rule):
    return mp.fsum(w * (K / u ** 2) * f(K / u) for u, w in rule)


class Quadrant:
    """Q = sum_{p,q>=0} U(p) V(p+q) W(q); LU, LV, LW are LogProd; eU, eV, eW real leading exponents.
    real=True: U, V, W real on the real axis (Schwarz reflection used for the y-integrals)."""

    def __init__(self, LU, LV, LW, eU, eV, eW, real):
        self.LU, self.LV, self.LW = LU, LV, LW
        self.eU, self.eV, self.eW = float(eU), float(eV), float(eW)
        self.real = real

    def total(self, cfg, details=False, cont=False):
        """cont=True: the two outer corner integrals are written as int_K^inf [F(x) - c I x^Lam] dx + analytic term,
        i.e. the analytic continuation in the parameters past 2 Re G = d (only the leading power is subtracted)."""
        LU, LV, LW, real = self.LU, self.LV, self.LW, self.real
        exp, fsum, mpc = mp.exp, mp.fsum, mp.mpc
        K = cfg.K
        Kf = mp.mpf(K)
        D, h = cfg.D, cfg.h
        if real:
            ev = lambda lg: _re(exp(lg))
        else:
            ev = exp
        cUV = -(self.eU + self.eV) - 1
        cVW = -(self.eV + self.eW) - 1
        cout = -(self.eU + self.eV + self.eW) - 2
        R_UV = ts01(cUV, D, h)
        R_VW = ts01(cVW, D, h)
        R_out = ts01(cout + (1 if cont else 0), D, h)
        JR = jrule(D, cfg.ngl)
        if cont:
            lamU, lamV, lamW = LU.lead, LV.lead, LW.lead
            cc = mp.exp(LU.const + LV.const + LW.const)
            Lam = lamU + lamV + lamW + 1
            mu, nu = -lamV - lamW - 1, -lamU - lamV - 1
            I_A = mp.hyp2f1(-lamV, mu, mu + 1, -1) / mu
            I_B = mp.hyp2f1(-lamV, nu, nu + 1, -1) / nu
            subA = lambda x: cc * I_A * mp.power(x, Lam)
            subB = lambda x: cc * I_B * mp.power(x, Lam)
            analytic = cc * (I_A + I_B) * (-mp.power(Kf, Lam + 1) / (Lam + 1))
            if real:
                subA0, subB0 = subA, subB
                subA = lambda x: _re(subA0(x))
                subB = lambda x: _re(subB0(x))
                analytic = _re(analytic)
        else:
            subA = subB = lambda x: 0
            analytic = 0
        ys = [y for y, _ in JR]
        om = [w for _, w in JR]
        nJ = len(ys)
        zp = [mpc(Kf, y) for y in ys]
        zm = [mpc(Kf, -y) for y in ys]

        def Japply(vals_p, vals_m):
            """i sum om [f(K+iy)-f(K-iy)]; vals_m ignored when real."""
            if real:
                return -2 * fsum(w * mp.im(v) for w, v in zip(om, vals_p))
            return mpc(0, 1) * fsum(w * (a - b) for w, a, b in zip(om, vals_p, vals_m))

        # ---- head
        Uh = [ev(LU(mp.mpf(p))) for p in range(K)]
        Wh = [ev(LW(mp.mpf(q))) for q in range(K)]
        Vh = [ev(LV(mp.mpf(m))) for m in range(2 * K - 1)]
        head = fsum(Uh[p] * fsum(Vh[p + q] * Wh[q] for q in range(K)) for p in range(K))

        def run(x, coef):
            """sum_{j<K} coef[j] V(x+j)/V(x), by the exact ratio recurrence."""
            v = 1
            acc = [coef[0]]
            for j in range(1, K):
                v = v * LV.ratio(x + j - 1)
                acc.append(coef[j] * v)
            return fsum(acc)

        # ---- line A: p<K, q>=K : gA(q) = W(q) V(q) sum_p Uh[p] V(q+p)/V(q)
        # ---- line B: q<K, p>=K : gB(p) = U(p) V(p) sum_q Wh[q] V(p+q)/V(p)
        nodes_VW = [(Kf / u, w * Kf / u ** 2) for u, w in R_VW]
        nodes_UV = [(Kf / u, w * Kf / u ** 2) for u, w in R_UV]

        def gA(q, e):
            return e(LW(q) + LV(q)) * run(q, Uh)

        def gB(p, e):
            return e(LU(p) + LV(p)) * run(p, Wh)

        lineA = (fsum(wx * gA(x, ev) for x, wx in nodes_VW) + gA(Kf, ev) / 2
                 + Japply([gA(z, exp) for z in zp], None if real else [gA(z, exp) for z in zm]))
        lineB = (fsum(wx * gB(x, ev) for x, wx in nodes_UV) + gB(Kf, ev) / 2
                 + Japply([gB(z, exp) for z in zp], None if real else [gB(z, exp) for z in zm]))

        # ---- corner (1): I_p I_q, split along the diagonal (single scale in every inner integral)
        IA = []
        for u, w in R_out:
            p = Kf / u
            inner = fsum(wv * (p / v ** 2) * ev(LV(p + p / v) + LW(p / v)) for v, wv in R_VW)
            IA.append(w * (Kf / u ** 2) * (ev(LU(p)) * inner - subA(p)))
        IB = []
        for u, w in R_out:
            q = Kf / u
            inner = fsum(wv * (q / v ** 2) * ev(LU(q / v) + LV(q + q / v)) for v, wv in R_UV)
            IB.append(w * (Kf / u ** 2) * (ev(LW(q)) * inner - subB(q)))
        II = fsum(IA) + fsum(IB) + analytic

        lUK, lWK = LU(Kf), LW(Kf)
        lU_UV = [LU(x) for x, _ in nodes_UV]
        lW_VW = [LW(x) for x, _ in nodes_VW]
        # (2) E_p I_q, (3) I_p E_q, (4) E_p E_q
        EI = fsum(wx * ev(lUK + LV(Kf + x) + lw) for (x, wx), lw in zip(nodes_VW, lW_VW)) / 2
        IE = fsum(wx * ev(lu + LV(x + Kf) + lWK) for (x, wx), lu in zip(nodes_UV, lU_UV)) / 2
        EE = ev(lUK + LV(2 * Kf) + lWK) / 4
        # (5) E_p J_q, (6) J_p E_q
        EJ = Japply([exp(lUK + LV(Kf + z) + LW(z)) for z in zp],
                    None if real else [exp(lUK + LV(Kf + z) + LW(z)) for z in zm]) / 2
        JE = Japply([exp(LU(z) + LV(z + Kf) + lWK) for z in zp],
                    None if real else [exp(LU(z) + LV(z + Kf) + lWK) for z in zm]) / 2

        # (7) I_p J_q : q = z complex near K, integral over p ; (8) J_p I_q
        def lam_q(z):
            lw = LW(z)
            return fsum(wx * exp(lu + LV(x + z) + lw) for (x, wx), lu in zip(nodes_UV, lU_UV))

        def lam_p(z):
            lu = LU(z)
            return fsum(wx * exp(lu + LV(z + x) + lw) for (x, wx), lw in zip(nodes_VW, lW_VW))

        IJ = Japply([lam_q(z) for z in zp], None if real else [lam_q(z) for z in zm])
        JI = Japply([lam_p(z) for z in zp], None if real else [lam_p(z) for z in zm])

        # (9) J_p J_q = - sum om_j om_k [phi(++) - phi(+-) - phi(-+) + phi(--)]
        lUp = [LU(z) for z in zp]
        lWp = [LW(z) for z in zp]
        acc = []
        if real:
            for j in range(nJ):
                for k in range(nJ):
                    fpp = exp(lUp[j] + LV(mpc(2 * Kf, ys[j] + ys[k])) + lWp[k])
                    fpm = exp(lUp[j] + LV(mpc(2 * Kf, ys[j] - ys[k])) + mp.conj(lWp[k]))
                    acc.append(om[j] * om[k] * 2 * (mp.re(fpp) - mp.re(fpm)))
        else:
            lUm = [LU(z) for z in zm]
            lWm = [LW(z) for z in zm]
            Vpm = [[LV(mpc(2 * Kf, ys[j] - ys[k])) for k in range(nJ)] for j in range(nJ)]
            for j in range(nJ):
                for k in range(nJ):
                    br = (exp(lUp[j] + LV(mpc(2 * Kf, ys[j] + ys[k])) + lWp[k])
                          - exp(lUp[j] + Vpm[j][k] + lWm[k])
                          - exp(lUm[j] + Vpm[k][j] + lWp[k])
                          + exp(lUm[j] + LV(mpc(2 * Kf, -ys[j] - ys[k])) + lWm[k]))
                    acc.append(om[j] * om[k] * br)
        JJ = -fsum(acc)

        corner = II + EI + IE + EE + EJ + JE + IJ + JI + JJ
        tot = head + lineA + lineB + corner
        if details:
            return tot, dict(head=head, lineA=lineA, lineB=lineB, II=II, EI=EI, IE=IE, EE=EE, EJ=EJ, JE=JE,
                             IJ=IJ, JI=JI, JJ=JJ)
        return tot


# ======================================================================================
# the Lemma G periodization
# ======================================================================================


class LemmaG:
    """Lemma G object.  beta defaults to per-factor balance (B): beta_i = d/2 - sigma - alpha_i - g_i.
    dmult: dimension used in the multiplicities (default d)."""

    def __init__(self, d, sigma, g, alpha, beta=None, dmult=None):
        self.d = mp.mpmathify(d)
        self.sigma = mp.mpmathify(sigma)
        self.g = [mp.mpmathify(x) for x in g]
        self.alpha = [mp.mpmathify(x) for x in alpha]
        self.r = len(self.g)
        if beta is None:
            beta = [self.d / 2 - self.sigma - a - gg for a, gg in zip(self.alpha, self.g)]
        self.beta = [mp.mpmathify(x) for x in beta]
        self.dm = self.d if dmult is None else mp.mpmathify(dmult)
        self.G = mp.fsum(self.g)
        self.realpar = all(mp.im(x) == 0 for x in [self.sigma, self.dm] + self.g + self.alpha + self.beta)

    def balance_defects(self):
        return [self.sigma + a + b + gg - self.d / 2 for a, b, gg in zip(self.alpha, self.beta, self.g)]

    def condC(self):
        al = mp.re(self.G)
        d = self.d
        return al, max(d / 2, d - 1, mp.mpf(1) / 2)

    def classes(self):
        """t-classes (mod 1) to avoid: poles of S and the 0*inf points of the reflected forms."""
        out = []
        for a, b, gg in zip(self.alpha, self.beta, self.g):
            out += [-(self.sigma + a), b, b + gg, -(self.sigma + a + gg)]
        return out

    def Dfac(self, t):
        v = 1
        for a, b in zip(self.alpha, self.beta):
            v *= mp.sinpi(t + self.sigma + a) * mp.sinpi(t - b)
        return v

    def parts(self, t, cfg, which=('right', 'left', 'middle'), cont=False):
        t = mp.mpmathify(t)
        real = self.realpar and mp.im(t) == 0
        if real:
            t = mp.re(t)
        s, g, al, be = self.sigma, self.g, self.alpha, self.beta
        a = [s + x + t for x in al]
        eG = -float(mp.re(self.G))
        ed = float(mp.re(self.dm)) - 2
        dlog = dseq_log(self.dm)
        dlog1 = dseq_log(self.dm, shift=1)
        A = LogProd([(ai, ai + gi) for ai, gi in zip(a, g)])
        UR = LogProd([(1 - bi - gi + t, 1 - bi + t) for bi, gi in zip(be, g)])
        UL = LogProd([(2 - ai - gi, 2 - ai) for ai, gi in zip(a, g)])
        Bn = LogProd([(bi - t + 1, bi - t + 1 + gi) for bi, gi in zip(be, g)])
        rhoB = 1
        for bi, gi in zip(be, g):
            rhoB *= mp.sinpi(bi + gi - t) / mp.sinpi(bi - t)
        rhoA = 1
        for ai, gi in zip(a, g):
            rhoA *= mp.sinpi(ai + gi) / mp.sinpi(ai)
        out = {}
        if 'right' in which:
            out['right'] = rhoB * Quadrant(UR, A, dlog, eG, eG, ed, real).total(cfg, cont=cont)
        if 'left' in which:
            out['left'] = rhoA * Quadrant(UL, Bn, dlog, eG, eG, ed, real).total(cfg, cont=cont)
        if 'middle' in which:
            out['middle'] = Quadrant(Bn, dlog1, A, eG, ed, eG, real).total(cfg, cont=cont)
        return out

    def S(self, t, cfg):
        p = self.parts(t, cfg)
        return p['right'] + p['left'] + p['middle']

    def Xi(self, t, cfg):
        return self.Dfac(t) * self.S(t, cfg)


def choose_t0(model, N, imag=0, grid=400, avoid=None):
    """t_j = t0 + j/N; maximise the minimum |sin pi(t_j - c)| over all classes c.
    avoid: a previous t0; candidates within 0.3/N of it (mod 1/N) are skipped (independent node set)."""
    cls = model.classes()
    best, bt = -1, None
    for i in range(grid):
        x = mp.mpf(i) / (grid * N) + mp.mpf(1) / (7 * grid * N)
        if avoid is not None:
            dx = (x - mp.re(avoid)) * N
            dx = dx - mp.floor(dx + mp.mpf(1) / 2)
            if abs(dx) < mp.mpf('0.3'):
                continue
        t0 = mp.mpc(x, imag) if imag else x
        m = min(abs(mp.sinpi(t0 + mp.mpf(j) / N - c)) for j in range(N) for c in cls)
        if m > best:
            best, bt = m, t0
    return bt, best


def dft(ts, xs, kmax):
    N = len(ts)
    return {k: mp.fsum(xs[j] * mp.expjpi(-2 * k * ts[j]) for j in range(N)) / N for k in range(-kmax, kmax + 1)}
