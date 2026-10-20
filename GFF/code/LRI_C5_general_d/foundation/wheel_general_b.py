#!/usr/bin/env python3
"""Finite-sample formula for the balanced wheels W_r(d;b), r = 3, 4, at a GENERAL rim exponent b
(generalization of Sec. app:generalPeriodization of the condensed note from b = d/2).

Notation:  q = d/4,  sigma = b/2,  g = 2q - sigma = (d-b)/2,  N_b = Gamma(2q) Gamma(g)/Gamma(sigma),
           D_b(t) = sin(pi t) sin(pi (t + sigma)).
Kernel (gs:balancedWheel):  t_{l,b}(nu) = N_b g_l(i nu; b),  g_l(s;b) = G(a_l+s)G(a_l-s)/(G(b_l+s)G(b_l-s)),
           a_l = l/2 + b/4,  b_l = l/2 + d/2 - b/4,   W_r(d;b) = N_b^r sum_l d_l int ds/(2 pi i) g_l(s;b)^r.
Periodization:  Xi_r(t;b) = D_b(t)^r sum_l d_l sum_{n in Z} g_l(a_l+n+t;b)^r
           = sum_{k=0}^{r-2} c_{r,k}(q,b) cos(2 pi k (t + b/4))   (finite Fourier theorem for 0 < Re b < b_max,
             b_max = min(d - d/r, d - 2(d-1)/r, d - 1/r); the top mode c_{r,r-1} vanishes: top-mode theorem)
Sample:    Xi_r(t;b) = D_b(t)^r [A0(t) + A+(t) + A0(1-sigma-t) + A+(1-sigma-t) + C(t)]
           A0(t) = [G(sigma+t)G(-t)/(G(2q+t)G(g-t))]^r  2r+1F2r(1,(sigma+t)^r,(1-g+t)^r; (2q+t)^r,(1+t)^r; 1)
           A+(t) = 4q [G(1+sigma+t)G(-t)/(G(1+2q+t)G(g-t))]^r  sum_{j,n} D_j F_{j+n} G_n
           C(t)  = 4q [G(sigma+t)G(1-t)/(G(2q+t)G(1+g-t))]^r   sum_{j,k} D_{j+k} P_j Q_k
           D_j = (2q+1)_j (4q-1)_j/((2q)_j (2)_j),  F_m = [(1+sigma+t)_m/(1+2q+t)_m]^r,
           G_n = [(1-g+t)_n/(1+t)_n]^r,  P_j = [(1-t)_j/(1+g-t)_j]^r,  Q_k = [(sigma+t)_k/(2q+t)_k]^r.
Residue functional (only sigma enters):
           W_r(d;b) = -[N_b/(pi sin(pi sigma))]^r sum_{|m|<=r-1} gamma_m E_{r-1}(u_1+2 pi i m, u_2, ..., u_{r-1}),
           Xi_r(t) = sum_m gamma_m e^{2 pi i m t},  u_h = r[(1+(-1)^h) psi_{h-1}(1) - (-1)^{h+1} psi_{h-1}(1-sigma)
                                                           + psi_{h-1}(sigma)].
Nodes:  'fixed' (default): b-INDEPENDENT t_j = -q/2 + j/(2r-1) + i/(8 pi r), j = 0..2r-2, full complex DFT
        (does not use the top-mode theorem; reports c_{r,r-1} as a check);
        'reduced': b-independent t_j = -q/2 + j/(2r-3) + i/(8 pi r), j = 0..2r-4 (uses c_{r,r-1} = 0);
        'note': t_j = -sigma/2 + j/(2r-1) + i/(8 pi r), j = 0..r-1, cosine transform of Re Xi (real b only);
        at b = d/2 'note' is exactly fp:nodes/fp:cosineTransform.
Integer d = 1, 2, 3 must be passed exactly (they use the exact polynomial multiplicities).
Write-up: general_b_periodization.tex in this directory.

Usage:  python3 wheel_general_b.py r d b [dps] [nodes]
"""
import sys
import mpmath as mp
from hypsums import GammaSeq, PolySeq, single_sum, conv_sum, moment_product_sum


def _isint(x, n):
    try:
        return mp.im(x) == 0 and mp.re(x) == n
    except TypeError:
        return x == n


def bmax(r, d):
    """upper end of the absolute-convergence range 0 < b < bmax of the periodized sums (finite Fourier theorem)."""
    d = mp.mpf(d)
    return min(d * (r - 1) / r, d - 2 * (d - 1) / mp.mpf(r), d - mp.mpf(1) / r)


class Wheel:
    def __init__(self, r, d, b, M=None, K=None, N=None):
        self.r = int(r)
        self.d = mp.mpmathify(d)
        self.b = mp.mpmathify(b)
        self.q = self.d / 4
        self.sig = self.b / 2
        self.g = 2 * self.q - self.sig
        dps = mp.mp.dps
        self.M = M or max(80, int(1.6 * dps))
        self.K = K or max(30, int(0.8 * dps) + 10)
        self.N = N or self.M // 2
        q = self.q
        if _isint(self.d, 1):
            self.mult = 'delta'
            self.pref4q = mp.mpf(1)
        elif _isint(self.d, 2):
            self.mult = PolySeq([1])
            self.pref4q = mp.mpf(2)
        elif _isint(self.d, 3):
            self.mult = PolySeq([1, mp.mpf(2) / 3])
            self.pref4q = mp.mpf(3)
        else:
            self.mult = GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
            self.pref4q = 4 * q
            K = self.K
            self.muD = [mp.mpc((-1) ** (k + 1) / (4 * q)) for k in range(K + 1)]   # exact regularized moments
        self.cache = {}

    # ---------------------------------------------------------------- blocks
    def A0(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        G = mp.gamma
        pre = (G(s + t) * G(-t) * mp.rgamma(2 * q + t) * mp.rgamma(g - t)) ** r
        T = GammaSeq([(s + t, 2 * q + t, r), (1 - g + t, 1 + t, r)])
        return pre * single_sum(T, 0, self.N, self.K)

    def Aplus(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        G = mp.gamma
        pre = self.pref4q * (G(1 + s + t) * G(-t) * mp.rgamma(1 + 2 * q + t) * mp.rgamma(g - t)) ** r
        F = GammaSeq([(1 + s + t, 1 + 2 * q + t, r)])
        Gs = GammaSeq([(1 - g + t, 1 + t, r)])
        if self.mult == 'delta':
            return pre * single_sum(F.product(Gs), 0, self.N, self.K)
        muY = getattr(self, 'muD', None)
        return pre * conv_sum(F, self.mult, Gs, M=self.M, N=self.N, K=self.K, muY=muY)

    def Cmid(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        G = mp.gamma
        pre = self.pref4q * (G(s + t) * G(1 - t) * mp.rgamma(2 * q + t) * mp.rgamma(1 + g - t)) ** r
        if self.mult == 'delta':
            return pre
        P = GammaSeq([(1 - t, 1 + g - t, r)])
        Q = GammaSeq([(s + t, 2 * q + t, r)])
        if getattr(self.mult, 'poly', False):
            return pre * moment_product_sum(self.mult, P, Q, self.N, self.K)
        return pre * conv_sum(self.mult, P, Q, M=self.M, N=self.N, K=self.K)

    def Db(self, t):
        return mp.sin(mp.pi * t) * mp.sin(mp.pi * (t + self.sig))

    def Xi(self, t, parts=False):
        t = mp.mpc(t)
        key = (mp.nstr(t, mp.mp.dps), parts)
        if key in self.cache:
            return self.cache[key]
        tp = 1 - self.sig - t
        blocks = dict(A0=self.A0(t), Ap=self.Aplus(t), A0m=self.A0(tp), Apm=self.Aplus(tp), C=self.Cmid(t))
        val = self.Db(t) ** self.r * mp.fsum(blocks.values())
        out = (val, blocks) if parts else val
        self.cache[key] = out
        return out

    # ---------------------------------------------------------------- functional
    def uweights(self):
        r, s = self.r, self.sig
        u = []
        for h in range(1, r):
            L = (-1) ** (h + 1) * mp.psi(h - 1, 1 - s) - mp.psi(h - 1, s)
            u.append(r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - L))
        return u

    @staticmethod
    def bellE(xs):
        """E_m(x_1..x_m), m = 0..len(xs): coefficients of exp(sum x_h t^h/h!)."""
        E = [mp.mpc(1)]
        for m in range(1, len(xs) + 1):
            E.append(mp.fsum(xs[h - 1] / mp.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m)
        return E

    def Nb(self):
        return mp.gamma(2 * self.q) * mp.gamma(self.g) * mp.rgamma(self.sig)

    def exp_weights(self):
        """Res_{t=0} e^{2 pi i m t}/D_b(t)^r = e_m, m = -(r-1)..(r-1)."""
        r, s = self.r, self.sig
        u = self.uweights()
        lead = 1 / (mp.pi * mp.sin(mp.pi * s)) ** r
        return {m: lead * self.bellE([u[0] + 2j * mp.pi * m] + u[1:])[r - 1] for m in range(-(r - 1), r)}

    def nodes_fixed(self):
        r = self.r
        Nn = 2 * r - 1
        eta = 1 / (8 * mp.pi * r)
        tau0 = -self.q / 2
        return [tau0 + mp.mpf(j) / Nn + 1j * eta for j in range(Nn)], tau0, eta

    def fourier_fixed(self):
        """exponential Fourier coefficients gamma_m (|m| <= r-1) from 2r-1 b-independent complex samples."""
        r = self.r
        Nn = 2 * r - 1
        ts, tau0, eta = self.nodes_fixed()
        X = [self.Xi(t) for t in ts]
        gam = {}
        for m in range(-(r - 1), r):
            dft = mp.fsum(X[j] * mp.expjpi(-2 * m * mp.mpf(j) / Nn) for j in range(Nn)) / Nn
            gam[m] = dft * mp.exp(-2j * mp.pi * m * (tau0 + 1j * eta))
        return gam, X

    def cos_coeffs(self, gam):
        """c_k with Xi = sum_k c_k cos(2 pi k (t + b/4)); returns (c, asymmetry) where asymmetry measures
        |2 gamma_k e^{-i pi k sigma} - 2 gamma_{-k} e^{i pi k sigma}| (reflection-symmetry check)."""
        r, s = self.r, self.sig
        c = [gam[0]]
        asym = mp.mpf(0)
        for k in range(1, r):
            c1 = 2 * gam[k] * mp.expjpi(-k * s)
            c2 = 2 * gam[-k] * mp.expjpi(k * s)
            asym = max(asym, abs(c1 - c2))
            c.append((c1 + c2) / 2)
        return c, asym

    def W_fixed(self, full=False):
        gam, X = self.fourier_fixed()
        e = self.exp_weights()
        W = -self.Nb() ** self.r * mp.fsum(gam[m] * e[m] for m in gam)
        if full:
            c, asym = self.cos_coeffs(gam)
            return W, dict(gamma=gam, c=c, asym=asym, samples=X)
        return W

    def W_reduced(self, full=False):
        """Uses the top-mode theorem c_{r,r-1} = 0: exponential modes |m| <= r-2 only, so 2r-3 b-independent
        complex samples t_j = -q/2 + j/(2r-3) + i/(8 pi r) suffice (exact DFT, no aliasing)."""
        r = self.r
        Nn = 2 * r - 3
        eta = 1 / (8 * mp.pi * r)
        tau0 = -self.q / 2
        ts = [tau0 + mp.mpf(j) / Nn + 1j * eta for j in range(Nn)]
        X = [self.Xi(t) for t in ts]
        gam = {}
        for m in range(-(r - 2), r - 1):
            dft = mp.fsum(X[j] * mp.expjpi(-2 * m * mp.mpf(j) / Nn) for j in range(Nn)) / Nn
            gam[m] = dft * mp.exp(-2j * mp.pi * m * (tau0 + 1j * eta))
        e = self.exp_weights()
        W = -self.Nb() ** r * mp.fsum(gam[m] * e[m] for m in gam)
        if full:
            return W, dict(gamma=gam, samples=X, nodes=ts)
        return W

    def W_explicit(self, c):
        """explicit trigonometric form of the functional (c_{r,r-1} = 0 used), s = sin(pi sigma), co = cos(pi sigma):
           r=3: W = -2 N^3/(pi s^5) [ (1+2 co^2) c0 + 3 co c1 ]
           r=4: W =  4 N^4/(pi s^7) [ co (3+2co^2) c0 + (1+4co^2) c1 + 5 co c2 ]"""
        s, co = mp.sin(mp.pi * self.sig), mp.cos(mp.pi * self.sig)
        N = self.Nb()
        if self.r == 3:
            return -2 * N ** 3 / (mp.pi * s ** 5) * ((1 + 2 * co ** 2) * c[0] + 3 * co * c[1])
        if self.r == 4:
            return 4 * N ** 4 / (mp.pi * s ** 7) * (co * (3 + 2 * co ** 2) * c[0] + (1 + 4 * co ** 2) * c[1]
                                                     + 5 * co * c[2])
        raise ValueError('explicit form coded for r = 3, 4')

    def B_weights(self):
        """B_{r,k}(sigma) of fp:finiteFunctional with q -> sigma."""
        r, s = self.r, self.sig
        u = self.uweights()
        out = []
        for k in range(r):
            Ep = self.bellE([u[0] + 2j * mp.pi * k] + u[1:])[r - 1]
            Em = self.bellE([u[0] - 2j * mp.pi * k] + u[1:])[r - 1]
            out.append((mp.expjpi(k * s) * Ep + mp.expjpi(-k * s) * Em) / 2)
        return out

    def W_note(self, full=False):
        """note's real cosine transform at b-dependent nodes t_j = -sigma/2 + j/N + i eta (real b)."""
        r = self.r
        Nn = 2 * r - 1
        eta = 1 / (8 * mp.pi * r)
        Y = [mp.re(self.Xi(-self.sig / 2 + mp.mpf(j) / Nn + 1j * eta)) for j in range(r)]
        c = [(Y[0] + 2 * mp.fsum(Y[1:])) / Nn]
        for k in range(1, r):
            c.append(2 / (Nn * mp.cosh(mp.mpf(k) / (4 * r))) *
                     (Y[0] + 2 * mp.fsum(Y[j] * mp.cospi(2 * mp.mpf(k * j) / Nn) for j in range(1, r))))
        Bw = self.B_weights()
        W = -(self.Nb() / (mp.pi * mp.sin(mp.pi * self.sig))) ** r * mp.fsum(Bw[k] * c[k] for k in range(r))
        if full:
            return W, dict(c=c, Y=Y)
        return W

    def trig_check(self, c, t):
        """|Xi(t) - sum_k c_k cos(2 pi k (t + b/4))| at an arbitrary extra point (finite-Fourier check)."""
        approx = mp.fsum(c[k] * mp.cos(2 * mp.pi * k * (t + self.b / 4)) for k in range(self.r))
        return abs(self.Xi(t) - approx), abs(approx)


def exceptional(r, d, b, tol=None):
    """True at parameters where the generic acceleration formulas have removable poles:
    noninteger d with r(d-b)/2 an integer (resonance of the large-index families), or b/2 an integer."""
    tol = tol or mp.mpf(10) ** (-mp.mp.dps // 3)
    d = mp.mpmathify(d)
    b = mp.mpmathify(b)
    rg = r * (d - b) / 2
    integer_d = any(_isint(d, n) for n in (1, 2, 3))
    res = (not integer_d) and abs(rg - mp.nint(mp.re(rg))) < tol
    return bool(res or abs(b / 2 - mp.nint(mp.re(b / 2))) < tol)


def W(r, d, b, dps=30, nodes='fixed', guard=15, m_circle=8, **kw):
    """W_r(d;b) from the finite-sample formula, returned with dps significant digits (computed with dps+guard).
    nodes: 'fixed' (2r-1 b-independent complex nodes, full DFT; default), 'reduced' (2r-3 nodes, uses the
    top-mode theorem c_{r,r-1} = 0), 'note' (r b-dependent nodes, real cosine transform; real b only).
    At exceptional (resonant) parameters the value is the mean over m_circle points b + rho e^{i theta_k},
    theta_k = 2 pi (k+1/2)/m_circle: exact for the analytic W up to O(rho^m_circle)."""
    d = mp.mpmathify(d)
    b = mp.mpmathify(b)
    if not exceptional(r, d, b):
        with mp.workdps(dps + guard):
            w = Wheel(r, d, b, **kw)
            val = {'fixed': w.W_fixed, 'note': w.W_note, 'reduced': w.W_reduced}[nodes]()
        with mp.workdps(dps):
            return +val
    rho = mp.mpf(10) ** (-mp.mpf(dps + 10) / m_circle) / 10
    extra = int(2 * (-mp.log10(rho))) + 5
    with mp.workdps(dps + guard + extra):
        vals = []
        for k in range(m_circle):
            bk = b + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / m_circle)
            vals.append(Wheel(r, d, bk, **kw).W_fixed())
        val = mp.fsum(vals) / m_circle
    with mp.workdps(dps):
        return +val


def bspec(r, d):
    """spectral convergence bound: W_r(d;b) converges absolutely for 0 < Re b < d - max(d,1)/r."""
    d = mp.mpf(d)
    return d - max(d, 1) / mp.mpf(r)


def circle_params(r, d, frac=mp.mpf(1) / 3):
    """centre d/2 and radius frac * min(distance to the nearest singularity of W_r(d;.), bmax - d/2)."""
    d = mp.mpmathify(d)
    b0 = d / 2
    R = min(b0, bspec(r, d) - b0, bmax(r, d) - b0)
    return b0, frac * R


def bjets(r, d, kmax=2, dps=30, M=64, rho=None, b0=None, pool=None):
    """Taylor coefficients a_k = W^{(k)}(b0)/k!, k <= kmax, of b -> W_r(d;b) from a Cauchy circle of M points
    (conjugate symmetry W(conj b) = conj W(b) halves the work).  L_d = a_1 (r=4), Z_d = 2 a_2 / 9 (r=3).
    pool: optional multiprocessing pool (its map is used for the M/2 evaluations)."""
    with mp.workdps(dps + 15):
        d = mp.mpmathify(d)
        c0, r0 = circle_params(r, d)
        b0 = mp.mpmathify(b0) if b0 is not None else c0
        rho = mp.mpmathify(rho) if rho is not None else r0
        pts = [b0 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / M) for k in range(M // 2)]
        args = [(r, d, b, dps) for b in pts]
        vals = (pool.map(_w_star, args) if pool is not None else [_w_star(a) for a in args])
        vals = [mp.mpmathify(v) for v in vals]
        full = vals + [mp.conj(vals[M - 1 - k]) for k in range(M // 2, M)]
        coef = []
        for j in range(kmax + 1):
            s = mp.fsum(full[k] * mp.expjpi(-2 * j * (k + mp.mpf(1) / 2) / M) for k in range(M)) / M / rho ** j
            coef.append(s)
    with mp.workdps(dps):
        return [+c for c in coef]


def _w_star(a):
    r, d, b, dps = a
    mp.mp.dps = dps + 15
    return W(r, d, b, dps)


if __name__ == '__main__':
    import time
    r, d, b = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    dps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    nodes = sys.argv[5] if len(sys.argv) > 5 else 'fixed'
    mp.mp.dps = dps
    st = time.time()
    v = W(r, mp.mpmathify(d), mp.mpmathify(b), dps, nodes)
    print('W_%d(d=%s; b=%s) =' % (r, d, b), mp.nstr(v, dps), '  [%.1f s]' % (time.time() - st))
