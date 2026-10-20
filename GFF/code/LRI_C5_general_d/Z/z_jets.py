#!/usr/bin/env python3
"""Exact-jet engine: b-derivatives of the five sample blocks of the two-node formula for W_3(d;b) at b = d/2,
by truncated Taylor arithmetic in eps = b - d/2 (no numerical differentiation).

Every quantity of the accelerated Horn evaluation of the foundation (hypsums.py: Gamma-ratio sequences, their Stirling
data, Euler-Maclaurin Hurwitz zeta values, zeta-regularized moments, three-family convolution asymptotics) is an
analytic function of the parameters; here the same algorithms are run with parameters in the ring C[eps]/(eps^{D+1}).
The output coefficient j of a block is f^(j)(d/2)/j!.  The logic mirrors hypsums.py and wheel_general_b.py line by
line (same truncation parameters M, K, N), so at D = 0 it reproduces the foundation's values.

usage: z_jets.py OUT.json DPS d1,d2,...   [D]      (integer d = 1, 2, 3 passed exactly)
"""
import json
import os
import sys
import time

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'foundation'))
from hypsums import GammaSeq, PolySeq, _bern_over_fact  # noqa: E402

# ----------------------------------------------------------------------------------------------
# truncated Taylor arithmetic
# ----------------------------------------------------------------------------------------------
DEG = 2


class Jet:
    """a_0 + a_1 eps + ... + a_D eps^D, coefficients mpc, D = DEG (module global)."""
    __slots__ = ('c',)

    def __init__(self, c):
        self.c = c

    @staticmethod
    def const(x):
        return Jet([mp.mpc(x)] + [mp.mpc(0)] * DEG)

    @staticmethod
    def var(x0, slope=1):
        c = [mp.mpc(x0), mp.mpc(slope)] + [mp.mpc(0)] * (DEG - 1)
        return Jet(c[:DEG + 1])

    def __add__(self, o):
        if isinstance(o, Jet):
            return Jet([a + b for a, b in zip(self.c, o.c)])
        c = list(self.c)
        c[0] = c[0] + o
        return Jet(c)

    __radd__ = __add__

    def __neg__(self):
        return Jet([-a for a in self.c])

    def __sub__(self, o):
        if isinstance(o, Jet):
            return Jet([a - b for a, b in zip(self.c, o.c)])
        c = list(self.c)
        c[0] = c[0] - o
        return Jet(c)

    def __rsub__(self, o):
        c = [-a for a in self.c]
        c[0] = c[0] + o
        return Jet(c)

    def __mul__(self, o):
        if isinstance(o, Jet):
            a, b = self.c, o.c
            return Jet([mp.fsum(a[i] * b[k - i] for i in range(k + 1)) if k else a[0] * b[0]
                        for k in range(DEG + 1)])
        return Jet([a * o for a in self.c])

    __rmul__ = __mul__

    def recip(self):
        b = self.c
        r = [1 / b[0]]
        for k in range(1, DEG + 1):
            r.append(-mp.fsum(b[i] * r[k - i] for i in range(1, k + 1)) * r[0])
        return Jet(r)

    def __truediv__(self, o):
        if isinstance(o, Jet):
            return self * o.recip()
        return Jet([a / o for a in self.c])

    def __rtruediv__(self, o):
        return self.recip() * o

    def __pow__(self, m):
        if not isinstance(m, int):
            raise TypeError('integer powers only')
        if m < 0:
            return self.recip() ** (-m)
        out = Jet.const(1)
        base = self
        while m:
            if m & 1:
                out = out * base
            base = base * base
            m >>= 1
        return out

    def __eq__(self, o):
        if isinstance(o, Jet):
            return all(a == b for a, b in zip(self.c, o.c))
        return self.c[0] == o and all(a == 0 for a in self.c[1:])

    def __ne__(self, o):
        return not self.__eq__(o)

    __hash__ = None

    def __abs__(self):
        return abs(self.c[0])

    def __repr__(self):
        return 'Jet(%s)' % ', '.join(mp.nstr(a, 12) for a in self.c)


def c0(x):
    return x.c[0] if isinstance(x, Jet) else x


def tojet(x):
    return x if isinstance(x, Jet) else Jet.const(x)


def _compose(x, derivs):
    """f(x) for x = x0 + delta, given derivs = [f(x0), f'(x0), ..., f^(D)(x0)]."""
    if not isinstance(x, Jet):
        return derivs[0]
    dl = Jet([mp.mpc(0)] + x.c[1:])
    out = Jet.const(derivs[0])
    p = Jet.const(1)
    for k in range(1, DEG + 1):
        p = p * dl
        out = out + p * (derivs[k] / mp.factorial(k))
    return out


def jexp(x):
    if not isinstance(x, Jet):
        return mp.exp(x)
    e0 = mp.exp(x.c[0])
    return _compose(x, [e0] * (DEG + 1))


def jlog(x):
    if not isinstance(x, Jet):
        return mp.log(x)
    a = x.c[0]
    der = [mp.log(a)] + [(-1) ** (k + 1) * mp.factorial(k - 1) / a ** k for k in range(1, DEG + 1)]
    return _compose(x, der)


def jpow_scalar_base(n, s):
    """n^s for a positive scalar n and a jet (or scalar) exponent s."""
    if not isinstance(s, Jet):
        return mp.power(n, s)
    L = mp.log(n)
    p0 = mp.power(n, s.c[0])
    der = [p0 * L ** k for k in range(DEG + 1)]
    return _compose(s, der)


def _loggamma_exp(x, sign):
    """Gamma(x)^sign for a jet x: Gamma(x0)^sign exp(sign sum_k psi_{k-1}(x0) delta^k / k!)."""
    a = x.c[0]
    dl = Jet([mp.mpc(0)] + x.c[1:])
    lg = Jet.const(0)
    p = Jet.const(1)
    for k in range(1, DEG + 1):
        p = p * dl
        lg = lg + p * (sign * mp.psi(k - 1, a) / mp.factorial(k))
    base = mp.gamma(a) if sign > 0 else mp.rgamma(a)
    return jexp(lg) * base


def jgamma(x):
    return _loggamma_exp(x, 1) if isinstance(x, Jet) else mp.gamma(x)


def jrgamma(x):
    return _loggamma_exp(x, -1) if isinstance(x, Jet) else mp.rgamma(x)


def jbernpoly(n, x):
    if not isinstance(x, Jet):
        return mp.bernpoly(n, x)
    a = x.c[0]
    der = []
    for k in range(DEG + 1):
        der.append(mp.factorial(n) / mp.factorial(n - k) * mp.bernpoly(n - k, a) if k <= n else mp.mpc(0))
    return _compose(x, der)


def jsum(terms):
    terms = list(terms)
    if not any(isinstance(t, Jet) for t in terms):
        return mp.fsum(terms)
    cols = [[] for _ in range(DEG + 1)]
    for t in terms:
        if isinstance(t, Jet):
            for k in range(DEG + 1):
                cols[k].append(t.c[k])
        else:
            cols[0].append(t)
    return Jet([mp.fsum(c) if c else mp.mpc(0) for c in cols])


# ----------------------------------------------------------------------------------------------
# Hurwitz zeta (Euler-Maclaurin, relative precision), jet exponent
# ----------------------------------------------------------------------------------------------
def jhz_batch(s0, N, K):
    """[zeta(s0+k, N) for k = 0..K] with s0 a jet: same algorithm as hypsums.hz_batch."""
    if not isinstance(s0, Jet):
        from hypsums import hz_batch
        return hz_batch(s0, N, K)
    dps = mp.mp.dps
    twoJ = 2 * ((dps + 40) // 2)
    J = twoJ // 2
    sc = s0.c[0]
    ap = int(max(N, mp.ceil((abs(sc) + K + twoJ) / (2 * mp.pi) * mp.mpf(10) ** (mp.mpf(dps + 10) / twoJ))))
    # direct part: sum_{n=N}^{ap-1} n^{-s0-k}; jets of n^{-s0} = n^{-sc} * exp(-(s0-sc) log n)
    acc = [[mp.mpc(0)] * (DEG + 1) for _ in range(K + 1)]
    dl = [mp.mpc(0)] + s0.c[1:]
    for n in range(N, ap):
        L = mp.log(n)
        # e = exp(-dl * L) as a jet in eps
        e = jexp(Jet([-x * L for x in dl]))
        p0 = mp.power(n, -sc)
        inv = mp.mpf(1) / n
        base = [x * p0 for x in e.c]
        pk = mp.mpf(1)
        for k in range(K + 1):
            row = acc[k]
            for i in range(DEG + 1):
                row[i] += base[i] * pk
            pk *= inv
    out = [Jet(r) for r in acc]
    bf = _bern_over_fact(J)
    a = mp.mpf(ap)
    p = jpow_scalar_base(a, -s0)
    inva = 1 / a
    inva2 = inva * inva
    for k in range(K + 1):
        s = s0 + k
        tot = a * p / (s - 1) + p / 2
        poch = s
        term = p * inva
        for j in range(1, J + 1):
            tot = tot + poch * term * bf[j]
            poch = poch * ((s + (2 * j - 1)) * (s + 2 * j))
            term = term * inva2
        out[k] = out[k] + tot
        p = p * inva
    return out


# ----------------------------------------------------------------------------------------------
# sequences (jet parameters)
# ----------------------------------------------------------------------------------------------
def _series_exp(L, K):
    E = [Jet.const(1)] + [Jet.const(0)] * K
    for k in range(1, K + 1):
        E[k] = jsum(j * L[j] * E[k - j] for j in range(1, k + 1)) / k
    return E


def jconv(a, b, K):
    c = [Jet.const(0)] * (K + 1)
    for i, x in enumerate(a[:K + 1]):
        if x == 0:
            continue
        for j in range(min(len(b) - 1, K - i) + 1):
            c[i + j] = c[i + j] + x * b[j]
    return c


class JGammaSeq:
    """T_n = T0 prod (alpha)_n^mu/(beta)_n^mu, alpha/beta jets or scalars."""

    def __init__(self, factors, T0=1):
        self.factors = [(a, b, int(m)) for a, b, m in factors]
        self.T0 = T0
        self.poly = False

    def values(self, N):
        out = []
        t = tojet(self.T0)
        for n in range(N):
            out.append(t)
            r = Jet.const(1)
            for a, b, m in self.factors:
                r = r * (((a + n) / (b + n)) ** m)
            t = t * r
        return out

    def asym(self, K):
        s = jsum(-m * (a - b) for a, b, m in self.factors)
        L = [Jet.const(0)] * (K + 1)
        for j in range(1, K + 1):
            L[j] = jsum(m * (-1) ** (j + 1) * (jbernpoly(j + 1, a) - jbernpoly(j + 1, b))
                        for a, b, m in self.factors) / (j * (j + 1))
        C = tojet(self.T0)
        for a, b, m in self.factors:
            C = C * ((jgamma(b) * jrgamma(a)) ** m)
        E = _series_exp(L, K)
        return s, [C * e for e in E]

    def product(self, other):
        return JGammaSeq(self.factors + other.factors, tojet(self.T0) * tojet(other.T0))


def _values(T, N):
    """values of a jet sequence (JGammaSeq) or of a constant one (hypsums GammaSeq / PolySeq, plain mpc)."""
    return T.values(N)


def _asym(T, K):
    return T.asym(K)


def jsingle_sum(T, p=0, N=60, K=40):
    vals = _values(T, N)
    part = jsum((mp.mpf(n) ** p if (n or p) else 1) * v for n, v in enumerate(vals))
    s, tau = _asym(T, K)
    z = jhz_batch(s - p, N, K)
    return part + jsum(tau[k] * z[k] for k in range(K + 1))


def jreg_moments(T, K, N, Kst=None, vals=None, asym=None):
    if getattr(T, 'poly', False):
        return [Jet.const(x) for x in T.reg_moments(K)]
    Kst = Kst or K
    if vals is None:
        vals = _values(T, N)
    s, tau = asym if asym is not None else _asym(T, Kst)
    Z = jhz_batch(s - K, N, K + Kst)
    out = []
    pw = [mp.mpf(1)] * N
    for k in range(K + 1):
        if k == 0:
            part = jsum(vals)
        else:
            for n in range(N):
                pw[n] = pw[n] * n
            part = jsum(vals[n] * pw[n] for n in range(N))
        tail = jsum(tau[j] * Z[j - k + K] for j in range(Kst + 1))
        out.append(part + tail)
    return out


def _rf(x, k):
    r = Jet.const(1)
    for i in range(k):
        r = r * (x + i)
    return r


def jconv_sum(X, Y, Z, M=120, N=None, K=40, muY=None, muZ=None):
    """sum_{m>=0} X_m sum_{n<=m} Y_{m-n} Z_n with jet parameters (algorithm of hypsums.conv_sum)."""
    N = N or M // 2
    xv, yv, zv = _values(X, M), _values(Y, M), _values(Z, M)
    part = Jet.const(0)
    for m in range(M):
        h = jsum(yv[m - n] * zv[n] for n in range(m + 1))
        part = part + xv[m] * h
    x, xi = _asym(X, K)
    y, ups = _asym(Y, K)
    z, zet = _asym(Z, K)
    x, y, z = tojet(x), tojet(y), tojet(z)
    poly = getattr(Y, 'poly', False)
    if muZ is None:
        KZ = min(K, Y.deg) if poly else K
        muZ = jreg_moments(Z, KZ, N, Kst=K, vals=zv[:N], asym=(z, zet))
    if muY is None:
        muY = jreg_moments(Y, K, N, vals=yv[:N], asym=(y, ups))
    muY = [tojet(v) for v in muY]
    muZ = [tojet(v) for v in muZ]
    # precomputed Gamma factors of the C family: Gamma(1-y-a), Gamma(1-z-c), 1/Gamma(2-y-z-i)
    if not poly:
        Gy = [jgamma(1 - y)]
        for a in range(1, K + 1):
            Gy.append(Gy[-1] / (-y - (a - 1)))          # Gamma(w-1) = Gamma(w)/(w-1), w = 1-y-(a-1)
        RG = [jrgamma(2 - y - z)]
        for i in range(1, K + 1):
            RG.append(RG[-1] * (1 - y - z - (i - 1)))   # 1/Gamma(w-1) = (w-1)/Gamma(w), w = 2-y-z-(i-1)
    Gz = [jgamma(1 - z)]
    for c in range(1, K + 1):
        Gz.append(Gz[-1] / (-z - (c - 1)))
    A = [Jet.const(0)] * (K + 1)
    B = [Jet.const(0)] * (K + 1)
    C = [Jet.const(0)] * (K + 1)
    for i in range(K + 1):
        acc = []
        for a in range(i + 1):
            if ups[a] == 0:
                continue
            k = i - a
            if poly:
                dega = Y.deg - a
                if k > dega:
                    continue
            acc.append(ups[a] * _rf(y + a, k) * muZ[k] / mp.factorial(k))
        A[i] = jsum(acc) if acc else Jet.const(0)
        acc = []
        for c in range(i + 1):
            k = i - c
            acc.append(zet[c] * _rf(z + c, k) * muY[k] / mp.factorial(k))
        B[i] = jsum(acc)
        acc = []
        for a in range(i + 1):
            if ups[a] == 0:
                continue
            c = i - a
            if poly:
                dega = Y.deg - a
                acc.append(ups[a] * zet[c] * mp.factorial(dega) / _rf(1 - z - c, dega + 1))
            else:
                acc.append(ups[a] * zet[c] * Gy[a] * Gz[c] * RG[a + c])
        C[i] = jsum(acc) if acc else Jet.const(0)
    xa, xb, xc = jconv(xi, A, K), jconv(xi, B, K), jconv(xi, C, K)
    za = jhz_batch(x + y, M, K)
    zb = jhz_batch(x + z, M, K)
    zc = jhz_batch(x + y + z - 1, M, K)
    tail = jsum(xa[n] * za[n] + xb[n] * zb[n] + xc[n] * zc[n] for n in range(K + 1))
    return part + tail


def jmoment_product_sum(Xpoly, P, Q, N=60, K=40):
    deg = Xpoly.deg
    MP = [jsingle_sum(P, p, N, K) for p in range(deg + 1)]
    MQ = [jsingle_sum(Q, p, N, K) for p in range(deg + 1)]
    tot = Jet.const(0)
    for p, kp in enumerate(Xpoly.kappa):
        if kp == 0:
            continue
        for i in range(p + 1):
            tot = tot + MP[i] * MQ[p - i] * (kp * mp.binomial(p, i))
    return tot


# ----------------------------------------------------------------------------------------------
# the five blocks with b = d/2 + eps
# ----------------------------------------------------------------------------------------------
def _isint(x, n):
    return isinstance(x, int) and x == n


class JWheel3:
    """r = 3 blocks of the foundation's Wheel with jet rim exponent b = b0 + eps."""

    def __init__(self, d, b0=None, M=None, K=None, N=None):
        self.r = 3
        self.d = d
        dm = mp.mpmathify(d)
        self.q = dm / 4
        b0 = dm / 2 if b0 is None else mp.mpmathify(b0)
        self.b = Jet.var(b0)
        self.sig = self.b / 2
        self.g = 2 * self.q - self.sig
        dps = mp.mp.dps
        self.M = M or max(80, int(1.6 * dps))
        self.K = K or max(30, int(0.8 * dps) + 10)
        self.N = N or self.M // 2
        q = self.q
        if _isint(d, 1):
            self.mult = 'delta'
            self.pref4q = mp.mpf(1)
        elif _isint(d, 2):
            self.mult = PolySeq([1])
            self.pref4q = mp.mpf(2)
        elif _isint(d, 3):
            self.mult = PolySeq([1, mp.mpf(2) / 3])
            self.pref4q = mp.mpf(3)
        else:
            self.mult = GammaSeq([(2 * q + 1, 2 * q, 1), (4 * q - 1, 2, 1)])   # b-independent: plain mpc
            self.pref4q = 4 * q
            self.muD = [Jet.const(mp.mpc((-1) ** (k + 1) / (4 * q))) for k in range(self.K + 1)]

    def Nb(self):
        return mp.gamma(2 * self.q) * jgamma(self.g) * jrgamma(self.sig)

    def A0(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        pre = (jgamma(s + t) * jgamma(-t) * jrgamma(2 * q + t) * jrgamma(g - t)) ** r
        T = JGammaSeq([(s + t, 2 * q + t, r), (1 - g + t, 1 + t, r)])
        return pre * jsingle_sum(T, 0, self.N, self.K)

    def Aplus(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        pre = (jgamma(1 + s + t) * jgamma(-t) * jrgamma(1 + 2 * q + t) * jrgamma(g - t)) ** r * self.pref4q
        F = JGammaSeq([(1 + s + t, 1 + 2 * q + t, r)])
        Gs = JGammaSeq([(1 - g + t, 1 + t, r)])
        if self.mult == 'delta':
            return pre * jsingle_sum(F.product(Gs), 0, self.N, self.K)
        return pre * jconv_sum(F, self.mult, Gs, M=self.M, N=self.N, K=self.K, muY=getattr(self, 'muD', None))

    def Cmid(self, t):
        r, q, s, g = self.r, self.q, self.sig, self.g
        pre = (jgamma(s + t) * jgamma(1 - t) * jrgamma(2 * q + t) * jrgamma(1 + g - t)) ** r * self.pref4q
        if self.mult == 'delta':
            return pre
        P = JGammaSeq([(1 - t, 1 + g - t, r)])
        Q = JGammaSeq([(s + t, 2 * q + t, r)])
        if getattr(self.mult, 'poly', False):
            return pre * jmoment_product_sum(self.mult, P, Q, self.N, self.K)
        return pre * jconv_sum(self.mult, P, Q, M=self.M, N=self.N, K=self.K)

    def blocks(self, which=('R0', 'R1', 'M0', 'M1', 'MC')):
        r, q, s, g = self.r, self.q, self.sig, self.g
        out = {}
        if 'R0' in which:
            out['R0'] = jsingle_sum(JGammaSeq([(s, 2 * q, r), (1 - g, 1, r)]), 0, self.N, self.K)
        if 'R1' in which:
            F = JGammaSeq([(1 + s, 1 + 2 * q, r)])
            Gs = JGammaSeq([(1 - g, 1, r)])
            pre = (s / (2 * q)) ** r * self.pref4q
            if self.mult == 'delta':
                out['R1'] = pre * jsingle_sum(F.product(Gs), 0, self.N, self.K)
            else:
                out['R1'] = pre * jconv_sum(F, self.mult, Gs, M=self.M, N=self.N, K=self.K,
                                            muY=getattr(self, 'muD', None))
        tb = (1 - s) / 2
        N3 = self.Nb() ** r
        if 'M0' in which:
            out['M0'] = N3 * self.A0(tb) * 2
        if 'M1' in which:
            out['M1'] = N3 * self.Aplus(tb) * 2
        if 'MC' in which:
            out['MC'] = N3 * self.Cmid(tb)
        return out


def block_jets(d, which=('R0', 'R1', 'M0', 'M1', 'MC'), **kw):
    """{block: [f, f', f'', ...]} at b = d/2 (derivatives, not Taylor coefficients)."""
    w = JWheel3(d, **kw)
    bl = w.blocks(which)
    return {k: [v.c[j] * mp.factorial(j) for j in range(DEG + 1)] for k, v in bl.items()}


def parse_d(x):
    """'1','2','3' -> exact int (polynomial multiplicities); 'a/b' -> exact rational; else decimal."""
    if x in ('1', '2', '3'):
        return int(x)
    if '/' in x:
        a, b = x.split('/')
        return mp.mpf(int(a)) / int(b)
    return mp.mpf(x)


def _task(args):
    dstr, name, dps, deg = args
    global DEG
    DEG = deg
    mp.mp.dps = dps + 15
    d = parse_d(dstr)
    st = time.time()
    bj = block_jets(d, which=(name,))
    return (dstr, name), ([mp.nstr(x, dps + 10) for x in bj[name]], time.time() - st)


def main():
    from multiprocessing import Pool
    sys.path.insert(0, _HERE)
    import z_blocks as zb
    out, dps, ds = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
    deg = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    mp.mp.dps = dps + 15
    names = ('R0', 'R1', 'M0', 'M1', 'MC')
    tasks = [(dstr, n, dps, deg) for dstr in ds for n in names]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    st = time.time()
    with Pool(min(workers, len(tasks))) as pool:
        res = dict(pool.map(_task, tasks, chunksize=1))
    result = dict(dps=dps, engine='jets', deg=deg, results={})
    for dstr in ds:
        d = parse_d(dstr)
        q = mp.mpf(d) / 4
        jets = {n: [mp.mpmathify(x) for x in res[(dstr, n)][0]] for n in names}
        Rj = [jets['R0'][j] + jets['R1'][j] for j in range(3)]
        Mj = [jets['M0'][j] + jets['M1'][j] + jets['MC'][j] for j in range(3)]
        W0, W1, Z = zb.assemble(q, Rj, Mj)
        Zred, elim = zb.assemble_reduced(q, Rj, Mj)
        Zc0, c0j = zb.zero_mode_form(q, Rj, Mj)
        result['results'][dstr] = dict(
            blocks={n: [mp.nstr(x, dps) for x in jets[n]] for n in names},
            seconds={n: res[(dstr, n)][1] for n in names},
            R=[mp.nstr(x, dps) for x in Rj], Mh=[mp.nstr(x, dps) for x in Mj],
            W=mp.nstr(W0, dps), dW=mp.nstr(W1, dps), Z=mp.nstr(Z, dps), Z_reduced=mp.nstr(Zred, dps),
            eliminated=elim, Z_zero_mode_form=mp.nstr(Zc0, dps), c0hat=[mp.nstr(x, dps) for x in c0j])
        print('d=%s  W=%s  dW=%s  Z=%s  Zred=%s' % (dstr, mp.nstr(mp.re(W0), 30), mp.nstr(W1, 5),
                                                  mp.nstr(mp.re(Z), 35), mp.nstr(mp.re(Zred), 35)), flush=True)
    result['seconds'] = time.time() - st
    json.dump(result, open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))


if __name__ == '__main__':
    main()
