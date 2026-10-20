#!/usr/bin/env python3
"""L_d = d/db W_4(d;b) at b = d/2 for generic dimension 0 < d < 4 (d > 1/2), from a three-node finite-sample
formula with five two-variable Horn functions (session L, LRI_C5_general_d/L; derivation in L_general_d.tex).

Notation (rim exponent b, q = d/4):
   x = b/4,  y = d/2 - b/4  (so sigma = b/2 = 2x, spoke g = (d-b)/2 = y - x, x + y = 2q),
   phi(z) = Gamma(z+x)/Gamma(z+y),   psit(z) = Gamma(z+1-y)/Gamma(z+1-x),
   N_b = Gamma(2q) Gamma(g)/Gamma(sigma),   multiplicities d_l (d_0 = 1, d_{j+1} = 4q D_j,
   D_j = (2q+1)_j (4q-1)_j/((2q)_j (2)_j)).
Five Horn functions (r = 4; Pochhammer form, all two-variable, argument (1,1)):
   hR(u)  = sum_{l,n>=0} d_l [(u+x)_{l+n}/(u+y)_{l+n}]^r [(u+1-y)_n/(u+1-x)_n]^r      at u = x, 1/2, 1
   s0     = sum_{j,k>=0} d_{j+k}   [(x)_j (x)_k/((y)_j (y)_k)]^r
   s1     = sum_{j,k>=0} d_{j+k+1} [(1/2+x)_j (1/2+x)_k/((1/2+y)_j (1/2+y)_k)]^r
Samples of Xi_4(t;b) = sum_k c_k cos(2 pi k (t + b/4)) at t = 0 (pole class), tau = t + b/4 = 0 and tau = 1/2:
   N^r Xi(t=0)    = (-1)^r (pi sin 2pi x)^r hR(x)
   N^r Xi(tau=0)  = (-1)^r { 2 [N sin(pi x) sin(pi y) phi(1) psit(1)]^r hR(1) + [N sin^2(pi x) phi(0)^2]^r s0 }
   N^r Xi(tau=1/2)= 2 [N cos(pi x) cos(pi y) phi(1/2) psit(1/2)]^r hR(1/2) + [N cos^2(pi x) phi(1/2)^2]^r s1
Three-node formula (finite Fourier + top-mode theorem + residue functional), s = sin(pi b/2), c = cos(pi b/2):
   W_4(d;b) = 2/(pi s^7) [ (1+c)^2 (1+2c) N^4 Xi(tau=0) - (1-c)^2 (1-2c) N^4 Xi(tau=1/2) - 2c N^4 Xi(t=0) ]
   W_3(d;b) = -2/(pi s^5) [ (1+2c) N^3 Xi(t=0) - 2c(1-c) N^3 Xi(tau=1/2) ]      (r = 3, by-product check)
L_d is obtained exactly as the b-derivative: b = J(d/2, 1) (first-order jet), which differentiates every
parameter of the Horn series (polygamma-weighted series, tails accelerated identically); see jet.py.

Usage:  python3 L_general.py d [dps] [b]        (b defaults to d/2; integer d = 1, 2, 3 must be given exactly)
"""
import sys
import os
import time
import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jet import J, val, der, jgamma, jrgamma, jsinpi, jcospi  # noqa: E402
from hypsums_jet import GammaSeq, PolySeq, single_sum, conv_sum, moment_product_sum  # noqa: E402


def _isint(x, n):
    try:
        return mp.im(x) == 0 and mp.re(x) == n
    except TypeError:
        return x == n


def bmax(r, d):
    d = mp.mpf(d)
    return min(d * (r - 1) / r, d - 2 * (d - 1) / mp.mpf(r), d - mp.mpf(1) / r)


class Mult:
    """multiplicity data for dimension d: d_0 = 1, d_{j+1} = pref4q * D_j."""

    def __init__(self, d, K):
        self.d = d
        q = d / 4
        self.q = q
        if _isint(d, 1):
            self.kind, self.pref4q, self.D = 'delta', mp.mpf(1), None
        elif _isint(d, 2):
            self.kind, self.pref4q, self.D = 'poly', mp.mpf(2), PolySeq([1])
        elif _isint(d, 3):
            self.kind, self.pref4q, self.D = 'poly', mp.mpf(3), PolySeq([1, mp.mpf(2) / 3])
        else:
            self.kind, self.pref4q = 'gamma', 4 * q
            self.D = GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])
            self.muD = [mp.mpc((-1) ** (k + 1) / (4 * q)) for k in range(K + 1)]   # exact regularized moments


class Wheel3:
    """the five Horn functions and the three samples for one (r, d, b); b may be a jet."""

    def __init__(self, r, d, b, M=None, K=None, N=None):
        self.r = int(r)
        self.d = mp.mpmathify(d)
        self.b = b if isinstance(b, J) else mp.mpmathify(b)
        dps = mp.mp.dps
        self.M = M or max(80, int(1.6 * dps))
        self.K = K or max(30, int(0.8 * dps) + 10)
        self.N = N or self.M // 2
        self.mult = Mult(self.d, self.K)
        self.q = self.d / 4
        self.x = self.b / 4
        self.y = self.d / 2 - self.b / 4
        self.cache = {}

    # ------------------------------------------------------------------ Gamma prefactors
    def phi(self, z):
        return jgamma(z + self.x) * jrgamma(z + self.y)

    def psit(self, z):
        return jgamma(z + 1 - self.y) * jrgamma(z + 1 - self.x)

    def Nb(self):
        return mp.gamma(2 * self.q) * jgamma(self.y - self.x) * jrgamma(2 * self.x)

    # ------------------------------------------------------------------ Horn functions
    def _single(self, T):
        return single_sum(T, 0, self.N, self.K)

    def _single_mult(self, T):
        """sum_k D_k T_k"""
        m = self.mult
        if m.kind == 'delta':
            return T.values(1)[0]
        if m.kind == 'poly':
            return sum((kp * single_sum(T, p, self.N, self.K) for p, kp in enumerate(m.D.kappa) if kp != 0),
                       mp.mpc(0))
        return single_sum(m.D.product(T), 0, self.N, self.K)

    def _conv_mult_outer(self, P, Q):
        """sum_{j,k} D_{j+k} P_j Q_k"""
        m = self.mult
        if m.kind == 'delta':
            return P.values(1)[0] * Q.values(1)[0]
        if m.kind == 'poly':
            return moment_product_sum(m.D, P, Q, self.N, self.K)
        return conv_sum(m.D, P, Q, M=self.M, N=self.N, K=self.K)

    def _conv_mult_middle(self, X, Z):
        """sum_{j,n} D_j X_{j+n} Z_n"""
        m = self.mult
        if m.kind == 'delta':
            return self._single(X.product(Z))
        return conv_sum(X, m.D, Z, M=self.M, N=self.N, K=self.K, muY=getattr(m, 'muD', None))

    def hR(self, u):
        """sum_{l,n} d_l [(u+x)_{l+n}/(u+y)_{l+n}]^r [(u+1-y)_n/(u+1-x)_n]^r (split l = 0 / l = j+1)."""
        key = ('hR', str(val(u)))
        if key in self.cache:
            return self.cache[key]
        r, x, y = self.r, self.x, self.y
        row0 = self._single(GammaSeq([(u + x, u + y, r), (u + 1 - y, u + 1 - x, r)]))
        X = GammaSeq([(u + 1 + x, u + 1 + y, r)])
        Z = GammaSeq([(u + 1 - y, u + 1 - x, r)])
        rest = self.mult.pref4q * ((u + x) / (u + y)) ** r * self._conv_mult_middle(X, Z)
        out = row0 + rest
        self.cache[key] = (out, row0, rest)
        return self.cache[key]

    def s1(self):
        """sum_{j,k} d_{j+k+1} [(1/2+x)_j (1/2+x)_k/((1/2+y)_j (1/2+y)_k)]^r"""
        key = ('s1',)
        if key in self.cache:
            return self.cache[key]
        r, x, y = self.r, self.x, self.y
        h = mp.mpf(1) / 2
        a = GammaSeq([(h + x, h + y, r)])
        out = self.mult.pref4q * self._conv_mult_outer(a, a)
        self.cache[key] = (out,)
        return self.cache[key]

    def s0(self):
        """sum_{j,k} d_{j+k} [(x)_j (x)_k/((y)_j (y)_k)]^r = 1 + 4q a1 [sum_k D_k at_k + sum_{j,k} D_{j+k} at_j a_k]."""
        key = ('s0',)
        if key in self.cache:
            return self.cache[key]
        r, x, y = self.r, self.x, self.y
        a = GammaSeq([(x, y, r)])
        at = GammaSeq([(1 + x, 1 + y, r)])
        a1 = (x / y) ** r
        single = self._single_mult(at)
        double = self._conv_mult_outer(at, a)
        out = 1 + self.mult.pref4q * a1 * (single + double)
        self.cache[key] = (out, single, double)
        return self.cache[key]

    # ------------------------------------------------------------------ samples (normalized by N_b^r)
    def samples(self):
        r, x, y = self.r, self.x, self.y
        N = self.Nb()
        sgn = (-1) ** r
        half = mp.mpf(1) / 2
        hx, h1, hh = self.hR(x)[0], self.hR(mp.mpf(1))[0], self.hR(half)[0]
        S0, S1 = self.s0()[0], self.s1()[0]
        Xt = sgn * (mp.pi * jsinpi(2 * x)) ** r * hx
        k0 = N * jsinpi(x) ** 2 * self.phi(mp.mpf(0)) ** 2
        r0 = N * jsinpi(x) * jsinpi(y) * self.phi(mp.mpf(1)) * self.psit(mp.mpf(1))
        X0 = sgn * (2 * r0 ** r * h1 + k0 ** r * S0)
        kh = N * jcospi(x) ** 2 * self.phi(half) ** 2
        rh = N * jcospi(x) * jcospi(y) * self.phi(half) * self.psit(half)
        Xh = 2 * rh ** r * hh + kh ** r * S1
        # identity check: N sin(pi sigma) sin(pi g) phi(x) psit(x) = pi sin(pi sigma)
        chk = N * jsinpi(2 * x) * jsinpi(y - x) * self.phi(x) * self.psit(x) - mp.pi * jsinpi(2 * x)
        return dict(Xt=Xt, X0=X0, Xh=Xh, hx=hx, h1=h1, hh=hh, s0=S0, s1=S1, pref=dict(k0=k0, r0=r0, kh=kh, rh=rh),
                    idcheck=chk, N=N)

    def W(self, full=False):
        sm = self.samples()
        s, c = jsinpi(2 * self.x), jcospi(2 * self.x)
        if self.r == 4:
            Wv = 2 / (mp.pi * s ** 7) * ((1 + c) ** 2 * (1 + 2 * c) * sm['X0'] - (1 - c) ** 2 * (1 - 2 * c) * sm['Xh']
                                         - 2 * c * sm['Xt'])
        elif self.r == 3:
            Wv = -2 / (mp.pi * s ** 5) * ((1 + 2 * c) * sm['Xt'] - 2 * c * (1 - c) * sm['Xh'])
        else:
            raise ValueError('r = 3, 4 only')
        if full:
            # Fourier coefficients c_k (times N^r) from the three samples, for checks
            if self.r == 4:
                c1 = (sm['X0'] - sm['Xh']) / 2
                m = (sm['X0'] + sm['Xh']) / 2
                c2 = (m + c * c1 - sm['Xt']) / (2 * s ** 2)
                cs = (m - c2, c1, c2)
            else:
                c1 = (sm['Xt'] - sm['Xh']) / (1 + c)
                cs = (sm['Xh'] + c1, c1)
            sm['ck_times_Nr'] = cs
            return Wv, sm
        return Wv


def exceptional(r, d, b, tol=None):
    """True where the large-index expansions have removable (log-resonant) poles: non-integer d with
    r(d-b)/2 a positive integer (e.g. r = 3 at b = d/2 for d = 4/3, 8/3).  For r = 4 at b = d/2 this never
    happens at non-integer d.  Such points are not handled here (the foundation's W uses a circle mean)."""
    tol = tol or mp.mpf(10) ** (-mp.mp.dps // 3)
    d, b = mp.mpmathify(d), mp.mpmathify(b)
    if any(_isint(d, n) for n in (1, 2, 3)):
        return False
    rg = r * (d - b) / 2
    return abs(mp.im(rg)) < tol and abs(mp.re(rg) - mp.nint(mp.re(rg))) < tol


def LP4(d, dps=30, guard=15, b=None, r=4, full=False, **kw):
    """(W_r(d;b), dW_r/db) at b (default d/2) from the three-node formula with exact jet derivatives.
    r = 4: (P4(d), L_d) at b = d/2.  r = 3: (3Q_d, dW_3/db = 0) at b = d/2.
    Pass d as an exact string ('4/3') or an mpf at the working precision: a Python float or a string parsed at
    low precision changes q at the 1e-16 level."""
    with mp.workdps(dps + guard):
        d = mp.mpmathify(d)
        b0 = d / 2 if b is None else mp.mpmathify(b)
        if exceptional(r, d, b0):
            raise ValueError('resonant parameters r(d-b)/2 in Z at non-integer d: not handled')
        w = Wheel3(r, d, J(b0, 1), **kw)
        Wv, sm = w.W(full=True)
    with mp.workdps(dps):
        if full:
            return +val(Wv), +der(Wv), sm
        return +val(Wv), +der(Wv)


def coeffs_closed(d):
    """printed closed-form coefficients of Theorem 6 (L_general_d.tex, eq. Lfinal) at b = d/2, r = 4:
    returns {f: (a_f, a_f')} with P4 = sum_f a_f f and L_d = sum_f (a_f' f + a_f f'),
    f in (hx, h1, hh, s0, s1).  S = sin(pi q), C = cos(pi q), q = d/4."""
    q = mp.mpmathify(d) / 4
    pi = mp.pi
    S, C = mp.sin(pi * q), mp.cos(pi * q)
    G0 = mp.gamma(q / 2) / mp.gamma(3 * q / 2)
    Gh = mp.gamma((1 + q) / 2) / mp.gamma((1 + 3 * q) / 2)
    beta0 = mp.gamma(2 * q) ** 4 * G0 ** 8 * mp.tan(pi * q / 2) / (16 * pi * mp.cos(pi * q / 2) ** 2)
    betah = mp.gamma(2 * q) ** 4 * Gh ** 8 * mp.cot(pi * q / 2) / (16 * pi * mp.sin(pi * q / 2) ** 2)
    Lt0 = (-4 * mp.psi(0, q) + 2 * mp.psi(0, q / 2) + 2 * mp.psi(0, 3 * q / 2) + pi * mp.cot(pi * q / 2)
           - 3 * pi / 2 * mp.cot(pi * q))
    Lth = (-4 * mp.psi(0, q) + 2 * mp.psi(0, (1 + q) / 2) + 2 * mp.psi(0, (1 + 3 * q) / 2) - pi * mp.tan(pi * q / 2)
           - 3 * pi / 2 * mp.cot(pi * q))
    r0 = (2 - 3 * q) / (3 * (2 - q))
    rh = (1 - 3 * q) / (1 - q)
    nu0 = r0 ** 4 * (4 / (3 * q) + 1 / (2 - q)) / 2 + r0 ** 3 / (6 * (2 - q))
    nuh = rh ** 3 * (1 - 2 * q) / (1 - q) ** 2
    e0, eh = 1 + 2 * C, 2 * C - 1
    return dict(hx=(-4 * pi ** 3 * C / S ** 3, 2 * pi ** 4 * (1 + 2 * C ** 2) / S ** 4),
                h1=(2 * r0 ** 4 * e0 * beta0, beta0 * (2 * r0 ** 4 * (e0 * Lt0 - pi * S) + 8 * e0 * nu0)),
                hh=(2 * rh ** 4 * eh * betah, betah * (2 * rh ** 4 * (eh * Lth - pi * S) + 8 * eh * nuh)),
                s0=(e0 * beta0, beta0 * (e0 * Lt0 - pi * S)),
                s1=(eh * betah, betah * (eh * Lth - pi * S)))


def L_explicit(d, dps=30, guard=15, **kw):
    """(P4(d), L_d) from the printed formula: closed-form coefficients times the five Horn values and their
    first b-derivatives (the latter from jets, i.e. the series of Proposition 5)."""
    inv = inventory(d, dps, guard, **kw)
    with mp.workdps(dps + guard):
        d = mp.mpmathify(d)
        cf = coeffs_closed(d)
        P4 = mp.fsum(cf[k][0] * mp.re(inv[k][0]) for k in cf)
        L = mp.fsum(cf[k][1] * mp.re(inv[k][0]) + cf[k][0] * mp.re(inv[k][1]) for k in cf)
    with mp.workdps(dps):
        return +P4, +L


def inventory(d, dps=30, guard=15, r=4, **kw):
    """the five Horn values and their b-derivatives at b = d/2 (with the Gamma/elementary prefactors)."""
    with mp.workdps(dps + guard):
        d = mp.mpmathify(d)
        w = Wheel3(r, d, J(d / 2, 1), **kw)
        Wv, sm = w.W(full=True)
        out = {k: (val(sm[k]), der(sm[k])) for k in ('hx', 'h1', 'hh', 's0', 's1')}
    return out


if __name__ == '__main__':
    dps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    b = sys.argv[3] if len(sys.argv) > 3 else None
    mp.mp.dps = dps
    d = sys.argv[1]                      # kept as a string; parsed at the working precision inside LP4
    for r in (4, 3):
        st = time.time()
        try:
            Wv, dW = LP4(d, dps, b=b, r=r)
        except ValueError as e:
            print('r=%d d=%s: skipped (%s)' % (r, d, e))
            continue
        print('r=%d d=%s b=%s:  W = %s   dW/db = %s   [%.1f s]' % (r, sys.argv[1], b or 'd/2', mp.nstr(mp.re(Wv), dps),
                                                                  mp.nstr(mp.re(dW), dps), time.time() - st))
    if b is None:
        st = time.time()
        P4e, Le = L_explicit(d, dps)
        print('printed formula (Theorem 6): P4 = %s   L_d = %s   [%.1f s]' % (mp.nstr(P4e, dps), mp.nstr(Le, dps),
                                                                           time.time() - st))
