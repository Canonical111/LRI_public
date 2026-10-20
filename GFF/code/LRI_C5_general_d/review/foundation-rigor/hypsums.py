#!/usr/bin/env python3
"""Accelerated evaluation of the one- and two-variable hypergeometric (Horn) sums at unit argument
that occur in the finite-sample formula for the balanced wheels W_r(d;b).

Sequences.  A Gamma-ratio sequence is
    T_n = T_0 * prod_i [ (alpha_i)_n / (beta_i)_n ]^{mu_i},   n >= 0,   mu_i integer,
with large-n (Stirling) data   T_n ~ sum_k tau_k n^{-s-k},   s = -sum_i mu_i (alpha_i - beta_i),
    tau_k = T_0 prod_i [Gamma(beta_i)/Gamma(alpha_i)]^{mu_i} * [n^-k] exp( sum_j L_j n^-j ),
    L_j   = sum_i mu_i (-1)^{j+1} (B_{j+1}(alpha_i) - B_{j+1}(beta_i)) / (j (j+1)).
A polynomial sequence T_n = sum_p kappa_p n^p is the same data with a FINITE exact expansion.

Sums.
  single_sum(T, p)       = sum_{n>=0} n^p T_n
  conv_sum(X, Y, Z)      = sum_{m>=0} X_m sum_{n=0}^{m} Y_{m-n} Z_n          (two-variable Horn sum)
Both are computed as an exact finite part plus an asymptotic tail: the tail of a sequence with Stirling data is a
finite combination of Hurwitz zeta values zeta(s+k, M), evaluated by Euler-Maclaurin with every term carrying
M^-s (NOT mpmath.zeta(s, a), whose complex-s values have an absolute error floor ~10^-dps).
For the convolution H = Y*Z the large-m expansion has three families (generating-function transfer at x = 1):
    H_m ~ sum_i [ A_i m^{-y-i} + B_i m^{-z-i} + C_i m^{1-y-z-i} ],
    A_i = sum_{a+k=i} upsilon_a (y+a)_k/k! mu_k^Z ,   B_i = sum_{c+k=i} zeta_c (z+c)_k/k! mu_k^Y ,
    C_i = sum_{a+c=i} upsilon_a zeta_c Gamma(1-y-a) Gamma(1-z-c) / Gamma(2-y-z-a-c),
with mu_k the zeta-regularized moments  mu_k^Z = "sum_n n^k Z_n"  (analytically continued in the parameters).
This is numerical acceleration (asymptotic series truncated at its small terms), not an interval bound.
Exceptional parameters: the generic formulas have removable poles when z (or y) is a positive integer
(resonance, log m terms); polynomial Y is treated exactly and is pole-free in the convergent domain.
"""
import mpmath as mp

# ----------------------------------------------------------------------------------------------
# Hurwitz zeta, robust for complex s (relative precision)
# ----------------------------------------------------------------------------------------------
_BCACHE = {}


def _bern_over_fact(J):
    key = (J, mp.mp.prec)
    if key not in _BCACHE:
        _BCACHE[key] = [mp.bernoulli(2 * j) / mp.factorial(2 * j) for j in range(J + 1)]
    return _BCACHE[key]


def hz_batch(s0, N, K):
    """[zeta(s0+k, N) for k = 0..K], N a positive integer, s0 complex.  Direct sum up to a' >= N, then
    Euler-Maclaurin at a' (every term carries a'^-s, so the result has relative precision)."""
    dps = mp.mp.dps
    twoJ = 2 * ((dps + 40) // 2)
    J = twoJ // 2
    s0 = mp.mpc(s0)
    ap = int(max(N, mp.ceil((abs(s0) + K + twoJ) / (2 * mp.pi) * mp.mpf(10) ** (mp.mpf(dps + 10) / twoJ))))
    out = [mp.mpc(0)] * (K + 1)
    for n in range(N, ap):
        p = mp.power(n, -s0)
        inv = mp.mpf(1) / n
        for k in range(K + 1):
            out[k] += p
            p *= inv
    bf = _bern_over_fact(J)
    a = mp.mpf(ap)
    p = mp.power(a, -s0)
    inva = 1 / a
    inva2 = inva * inva
    for k in range(K + 1):
        s = s0 + k
        tot = a * p / (s - 1) + p / 2
        poch = s           # (s)_{2j-1}
        term = p * inva    # a^{-s-2j+1}
        for j in range(1, J + 1):
            tot += bf[j] * poch * term
            poch *= (s + 2 * j - 1) * (s + 2 * j)
            term *= inva2
        out[k] += tot
        p *= inva
    return out


# ----------------------------------------------------------------------------------------------
# sequences
# ----------------------------------------------------------------------------------------------
def _series_exp(L, K):
    """coefficients of exp(sum_{j>=1} L[j] x^j) up to x^K (L[0] ignored)."""
    E = [mp.mpc(1)] + [mp.mpc(0)] * K
    for k in range(1, K + 1):
        E[k] = mp.fsum(j * L[j] * E[k - j] for j in range(1, k + 1)) / k
    return E


def conv(a, b, K):
    c = [mp.mpc(0)] * (K + 1)
    for i, x in enumerate(a[:K + 1]):
        if x == 0:
            continue
        for j in range(min(len(b) - 1, K - i) + 1):
            c[i + j] += x * b[j]
    return c


class GammaSeq:
    """T_n = T0 * prod (alpha)_n^mu / (beta)_n^mu  for factors (alpha, beta, mu)."""

    def __init__(self, factors, T0=1):
        self.factors = [(mp.mpmathify(a), mp.mpmathify(b), int(m)) for a, b, m in factors]
        self.T0 = mp.mpmathify(T0)
        self.poly = False

    def values(self, N):
        out = []
        t = mp.mpc(self.T0)
        for n in range(N):
            out.append(t)
            r = mp.mpc(1)
            for a, b, m in self.factors:
                r *= ((n + a) / (n + b)) ** m
            t = t * r
        return out

    def asym(self, K):
        """(s, tau[0..K]) with T_n ~ sum_k tau_k n^{-s-k}."""
        s = -mp.fsum(m * (a - b) for a, b, m in self.factors)
        L = [mp.mpc(0)] * (K + 1)
        for j in range(1, K + 1):
            L[j] = mp.fsum(m * (-1) ** (j + 1) * (mp.bernpoly(j + 1, a) - mp.bernpoly(j + 1, b))
                           for a, b, m in self.factors) / (j * (j + 1))
        C = self.T0
        for a, b, m in self.factors:
            C *= (mp.gamma(b) * mp.rgamma(a)) ** m
        E = _series_exp(L, K)
        return s, [C * e for e in E]

    def product(self, other):
        return GammaSeq(self.factors + other.factors, self.T0 * other.T0)


class PolySeq:
    """T_n = sum_p kappa[p] n^p (exact, all n >= 0, with 0^0 = 1)."""

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
        """T_n = sum_{a=0}^{deg} kappa[deg-a] n^{deg-a}:  s = -deg, tau_a = kappa[deg-a]."""
        tau = [mp.mpc(self.kappa[self.deg - a]) if a <= self.deg else mp.mpc(0) for a in range(K + 1)]
        return mp.mpf(-self.deg), tau

    def reg_moments(self, K):
        """exact zeta-regularized moments  sum_{n>=0} n^k T_n = sum_p kappa_p [delta_{k+p,0} + zeta(-k-p)]."""
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
    part = mp.fsum((mp.mpf(n) ** p if (n or p) else 1) * v for n, v in enumerate(vals))
    s, tau = T.asym(K)
    z = hz_batch(s - p, N, K)
    return part + mp.fsum(tau[k] * z[k] for k in range(K + 1))


def reg_moments(T, K, N, Kst=None, vals=None, asym=None):
    """zeta-regularized moments mu_k = sum_{n>=0} n^k T_n, k = 0..K (partial sum to N + Hurwitz tails)."""
    if getattr(T, 'poly', False):
        return T.reg_moments(K)
    Kst = Kst or K
    if vals is None:
        vals = T.values(N)
    s, tau = asym if asym is not None else T.asym(Kst)
    # need zeta(s + j - k, N) for j in 0..Kst, k in 0..K: exponents s - K + m, m = 0..K+Kst
    Z = hz_batch(s - K, N, K + Kst)
    out = []
    pw = [mp.mpc(1)] * N   # n^k (with 0^0 = 1), built incrementally
    for k in range(K + 1):
        if k == 0:
            part = mp.fsum(vals)
        else:
            for n in range(N):
                pw[n] = pw[n] * n
            part = mp.fsum(pw[n] * vals[n] for n in range(N))
        tail = mp.fsum(tau[j] * Z[j - k + K] for j in range(Kst + 1))
        out.append(part + tail)
    return out


def _rf(x, k):
    """rising factorial (x)_k for complex x, integer k >= 0."""
    r = mp.mpc(1)
    for i in range(k):
        r *= x + i
    return r


def conv_sum(X, Y, Z, M=120, N=None, K=40, muY=None, muZ=None, info=None):
    """sum_{m>=0} X_m H_m,  H_m = sum_{n=0}^m Y_{m-n} Z_n.
    X, Z: GammaSeq;  Y: GammaSeq or PolySeq.  muY/muZ: optional precomputed regularized moments."""
    N = N or M // 2
    xv, yv, zv = X.values(M), Y.values(M), Z.values(M)
    part = mp.mpc(0)
    for m in range(M):
        h = mp.fsum(yv[m - n] * zv[n] for n in range(m + 1))
        part += xv[m] * h
    x, xi = X.asym(K)
    y, ups = Y.asym(K)
    z, zet = Z.asym(K)
    poly = getattr(Y, 'poly', False)
    if muZ is None:
        # polynomial Y only needs the (convergent) moments k <= deg Y: no resonance poles
        KZ = min(K, Y.deg) if poly else K
        muZ = reg_moments(Z, KZ, N, Kst=K, vals=zv[:N], asym=(z, zet))
    if muY is None:
        muY = reg_moments(Y, K, N, vals=yv[:N], asym=(y, ups))
    A = [mp.mpc(0)] * (K + 1)
    B = [mp.mpc(0)] * (K + 1)
    C = [mp.mpc(0)] * (K + 1)
    for i in range(K + 1):
        # A family
        acc = mp.mpc(0)
        for a in range(i + 1):
            if ups[a] == 0:
                continue
            k = i - a
            if poly:
                dega = Y.deg - a            # -(y+a) is a nonnegative integer
                if k > dega:
                    continue
            acc += ups[a] * _rf(y + a, k) / mp.factorial(k) * muZ[k]
        A[i] = acc
        # B family
        acc = mp.mpc(0)
        for c in range(i + 1):
            k = i - c
            acc += zet[c] * _rf(z + c, k) / mp.factorial(k) * muY[k]
        B[i] = acc
        # C family
        acc = mp.mpc(0)
        for a in range(i + 1):
            if ups[a] == 0:
                continue
            c = i - a
            if poly:
                dega = Y.deg - a
                # Gamma(1-y-a) Gamma(1-z-c)/Gamma(2-y-z-a-c) = dega! / (1-z-c)_{dega+1}
                acc += ups[a] * zet[c] * mp.factorial(dega) / _rf(1 - z - c, dega + 1)
            else:
                acc += ups[a] * zet[c] * mp.gamma(1 - y - a) * mp.gamma(1 - z - c) * mp.rgamma(2 - y - z - a - c)
        C[i] = acc
    xa, xb, xc = conv(xi, A, K), conv(xi, B, K), conv(xi, C, K)
    za = hz_batch(x + y, M, K)
    zb = hz_batch(x + z, M, K)
    zc = hz_batch(x + y + z - 1, M, K)
    tail = mp.fsum(xa[n] * za[n] + xb[n] * zb[n] + xc[n] * zc[n] for n in range(K + 1))
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
            tot += kp * mp.binomial(p, i) * MP[i] * MQ[p - i]
    return tot
