"""Independent numerical helpers (written from scratch for this review).

- em_tail(f, N, K, r, M): Euler-Maclaurin tail sum_{n>=N} f(n) for analytic f.
  Derivatives from a Cauchy-circle trapezoid (radius r, M points); the
  integral int_N^inf f via x = N/u on [0,1] with tanh-sinh.
- richardson(S, Ns): polynomial extrapolation of partial sums in h = 1/N.
- euler_avg(partials, m): m-fold averaging of consecutive partial sums
  (Euler / van Wijngaarden) for alternating series.
- cvz(a, n): Cohen-Villegas-Zagier algorithm 1 for sum (-1)^k a_k.
"""
import mpmath as mp


def em_tail(f, N, K=20, r=None, M=None, quad_tail=True):
    N = mp.mpf(N)
    if r is None:
        r = N / 2
    if M is None:
        M = int(3.5 * mp.mp.dps) + 80
    # Taylor coefficients c_m = f^{(m)}(N)/m! via trapezoid on circle
    vals = []
    for j in range(M):
        w = mp.expjpi(mp.mpf(2 * j) / M)
        vals.append(f(N + r * w))
    coef = []
    for m in range(2 * K):
        s = mp.mpc(0)
        for j in range(M):
            s += vals[j] * mp.expjpi(-mp.mpf(2 * j * m) / M)
        coef.append((s / M / r ** m).real)
    # integral
    dps0 = mp.mp.dps
    def g(u):
        if u == 0:
            return mp.mpf(0)
        x = N / u
        extra = int(mp.log10(x)) + 15
        if extra > 2 * dps0 + 15:
            return mp.mpf(0)  # node weight below 10^-2dps: negligible
        with mp.workdps(dps0 + extra):
            x = mp.mpf(N) / u
            v = f(x) * N / u ** 2
        return +v
    I = mp.quad(g, [0, mp.mpf(1) / 4, mp.mpf(1) / 2, 1])
    tail = I + coef[0] / 2
    for k in range(1, K + 1):
        d = coef[2 * k - 1] * mp.factorial(2 * k - 1)
        tail -= mp.bernoulli(2 * k) / mp.factorial(2 * k) * d
    return tail, I


def richardson(S, Ns):
    """Extrapolate S(N) -> N=inf assuming S(N) = S + sum_k c_k N^-k.
    Neville on h=1/N."""
    hs = [mp.mpf(1) / n for n in Ns]
    P = list(S)
    n = len(P)
    # Neville evaluation at h=0
    for k in range(1, n):
        for i in range(n - k):
            P[i] = (P[i + 1] * hs[i] - P[i] * hs[i + k]) / (hs[i] - hs[i + k])
    return P[0]


def euler_avg(partials, m):
    """partials: list of consecutive partial sums S_N..S_{N+m}; returns m-fold average."""
    P = list(partials[: m + 1])
    for k in range(m):
        P = [(P[i] + P[i + 1]) / 2 for i in range(len(P) - 1)]
    return P[0]


def cvz(a, n):
    """CVZ algorithm 1: sum_{k>=0} (-1)^k a[k] using a[0..n-1]."""
    d = (3 + mp.sqrt(8)) ** n
    d = (d + 1 / d) / 2
    b = mp.mpf(-1)
    c = -d
    s = mp.mpf(0)
    for k in range(n):
        c = b - c
        s = s + c * a[k]
        b = (k + n) * (k - n) * b / ((k + mp.mpf(1) / 2) * (k + 1))
    return s / d
