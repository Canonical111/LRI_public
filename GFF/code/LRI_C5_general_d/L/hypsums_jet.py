#!/usr/bin/env python3
"""Jet-generic version of foundation/hypsums.py (session L).

Same algorithm as the foundation module (exact finite part + Stirling/Bernoulli asymptotic tail summed with
Euler-Maclaurin Hurwitz zeta values; Cauchy convolutions by the three-family large-index expansion with
zeta-regularized moments), but every parameter may be a first-order jet (jet.J).  Passing parameters that are
affine functions of the rim exponent b, built from b = J(b0, 1), returns J(F, dF/db) for every sum F.
Because the tail is an analytic function of the parameters, the derivative of the evaluated expression is the
evaluated expression of the derivative series: the polygamma-weighted sum
    d/dp sum_n T_n = sum_n T_n * d/dp log T_n ,   d/dp log (a)_n = psi(a+n) - psi(a),
with its tail (now containing log n terms, i.e. Hurwitz derivatives in s) accelerated identically.

Sequences:  T_n = T0 prod_i [(alpha_i)_n/(beta_i)_n]^{mu_i},  T_n ~ sum_k tau_k n^{-s-k}.
Sums:       single_sum(T,p) = sum_n n^p T_n,   conv_sum(X,Y,Z) = sum_m X_m sum_{n<=m} Y_{m-n} Z_n.
"""
import mpmath as mp
from jet import J, val, cnum, num, jsum, jgamma, jrgamma, jpow, jbernpoly

_BCACHE = {}


def _bern_over_fact(Jn):
    key = (Jn, mp.mp.prec)
    if key not in _BCACHE:
        _BCACHE[key] = [mp.bernoulli(2 * j) / mp.factorial(2 * j) for j in range(Jn + 1)]
    return _BCACHE[key]


def hz_batch(s0, N, K):
    """[zeta(s0+k, N) for k = 0..K] (jets allowed in s0).  Direct sum to a' >= N, then Euler-Maclaurin at a'.
    For a jet s0 the derivative is d/ds zeta(s+k, N) = -sum_{n>=N} log(n) n^{-s-k}, obtained from the same
    formula differentiated exactly."""
    dps = mp.mp.dps
    twoJ = 2 * ((dps + 40) // 2)
    Jn = twoJ // 2
    s0 = cnum(s0)
    sv = val(s0)
    ap = int(max(N, mp.ceil((abs(sv) + K + twoJ) / (2 * mp.pi) * mp.mpf(10) ** (mp.mpf(dps + 10) / twoJ))))
    isj = isinstance(s0, J)
    # direct part: value sums and log-weighted sums separately (faster than generic jets)
    outv = [mp.mpc(0)] * (K + 1)
    outl = [mp.mpc(0)] * (K + 1)
    for n in range(N, ap):
        p = mp.power(n, -sv)
        inv = mp.mpf(1) / n
        ln = mp.log(n)
        for k in range(K + 1):
            outv[k] += p
            if isj:
                outl[k] += ln * p
            p *= inv
    if isj:
        out = [J(outv[k], -outl[k] * s0.d) for k in range(K + 1)]
    else:
        out = outv
    bf = _bern_over_fact(Jn)
    a = mp.mpf(ap)
    p = jpow(a, -s0)
    inva = 1 / a
    inva2 = inva * inva
    for k in range(K + 1):
        s = s0 + k
        tot = a * p / (s - 1) + p / 2
        poch = s           # (s)_{2j-1}
        term = p * inva    # a^{-s-2j+1}
        for j in range(1, Jn + 1):
            tot = tot + bf[j] * poch * term
            poch = poch * ((s + 2 * j - 1) * (s + 2 * j))
            term = term * inva2
        out[k] = out[k] + tot
        p = p * inva
    return out


# ----------------------------------------------------------------------------------------------
# sequences
# ----------------------------------------------------------------------------------------------
def _series_exp(L, K):
    """coefficients of exp(sum_{j>=1} L[j] x^j) up to x^K (L[0] ignored)."""
    E = [mp.mpc(1)] + [mp.mpc(0)] * K
    for k in range(1, K + 1):
        E[k] = jsum(j * L[j] * E[k - j] for j in range(1, k + 1)) / k
    return E


def conv(a, b, K):
    c = [mp.mpc(0)] * (K + 1)
    for i, x in enumerate(a[:K + 1]):
        if not isinstance(x, J) and x == 0:
            continue
        for j in range(min(len(b) - 1, K - i) + 1):
            c[i + j] = c[i + j] + x * b[j]
    return c


class GammaSeq:
    """T_n = T0 * prod (alpha)_n^mu / (beta)_n^mu  for factors (alpha, beta, mu); alpha, beta may be jets."""

    def __init__(self, factors, T0=1):
        self.factors = [(num(a), num(b), int(m)) for a, b, m in factors]
        self.T0 = num(T0)
        self.poly = False

    def values(self, N):
        out = []
        t = cnum(self.T0)
        for n in range(N):
            out.append(t)
            r = mp.mpc(1)
            for a, b, m in self.factors:
                r = r * ((n + a) / (n + b)) ** m
            t = t * r
        return out

    def asym(self, K):
        """(s, tau[0..K]) with T_n ~ sum_k tau_k n^{-s-k}."""
        s = -jsum(m * (a - b) for a, b, m in self.factors)
        L = [mp.mpc(0)] * (K + 1)
        for j in range(1, K + 1):
            L[j] = jsum(m * (-1) ** (j + 1) * (jbernpoly(j + 1, a) - jbernpoly(j + 1, b))
                        for a, b, m in self.factors) / (j * (j + 1))
        C = self.T0
        for a, b, m in self.factors:
            C = C * (jgamma(b) * jrgamma(a)) ** m
        E = _series_exp(L, K)
        return s, [C * e for e in E]

    def product(self, other):
        return GammaSeq(self.factors + other.factors, self.T0 * other.T0)


class PolySeq:
    """T_n = sum_p kappa[p] n^p (exact, all n >= 0, with 0^0 = 1); constant coefficients."""

    def __init__(self, kappa):
        self.kappa = [mp.mpmathify(k) for k in kappa]
        while len(self.kappa) > 1 and self.kappa[-1] == 0:
            self.kappa.pop()
        self.deg = len(self.kappa) - 1
        self.poly = True

    def values(self, N):
        return [mp.mpc(mp.fsum(k * mp.mpf(n) ** p if (n or p) else k for p, k in enumerate(self.kappa)))
                for n in range(N)]

    def asym(self, K):
        tau = [mp.mpc(self.kappa[self.deg - a]) if a <= self.deg else mp.mpc(0) for a in range(K + 1)]
        return mp.mpf(-self.deg), tau

    def reg_moments(self, K):
        out = []
        for k in range(K + 1):
            v = mp.mpf(0)
            for p, kp in enumerate(self.kappa):
                if kp == 0:
                    continue
                v += kp * ((1 if k + p == 0 else 0) + mp.zeta(-(k + p)))
            out.append(mp.mpc(v))
        return out


# ----------------------------------------------------------------------------------------------
# sums
# ----------------------------------------------------------------------------------------------
def single_sum(T, p=0, N=60, K=40):
    """sum_{n>=0} n^p T_n  (zeta-regularized = analytically continued when divergent)."""
    vals = T.values(N)
    part = jsum((mp.mpf(n) ** p if (n or p) else 1) * v for n, v in enumerate(vals))
    s, tau = T.asym(K)
    z = hz_batch(s - p, N, K)
    return part + jsum(tau[k] * z[k] for k in range(K + 1))


def reg_moments(T, K, N, Kst=None, vals=None, asym=None):
    """zeta-regularized moments mu_k = sum_{n>=0} n^k T_n, k = 0..K."""
    if getattr(T, 'poly', False):
        return T.reg_moments(K)
    Kst = Kst or K
    if vals is None:
        vals = T.values(N)
    s, tau = asym if asym is not None else T.asym(Kst)
    Z = hz_batch(s - K, N, K + Kst)
    out = []
    pw = [mp.mpc(1)] * N
    for k in range(K + 1):
        if k == 0:
            part = jsum(vals)
        else:
            for n in range(N):
                pw[n] = pw[n] * n
            part = jsum(pw[n] * vals[n] for n in range(N))
        tail = jsum(tau[j] * Z[j - k + K] for j in range(Kst + 1))
        out.append(part + tail)
    return out


def _rf(x, k):
    r = mp.mpc(1)
    for i in range(k):
        r = r * (x + i)
    return r


def conv_sum(X, Y, Z, M=120, N=None, K=40, muY=None, muZ=None, info=None):
    """sum_{m>=0} X_m H_m,  H_m = sum_{n=0}^m Y_{m-n} Z_n.  X, Z: GammaSeq; Y: GammaSeq or PolySeq."""
    N = N or M // 2
    xv, yv, zv = X.values(M), Y.values(M), Z.values(M)
    part = mp.mpc(0)
    for m in range(M):
        h = jsum(yv[m - n] * zv[n] for n in range(m + 1))
        part = part + xv[m] * h
    x, xi = X.asym(K)
    y, ups = Y.asym(K)
    z, zet = Z.asym(K)
    poly = getattr(Y, 'poly', False)
    if muZ is None:
        KZ = min(K, Y.deg) if poly else K
        muZ = reg_moments(Z, KZ, N, Kst=K, vals=zv[:N], asym=(z, zet))
    if muY is None:
        muY = reg_moments(Y, K, N, vals=yv[:N], asym=(y, ups))
    A = [mp.mpc(0)] * (K + 1)
    B = [mp.mpc(0)] * (K + 1)
    C = [mp.mpc(0)] * (K + 1)
    for i in range(K + 1):
        acc = mp.mpc(0)
        for a in range(i + 1):
            if not isinstance(ups[a], J) and ups[a] == 0:
                continue
            k = i - a
            if poly:
                dega = Y.deg - a
                if k > dega:
                    continue
            acc = acc + ups[a] * _rf(y + a, k) / mp.factorial(k) * muZ[k]
        A[i] = acc
        acc = mp.mpc(0)
        for c in range(i + 1):
            k = i - c
            acc = acc + zet[c] * _rf(z + c, k) / mp.factorial(k) * muY[k]
        B[i] = acc
        acc = mp.mpc(0)
        for a in range(i + 1):
            if not isinstance(ups[a], J) and ups[a] == 0:
                continue
            c = i - a
            if poly:
                dega = Y.deg - a
                acc = acc + ups[a] * zet[c] * mp.factorial(dega) / _rf(1 - z - c, dega + 1)
            else:
                acc = acc + ups[a] * zet[c] * jgamma(1 - y - a) * jgamma(1 - z - c) * jrgamma(2 - y - z - a - c)
        C[i] = acc
    xa, xb, xc = conv(xi, A, K), conv(xi, B, K), conv(xi, C, K)
    za = hz_batch(x + y, M, K)
    zb = hz_batch(x + z, M, K)
    zc = hz_batch(x + y + z - 1, M, K)
    tail = jsum(xa[n] * za[n] + xb[n] * zb[n] + xc[n] * zc[n] for n in range(K + 1))
    if info is not None:
        info.update(part=part, tail=tail, lastA=abs(xa[K] * za[K]), lastB=abs(xb[K] * zb[K]),
                    lastC=abs(xc[K] * zc[K]))
    return part + tail


def moment_product_sum(Xpoly, P, Q, N=60, K=40):
    """sum_{j,k>=0} X_{j+k} P_j Q_k for a polynomial X (exact binomial split into products of single moments)."""
    deg = Xpoly.deg
    MP = [single_sum(P, p, N, K) for p in range(deg + 1)]
    MQ = [single_sum(Q, p, N, K) for p in range(deg + 1)]
    tot = mp.mpc(0)
    for p, kp in enumerate(Xpoly.kappa):
        if kp == 0:
            continue
        for i in range(p + 1):
            tot = tot + kp * mp.binomial(p, i) * MP[i] * MQ[p - i]
    return tot
