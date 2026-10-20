#!/usr/bin/env python3
"""Independent direct evaluation of the periodized balanced wheel (review key: topmode-numeric).

Definitions (taken from the note, gs:spectrum / gs:balancedWheel, and foundation eq. (2.1)-(3.1)):
  q = d/4, sigma = b/2, g = spoke parameter (balanced: g = d/2 - sigma),
  g_l(s) = Gamma(a_l+s)Gamma(a_l-s) / (Gamma(a_l+g+s)Gamma(a_l+g-s)),  a_l = l/2 + sigma/2,
  S_r(t) = sum_{l>=0} d_l sum_{n in Z} g_l(a_l+n+t)^r,   D_b(t) = sin(pi t) sin(pi(t+sigma)),
  Xi_r(t) = D_b(t)^r S_r(t).

The (l,n) lattice is split into right (n>=0), middle (-l<=n<=-1) and left (n<=-l-1) parts. The left
part is the right part at 1-sigma-t (evenness of g_l). Every part is a quadrant sum

        T[U,V,W] = sum_{p,q>=0} U(p) V(p+q) W(q),

evaluated exactly on [0,K)^2 and with a tensor-product Euler-Maclaurin tail. The EM integrals are
done by tanh-sinh quadrature (2-D integral split along the diagonal so every inner integral has a
single scale), the EM boundary derivatives by Cauchy circles.

Nothing from ../foundation, ../specialize, ../L, ../Z is imported or copied.
"""
import mpmath as mp

# ----------------------------------------------------------------------------------------------
# log Gamma(z+a) - log Gamma(z+b): only exp(integer * this) is ever used, so the branch is irrelevant.
# For |z| > ZBIG an asymptotic series (no cancellation); else loggamma with guard digits.
# ----------------------------------------------------------------------------------------------
ZBIG = 2000


class LGR:
    def __init__(self, a, b):
        self.a = mp.mpmathify(a)
        self.b = mp.mpmathify(b)
        self._c = None
        self._cdps = None

    def _coef(self):
        if self._c is None or self._cdps != mp.mp.dps:
            self._c = [(-1) ** (k + 1) * (mp.bernpoly(k + 1, self.a) - mp.bernpoly(k + 1, self.b)) / (k * (k + 1))
                       for k in range(1, 41)]
            self._cdps = mp.mp.dps
        return self._c

    def __call__(self, z):
        az = abs(z)
        if az > ZBIG:
            c = self._coef()
            s = (self.a - self.b) * mp.log(z)
            zi = 1 / z
            zp = zi
            tol = mp.mpf(10) ** (-mp.mp.dps - 8)
            small = 0
            for k, ck in enumerate(c):
                term = ck * zp
                s += term
                # stop only after two consecutive negligible terms: for symmetric parameters (e.g. a=1/2,
                # b=1) every other coefficient B_{k+1}(a)-B_{k+1}(b) vanishes exactly (bug fixed 2026-10-03)
                small = small + 1 if abs(term) < tol else 0
                if small >= 2 and k >= 3:
                    break
                zp *= zi
            return s
        extra = int(mp.log10(az + 2)) + 6
        with mp.extradps(extra):
            return mp.loggamma(z + self.a) - mp.loggamma(z + self.b)


# ----------------------------------------------------------------------------------------------
# tanh-sinh on (0,1), endpoint singularity allowed at 0 (x^c, Re c > -1) and at 1.
# ----------------------------------------------------------------------------------------------
_TS_CACHE = {}


def ts_rule(h, digits, cp1):
    """nodes/weights for int_0^1 f; cp1 = (Re c + 1) lower bound of the endpoint exponent at 0."""
    key = (mp.mp.dps, mp.mpf(h), digits, mp.mpf(cp1))
    if key in _TS_CACHE:
        return _TS_CACHE[key]
    h = mp.mpf(h)
    L = mp.log(10) * (digits + 3)
    Tp = mp.asinh(L / mp.pi) + h            # right end (regular or weakly singular)
    Tm = mp.asinh(L / (mp.pi * mp.mpf(cp1))) + h
    kmin = int(mp.floor(-Tm / h))
    kmax = int(mp.ceil(Tp / h))
    out = []
    for k in range(kmin, kmax + 1):
        tau = k * h
        e = mp.exp(-mp.pi * mp.sinh(tau))
        x = 1 / (1 + e)
        w = h * mp.pi * mp.cosh(tau) * x * (e / (1 + e))
        out.append((x, w))
    _TS_CACHE[key] = out
    return out


def ts_integrate(f, rule):
    return mp.fsum(w * f(x) for x, w in rule)


# ----------------------------------------------------------------------------------------------
# Taylor coefficients by Cauchy circle
# ----------------------------------------------------------------------------------------------
def cauchy_coeffs(fvals, rho, nmax):
    M = len(fvals)
    out = []
    for m in range(nmax + 1):
        s = mp.fsum(fvals[j] * mp.expjpi(-2 * mp.mpf(j * m) / M) for j in range(M))
        out.append(s / (M * mp.mpf(rho) ** m))
    return out


def circle_points(z0, rho, M):
    return [z0 + rho * mp.expjpi(2 * mp.mpf(j) / M) for j in range(M)]


# Bernoulli factors B_{2k}/(2k)
def em_factors(P):
    return [mp.bernoulli(2 * k) / (2 * k) for k in range(1, P + 1)]


# ----------------------------------------------------------------------------------------------
# quadrant sum T = sum_{p,q>=0} U(p) V(p+q) W(q)
# ----------------------------------------------------------------------------------------------
class Quadrant:
    """lnU, lnV, lnW: logs of the smooth continuations (any complex argument with Re >~ K/2).
    ratV(x) = V(x+1)/V(x). eU,eV,eW: leading power exponents (real parts used for node ranges)."""

    def __init__(self, lnU, lnV, lnW, ratV, eU, eV, eW):
        self.lnU, self.lnV, self.lnW, self.ratV = lnU, lnV, lnW, ratV
        self.eU, self.eV, self.eW = [mp.re(mp.mpmathify(e)) for e in (eU, eV, eW)]

    def total(self, K=40, P=10, h=mp.mpf(1) / 32, M=64, digits=None, details=False):
        if digits is None:
            digits = mp.mp.dps
        lnU, lnV, lnW, ratV = self.lnU, self.lnV, self.lnW, self.ratV
        E = em_factors(P)
        nder = 2 * P - 1
        rho = mp.mpf(K) / 3
        # ---------------- direct block
        U = [mp.exp(lnU(p)) for p in range(K)]
        W = [mp.exp(lnW(q)) for q in range(K)]
        V = [mp.exp(lnV(m)) for m in range(2 * K - 1)]
        S_dir = mp.fsum(U[p] * mp.fsum(V[p + q] * W[q] for q in range(K)) for p in range(K))

        # V(x+j), j=0..n-1 by recurrence from V(x)
        def Vrun(x, n):
            v = mp.exp(lnV(x))
            out = [v]
            for j in range(n - 1):
                v = v * ratV(x + j)
                out.append(v)
            return out

        # ---------------- line Q: p<K, q>=K :  f_Q(q) = W(q) * sum_{p<K} U[p] V(p+q)
        def fQ(qq):
            vr = Vrun(qq, K)
            return mp.exp(lnW(qq)) * mp.fsum(U[p] * vr[p] for p in range(K))

        # ---------------- line P: q<K, p>=K :  f_P(p) = U(p) * sum_{q<K} W[q] V(p+q)
        def fP(pp):
            vr = Vrun(pp, K)
            return mp.exp(lnU(pp)) * mp.fsum(W[q] * vr[q] for q in range(K))

        def em_line(f, cp1):
            rule = ts_rule(h, digits, max(cp1, mp.mpf('0.02')))
            Kf = mp.mpf(K)
            I = ts_integrate(lambda u: (Kf / u ** 2) * f(Kf / u), rule)
            cf = cauchy_coeffs([f(z) for z in circle_points(Kf, rho, M)], rho, nder)
            corr = cf[0] / 2 - mp.fsum(E[k - 1] * cf[2 * k - 1] for k in range(1, P + 1))
            return I + corr, I, corr

        cQ = -(self.eV + self.eW) - 1
        cP = -(self.eU + self.eV) - 1
        LQ = em_line(fQ, cQ)
        LP = em_line(fP, cP)

        # ---------------- corner p>=K, q>=K : tensor EM
        Kf = mp.mpf(K)

        def F(pp, qq):
            return mp.exp(lnU(pp) + lnV(pp + qq) + lnW(qq))

        cu_out = -(self.eU + self.eV + self.eW) - 2           # outer exponent (+1)
        cvA = -(self.eV + self.eW) - 1                        # region A inner (+1)
        cvB = -(self.eU + self.eV) - 1                        # region B inner (+1)
        rule_out = ts_rule(h, digits, max(cu_out, mp.mpf('0.02')))
        rule_A = ts_rule(h, digits, max(cvA, mp.mpf('0.02')))
        rule_B = ts_rule(h, digits, max(cvB, mp.mpf('0.02')))

        def innerA(p):
            # int_p^inf V(p+q) W(q) dq,  q = p/v
            return ts_integrate(lambda v: (p / v ** 2) * mp.exp(lnV(p + p / v) + lnW(p / v)), rule_A)

        def innerB(q):
            # int_q^inf U(p) V(p+q) dp,  p = q/v
            return ts_integrate(lambda v: (q / v ** 2) * mp.exp(lnU(q / v) + lnV(q + q / v)), rule_B)

        IA = ts_integrate(lambda u: (Kf / u ** 2) * mp.exp(lnU(Kf / u)) * innerA(Kf / u), rule_out)
        IB = ts_integrate(lambda u: (Kf / u ** 2) * mp.exp(lnW(Kf / u)) * innerB(Kf / u), rule_out)
        I2 = IA + IB

        # boundary lines of the corner, with their q- (resp. p-) Taylor coefficients at K via circles
        rule_lq = ts_rule(h, digits, max(-(self.eU + self.eV) - 1, mp.mpf('0.02')))   # int over p of U(p)V(p+q)
        rule_lp = ts_rule(h, digits, max(-(self.eV + self.eW) - 1, mp.mpf('0.02')))   # int over q of V(p+q)W(q)
        circ = circle_points(Kf, rho, M)
        Uout = [(w, Kf / x, mp.exp(lnU(Kf / x))) for x, w in rule_lq]
        Lam_q = []
        for qq in circ:
            wq = mp.exp(lnW(qq))
            s = mp.fsum(w * (pp ** 2 / Kf) * up * mp.exp(lnV(pp + qq)) for (w, pp, up) in Uout)
            Lam_q.append(wq * s)
        Wout = [(w, Kf / x, mp.exp(lnW(Kf / x))) for x, w in rule_lp]
        Lam_p = []
        for pp in circ:
            up = mp.exp(lnU(pp))
            s = mp.fsum(w * (qq ** 2 / Kf) * wq * mp.exp(lnV(pp + qq)) for (w, qq, wq) in Wout)
            Lam_p.append(up * s)
        lam_q = cauchy_coeffs(Lam_q, rho, nder)
        lam_p = cauchy_coeffs(Lam_p, rho, nder)
        # corner Taylor coefficients c_{ij} of F(K+u,K+v) = U(K+u) V(2K+u+v) W(K+v)
        cU = cauchy_coeffs([mp.exp(lnU(z)) for z in circ], rho, nder)
        cW = cauchy_coeffs([mp.exp(lnW(z)) for z in circ], rho, nder)
        rho2 = 2 * rho
        cV = cauchy_coeffs([mp.exp(lnV(z)) for z in circle_points(2 * Kf, rho2, M)], rho2, 2 * nder)

        def cF(i, j):
            return mp.fsum(cU[i - a] * cW[j - c] * cV[a + c] * mp.binomial(a + c, a)
                           for a in range(i + 1) for c in range(j + 1))

        corner = (I2 + lam_q[0] / 2 + lam_p[0] / 2 + cF(0, 0) / 4
                  - mp.fsum(E[k - 1] * (lam_q[2 * k - 1] + lam_p[2 * k - 1]) for k in range(1, P + 1))
                  - mp.fsum(E[k - 1] * (cF(0, 2 * k - 1) + cF(2 * k - 1, 0)) for k in range(1, P + 1)) / 2
                  + mp.fsum(E[j - 1] * E[k - 1] * cF(2 * j - 1, 2 * k - 1)
                            for j in range(1, P + 1) for k in range(1, P + 1)))
        tot = S_dir + LQ[0] + LP[0] + corner
        if details:
            return tot, dict(direct=S_dir, lineQ=LQ[0], lineP=LP[0], corner=corner, I2=I2,
                             emQ=LQ[2], emP=LP[2])
        return tot


# ----------------------------------------------------------------------------------------------
# the periodized kernel
# ----------------------------------------------------------------------------------------------
class Wheel:
    def __init__(self, d, b, r, g=None, mult='so'):
        self.d = mp.mpf(d)
        self.b = mp.mpmathify(b)
        self.r = int(r)
        self.sigma = self.b / 2
        self.g = (self.d / 2 - self.sigma) if g is None else mp.mpmathify(g)
        self.mult = mult
        self.alpha = self.r * self.g
        d_ = self.d
        if mult == 'so':          # d_l of gs:spectrum, generating function (1+z)(1-z)^{1-d}
            self._lgm = LGR(d_ - 2, 1)
            self._c0 = mp.loggamma(d_ - 1)
        elif mult == 'noplus':    # control: (1-z)^{1-d} only, d_l = (d-1)_l / l!
            self._lgm = LGR(d_ - 1, 1)
            self._c0 = mp.loggamma(d_ - 1)
        else:
            raise ValueError(mult)

    # log multiplicity, smooth in x
    def lnmult(self, x):
        if self.mult == 'so':
            return mp.log(2 * x + self.d - 2) + self._lgm(x) - self._c0
        return self._lgm(x) - self._c0

    def ratmult(self, x):   # m(x+1)/m(x)
        d_ = self.d
        if self.mult == 'so':
            return (2 * x + d_) / (2 * x + d_ - 2) * (x + d_ - 2) / (x + 1)
        return (x + d_ - 1) / (x + 1)

    def mult_int(self, l):
        return mp.exp(self.lnmult(mp.mpf(l)))

    # ---- kernel straight from the definition (used for brute-force checks only)
    def gl(self, l, s):
        a = mp.mpf(l) / 2 + self.sigma / 2
        be = a + self.g
        return mp.gamma(a + s) * mp.gamma(a - s) / (mp.gamma(be + s) * mp.gamma(be - s))

    # ---- quadrant sums
    def _right(self, t):
        r, s, g = self.r, self.sigma, self.g
        lV = LGR(s + t, s + t + g)          # f(m+sigma+t) = Gamma(m+s+t)/Gamma(m+s+t+g)
        lW = LGR(1 - g + t, 1 + t)          # reflected f(-n-t) without the sine prefactor
        Q = Quadrant(lnU=self.lnmult,
                     lnV=lambda m: r * lV(m),
                     lnW=lambda n: r * lW(n),
                     ratV=lambda m: ((m + s + t) / (m + s + t + g)) ** r,
                     eU=self.d - 2, eV=-self.alpha, eW=-self.alpha)
        rho_t = -mp.sinpi(g - t) / mp.sinpi(t)
        return rho_t ** r, Q

    def _middle(self, t):
        r, s, g = self.r, self.sigma, self.g
        lU = LGR(1 - t, 1 - t + g)          # f(j+1-t)
        lW = LGR(s + t, s + t + g)          # f(k+sigma+t)
        Q = Quadrant(lnU=lambda j: r * lU(j),
                     lnV=lambda m: self.lnmult(m + 1),
                     lnW=lambda k: r * lW(k),
                     ratV=lambda m: self.ratmult(m + 1),
                     eU=-self.alpha, eV=self.d - 2, eW=-self.alpha)
        return Q

    def S(self, t, details=False, **kw):
        t = mp.mpmathify(t)
        pr, QR = self._right(t)
        t2 = 1 - self.sigma - t
        pl, QL = self._right(t2)
        QM = self._middle(t)
        R = QR.total(**kw)
        L = QL.total(**kw)
        Mm = QM.total(**kw)
        val = pr * R + pl * L + Mm
        if details:
            return val, dict(right=pr * R, left=pl * L, middle=Mm)
        return val

    def D(self, t):
        return mp.sinpi(t) * mp.sinpi(t + self.sigma)

    def Xi(self, t, **kw):
        t = mp.mpmathify(t)
        return self.D(t) ** self.r * self.S(t, **kw)

    def Nb(self):
        return mp.gamma(self.d / 2) * mp.gamma(self.g) / mp.gamma(self.sigma)


# ----------------------------------------------------------------------------------------------
# Fourier analysis and residue functional (own implementation)
# ----------------------------------------------------------------------------------------------
def dft_modes(ts, xis, mmax):
    """gamma_m from samples on t_j = t0 + j/N: Xi(t) = sum_m gamma_m e^{2 pi i m t}."""
    N = len(ts)
    out = {}
    for m in range(-mmax, mmax + 1):
        out[m] = mp.fsum(xis[j] * mp.expjpi(-2 * m * ts[j]) for j in range(N)) / N
    return out


def series_mul(a, b, n):
    return [mp.fsum(a[i] * b[k - i] for i in range(k + 1)) for k in range(n)]


def series_inv(a, n):
    out = [1 / a[0]]
    for k in range(1, n):
        out.append(-mp.fsum(a[i] * out[k - i] for i in range(1, k + 1)) / a[0])
    return out


def residue_W(modes, sigma, r, Nb):
    """W_r = -Nb^r Res_{t=0} Xi(t)/D(t)^r with Xi = sum gamma_m e^{2 pi i m t} (own series arithmetic)."""
    n = r  # need coefficient t^{r-1}
    # E(t) = D(t)/t = [sin(pi t)/t] sin(pi(t+sigma))
    s1 = [(-1) ** (k // 2) * mp.pi ** (k + 1) / mp.factorial(k + 1) if k % 2 == 0 else mp.mpf(0) for k in range(n)]
    s2 = [mp.pi ** k * mp.sin(mp.pi * sigma + k * mp.pi / 2) / mp.factorial(k) for k in range(n)]
    Eser = series_mul(s1, s2, n)
    Einv = series_inv(Eser, n)
    Er = [mp.mpf(1)] + [mp.mpf(0)] * (n - 1)
    for _ in range(r):
        Er = series_mul(Er, Einv, n)
    xs = [mp.fsum(gm * (2j * mp.pi * m) ** k for m, gm in modes.items()) / mp.factorial(k) for k in range(n)]
    prod = series_mul(xs, Er, n)
    return -Nb ** r * prod[r - 1]


def explicit_W(modes, b, r, Nb):
    """foundation eq. (explicit): only for r=3,4; uses c_0 = gamma_0, c_k = 2 gamma_k e^{-i pi k sigma}."""
    sigma = mp.mpmathify(b) / 2
    c = {0: modes[0]}
    for k in range(1, r):
        c[k] = 2 * modes[k] * mp.expjpi(-k * sigma)
    s = mp.sin(mp.pi * b / 2)
    v = mp.cos(mp.pi * b / 2)
    if r == 3:
        return -2 * Nb ** 3 / (mp.pi * s ** 5) * ((1 + 2 * v ** 2) * c[0] + 3 * v * c[1])
    if r == 4:
        return 4 * Nb ** 4 / (mp.pi * s ** 7) * (v * (3 + 2 * v ** 2) * c[0] + (1 + 4 * v ** 2) * c[1] + 5 * v * c[2])
    return None


def bell_E(xs, m):
    """note fp:BellFinite convention: E_0=1, E_m = (1/m) sum_h x_h/(h-1)! E_{m-h} (= [t^m] exp(sum x_h t^h/h!))."""
    E = [mp.mpf(1)]
    for k in range(1, m + 1):
        E.append(mp.fsum(xs[h - 1] / mp.factorial(h - 1) * E[k - h] for h in range(1, k + 1)) / k)
    return E[m]


def bell_W(modes, sigma, r, Nb):
    """foundation eq. (functional)/(weights) in exponential form, u_h from polygammas (checked separately)."""
    u = [r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - (-1) ** (h + 1) * mp.psi(h - 1, 1 - sigma) + mp.psi(h - 1, sigma))
         for h in range(1, r)]
    tot = 0
    for m, gm in modes.items():
        xs = [u[0] + 2j * mp.pi * m] + u[1:]
        tot += gm * bell_E(xs, r - 1)
    return -(Nb / (mp.pi * mp.sin(mp.pi * sigma))) ** r * tot
