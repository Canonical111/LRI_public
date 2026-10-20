#!/usr/bin/env python3
"""General-rim-exponent (b) version of the d=3 half-shift reduction for the three-wheel W_3(3;b).

Notation (derived in wf_Z3/RESULT notes):
  c = (b-1)/4,  h(x) = Gamma(x+c)/Gamma(x+1-c),  pref(b) = Gamma(3/2) Gamma((3-b)/2)/Gamma(b/2)
  Y(b) = sum_{l,n>=0} (2l+1) [Gamma(l+n+b/2) Gamma(n+(b-1)/2) / (Gamma(l+n+3/2) Gamma(n+1))]^3
       = sum_{k>=j>=0} 2(x-y) h(x)^3 h(y)^3,  x = k+c+1/2, y = j+c      (unweighted residue-prefactor sum)
  c0(b) = -a3(b) b3(b)   (Dixon 3F2 and Dougall 5F4 at a = 2c)
  Xi_3(t;b) = c0 + c1 cos(2 pi (t+b/4)),   Xi_3(0;b) = (sin(pi b)/2)^3 Y(b)
  W_3(3;b) = -pref^3 Res_{t=0} Xi_3(t;b)/D(t)^3,  D = sin(pi t) sin(pi(t+b/2))
           = E0(b) c0(b) + E1(b) Y(b)
The ordered (triangular) sums use the accelerated prefix-sum + asymptotic-tail method of
inputs/general_d3/d3_reduction.py (numerical acceleration, not an interval bound), generalized to arbitrary
complex parameters.
"""
import mpmath as mp


_BCACHE = {}


def _bern_over_fact(J):
    key = (mp.mp.prec, J)
    if key not in _BCACHE:
        _BCACHE[key] = [mp.bernoulli(2 * j) / mp.factorial(2 * j) for j in range(J + 1)]
    return _BCACHE[key]


def hz(s, a, Jmax=400):
    """Hurwitz zeta(s, a) for complex s, integer/real a >> |s|, by Euler-Maclaurin with every term carrying a^-s,
    so the result has RELATIVE precision.  (mpmath 1.3 mp.zeta(s, a) for complex s has an ABSOLUTE error floor
    ~10^-dps, which is fatal once multiplied by large asymptotic coefficients.)"""
    s = mp.mpc(s)
    a = mp.mpf(a)
    lam = mp.exp(-s * mp.log(a))            # a^-s
    res = lam * (a / (s - 1) + mp.mpf(1) / 2)
    B = _bern_over_fact(Jmax)
    t = s * lam / a                          # (s)_1 a^(-s-1)
    eps = mp.eps * abs(res) / 16
    for j in range(1, Jmax + 1):
        term = B[j] * t
        res += term
        if abs(term) < eps:
            return res
        t *= (s + 2 * j - 1) * (s + 2 * j) / (a * a)
    raise ValueError('hz: no convergence, increase a')


def conv(a, b, K):
    c = [mp.mpc(0)] * (K + 1)
    for i, x in enumerate(a):
        if not x:
            continue
        for j in range(min(len(b) - 1, K - i) + 1):
            c[i + j] += x * b[j]
    return c


def coeffs(A, B, r, delta, m, K):
    """f(n)=(n+delta)^m [Gamma(n+A)/Gamma(n+B)]^r ~ n^(-alpha) sum c[k]/n^k, alpha=r(B-A)-m."""
    logs = [mp.mpc(0)] + [r * (-1) ** (j + 1) * (mp.bernpoly(j + 1, A) - mp.bernpoly(j + 1, B)) / (j * (j + 1))
                          for j in range(1, K + 1)]
    ex = [mp.mpc(1)]
    for j in range(1, K + 1):
        ex.append(mp.fsum(h * logs[h] * ex[j - h] for h in range(1, j + 1)) / j)
    poly = [mp.binomial(m, j) * delta ** j for j in range(m + 1)]
    return conv(ex, poly, K)


def gamma_moment(A, B, r, delta, m, N, K):
    A, B, delta = map(mp.mpc, (A, B, delta))
    alpha = r * (B - A) - m
    c = coeffs(A, B, r, delta, m, K)
    h = (mp.gamma(A) / mp.gamma(B)) ** r
    partial = mp.mpc(0)
    for n in range(N):
        partial += (n + delta) ** m * h
        h *= ((n + A) / (n + B)) ** r
    return partial + mp.fsum(c[k] * hz(alpha + k, N) for k in range(K + 1))


def tail_coefficients(c, alpha, K):
    """sum_{n>k} n^(-alpha) sum_j c_j n^-j  =  k^(1-alpha) sum_i T_i k^-i  (Euler-Maclaurin)."""
    out = [mp.mpc(0)] * (K + 1)
    for j in range(K + 1):
        s = alpha + j
        out[j] += c[j] / (s - 1)
        if j + 1 <= K:
            out[j + 1] -= c[j] / 2
        for h in range(1, (K - j) // 2 + 1):
            out[j + 2 * h] += c[j] * mp.bernpoly(2 * h, 0) / mp.factorial(2 * h) * mp.rf(s, 2 * h - 1)
    return out


def ordered(A, B, da, m, C, D, db, n, r, N, K):
    """sum_{0<=j<=k} (k+da)^m [G(k+A)/G(k+B)]^r (j+db)^n [G(j+C)/G(j+D)]^r."""
    A, B, C, D, da, db = map(mp.mpc, (A, B, C, D, da, db))
    alpha = r * (B - A) - m
    beta = r * (D - C) - n
    ca = coeffs(A, B, r, da, m, K)
    cb = coeffs(C, D, r, db, n, K)
    btotal = gamma_moment(C, D, r, db, n, N, K)
    ha = (mp.gamma(A) / mp.gamma(B)) ** r
    hb = (mp.gamma(C) / mp.gamma(D)) ** r
    prefix = mp.mpc(0)
    val = mp.mpc(0)
    for k in range(N):
        prefix += (k + db) ** n * hb
        val += (k + da) ** m * ha * prefix
        ha *= ((k + A) / (k + B)) ** r
        hb *= ((k + C) / (k + D)) ** r
    val += btotal * mp.fsum(ca[j] * hz(alpha + j, N) for j in range(K + 1))
    tb = tail_coefficients(cb, beta, K)
    prod = conv(ca, tb, K)
    val -= mp.fsum(prod[j] * hz(alpha + beta - 1 + j, N) for j in range(K + 1))
    return val


def Y(b, N=120, K=48, t=0):
    """Unweighted sum Y(b) (optionally at lattice offset t: right-tail sample V(t;b) = G*H)."""
    b = mp.mpc(b)
    A, B, da = b / 2 + t, mp.mpf(3) / 2 + t, (b + 1) / 4 + t
    C, D, db = (b - 1) / 2 + t, 1 + t, (b - 1) / 4 + t
    return 2 * (ordered(A, B, da, 1, C, D, db, 0, 3, N, K) - ordered(A, B, da, 0, C, D, db, 1, 3, N, K))


def a3b3(b):
    """c0 = -a3 b3 from Dixon (3F2) and Dougall (5F4 with a cancelled pair) at a = 2c = (b-1)/2."""
    c = (mp.mpc(b) - 1) / 4
    a = 2 * c
    G = mp.gamma
    s = mp.sin(2 * mp.pi * c) ** 3
    U0 = G(a) ** 3 * G(1 + c) * G(1 - 3 * c) / (G(1 + a) * G(1 - c) ** 2 * G(1 - a))
    U1 = c * G(a) ** 3 * G((1 + a) / 2) * G((1 - 3 * a) / 2) / (G(1 + a) * G(1 - a) * G((1 - a) / 2) ** 2)
    a3 = s * U0 / mp.cos(mp.pi * c)
    b3 = s * U1 / mp.sin(mp.pi * c)
    return a3, b3


def pref(b):
    return mp.gamma(mp.mpf(3) / 2) * mp.gamma((3 - b) / 2) / mp.gamma(b / 2)


def residue_weights(b):
    """R0 = Res_{t=0} 1/D^3, R1 = Res_{t=0} cos(2 pi (t+b/4))/D^3 (exact series, closed form)."""
    pi = mp.pi
    s, co = mp.sin(pi * b / 2), mp.cos(pi * b / 2)
    # D/t = pi (1 - (pi t)^2/6) (s + pi co t - pi^2 s t^2/2) + O(t^3) = pi s (1 + u1 t + u2 t^2)
    u1 = pi * co / s
    u2 = -pi ** 2 / 2 - pi ** 2 / 6
    # (1+u1 t+u2 t^2)^-3 = 1 - 3u1 t + (6u1^2 - 3u2) t^2
    e1, e2 = -3 * u1, 6 * u1 ** 2 - 3 * u2
    lead = 1 / (pi * s) ** 3
    R0 = lead * e2
    # cos(pi b/2 + 2 pi t) = co - 2 pi s t - 2 pi^2 co t^2
    n0, n1, n2 = co, -2 * pi * s, -2 * pi ** 2 * co
    R1 = lead * (n0 * e2 + n1 * e1 + n2)
    return R0, R1


def E01(b):
    b = mp.mpc(b)
    R0, R1 = residue_weights(b)
    co = mp.cos(mp.pi * b / 2)
    P = pref(b) ** 3
    E0 = -P * (R0 - R1 / co)
    E1 = -P * (mp.sin(mp.pi * b) / 2) ** 3 * R1 / co
    return E0, E1


def W3_formula(b, N=120, K=48):
    a3, b3 = a3b3(b)
    E0, E1 = E01(b)
    return E0 * (-a3 * b3) + E1 * Y(b, N, K)
