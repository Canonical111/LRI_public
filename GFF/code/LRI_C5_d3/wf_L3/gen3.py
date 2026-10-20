"""d=3 balanced four-wheel W_4(3;b) for a general (complex) rim exponent b, through the
half-shift reduction of the condensed note (td:*), generalized from b=3/2 to arbitrary b.

Notation (session L3):
  sigma = b/2,   gamma = 3/2 - sigma (Barnes gap),   alpha = (1-gamma)/2,
  h(z) = Gamma(z+alpha)/Gamma(z+1-alpha)                     (h ~ z^-gamma)
  u = t + alpha  (t = Barnes shift),   X = k+u+1/2, Y = j+u, d_l = 2l+1 = 2(X-Y)
  U_m(v)   = sum_{n>=0} (n+v)^m h(n+v)^4                     (ordinary moments)
  Psi_m(u) = sin^4(pi(u+alpha)) U_m(u) + (-1)^m sin^4(pi(alpha-u)) U_m(1-u)
           = a + c cos(2 pi u)  (m=0),   b sin(2 pi u)  (m=1)      [finite modes, every gamma>1/2]
  Tp(u)    = sum_{k>=j>=0} 2(X-Y) h(X)^4 h(Y)^4              (right-tail Horn function)
  Xi(u)    = s(u) Tp(u) + s(-u) Tp(1/2-u) + mid(u),  s(u) = sin^4(2 pi(u+alpha))/16,
  mid(u)   = sin^4(pi(alpha-u)) cos^4(pi(u+alpha)) 2[U_1(u+1/2)U_0(1-u)+U_0(u+1/2)U_1(1-u)]
  Xi(u)    = sum_{k=0}^{3} c_k cos(2 pi k (u+1/4)),  c_1 = 2ab, c_3 = 0 (half-shift determinant)
  W_4      = pref^4 * E_4(sigma; c),  pref = Gamma(3/2)Gamma(gamma)/Gamma(3/2-gamma),
  E_4      = -sum_k B_{4,k}(sigma) c_k/(pi sin(pi sigma))^4    (fp:finiteFunctional, q -> sigma)
At b = 3/2 (gamma = 3/4) this is exactly td:wheelSample / td:P4answer.
Tails: Stirling-Bernoulli expansions + Hurwitz zeta (numerical acceleration, not a bound).
"""
import mpmath as mp


def conv(a, b, K):
    c = [mp.mpc(0)] * (K + 1)
    for i, x in enumerate(a):
        if not x:
            continue
        for j in range(min(len(b) - 1, K - i) + 1):
            c[i + j] += x * b[j]
    return c


def coeffs(A, B, r, delta, m, K):
    """(n+delta)^m [Gamma(n+A)/Gamma(n+B)]^r ~ n^(-al) sum_k c_k n^-k, al = r(B-A)-m."""
    logs = [mp.mpc(0)] + [r * (-1) ** (j + 1) * (mp.bernpoly(j + 1, A) - mp.bernpoly(j + 1, B)) / (j * (j + 1))
                          for j in range(1, K + 1)]
    ex = [mp.mpc(1)]
    for j in range(1, K + 1):
        ex.append(mp.fsum(h * logs[h] * ex[j - h] for h in range(1, j + 1)) / j)
    poly = [mp.binomial(m, j) * delta ** j for j in range(m + 1)]
    return conv(ex, poly, K)



_BCACHE = {}


def _bern_over_fact(J):
    key = (J, mp.mp.prec)
    if key not in _BCACHE:
        _BCACHE[key] = [mp.bernoulli(2 * j) / mp.factorial(2 * j) for j in range(J + 1)]
    return _BCACHE[key]


def hz_batch(s0, N, K):
    """[zeta(s0+k, N) for k=0..K], N a positive integer, s0 complex allowed.
    mpmath's zeta(s,a) has only ABSOLUTE accuracy ~10^-dps for complex s (relative error huge when
    |zeta| is tiny), so it must not be used here.  Direct sum up to a', then Euler-Maclaurin at a'."""
    dps = mp.mp.dps
    twoJ = 2 * ((dps + 40) // 2)
    J = twoJ // 2
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


def moment(A, B, r, delta, m, N, K):
    """sum_{n>=0} (n+delta)^m [Gamma(n+A)/Gamma(n+B)]^r."""
    alpha = r * (B - A) - m
    c = coeffs(A, B, r, delta, m, K)
    h = (mp.gamma(A) / mp.gamma(B)) ** r
    partial = mp.mpc(0)
    for n in range(N):
        partial += (n + delta) ** m * h
        h *= ((n + A) / (n + B)) ** r
    z = hz_batch(alpha, N, K)
    return partial + mp.fsum(c[k] * z[k] for k in range(K + 1))


def tail_coefficients(c, alpha, K):
    """sum_{j>k} j^-alpha sum_i c_i j^-i  ~  k^(1-alpha) sum_i T_i k^-i   (Euler-Maclaurin of zeta(s,k+1))."""
    out = [mp.mpc(0)] * (K + 1)
    for j in range(K + 1):
        s = alpha + j
        out[j] += c[j] / (s - 1)
        if j + 1 <= K:
            out[j + 1] -= c[j] / 2
        for h in range(1, (K - j) // 2 + 1):
            out[j + 2 * h] += c[j] * mp.bernoulli(2 * h) / mp.factorial(2 * h) * mp.rf(s, 2 * h - 1)
    return out


def ordered(A, B, da, m, C, D, db, n, r, N, K):
    """sum_{k>=j>=0} (k+da)^m [G(k+A)/G(k+B)]^r (j+db)^n [G(j+C)/G(j+D)]^r."""
    alpha = r * (B - A) - m
    beta = r * (D - C) - n
    ca = coeffs(A, B, r, da, m, K)
    cb = coeffs(C, D, r, db, n, K)
    btotal = moment(C, D, r, db, n, N, K)
    ha = (mp.gamma(A) / mp.gamma(B)) ** r
    hb = (mp.gamma(C) / mp.gamma(D)) ** r
    prefix = mp.mpc(0)
    val = mp.mpc(0)
    for k in range(N):
        prefix += (k + db) ** n * hb
        val += (k + da) ** m * ha * prefix
        ha *= ((k + A) / (k + B)) ** r
        hb *= ((k + C) / (k + D)) ** r
    za = hz_batch(alpha, N, K)
    val += btotal * mp.fsum(ca[j] * za[j] for j in range(K + 1))
    tb = tail_coefficients(cb, beta, K)
    prod = conv(ca, tb, K)
    zb = hz_batch(alpha + beta - 1, N, K)
    val -= mp.fsum(prod[j] * zb[j] for j in range(K + 1))
    return val


class D3:
    def __init__(self, gamma, N=120, K=48):
        self.g = mp.mpmathify(gamma)
        self.al = (1 - self.g) / 2
        self.N, self.K = N, K
        self._U = {}
        self._T = {}

    def U(self, m, v):
        key = (m, str(v))
        if key not in self._U:
            v = mp.mpmathify(v)
            self._U[key] = moment(v + self.al, v + 1 - self.al, 4, v, m, self.N, self.K)
        return self._U[key]

    def Psi(self, m, u):
        al = self.al
        first = mp.sin(mp.pi * (u + al)) ** 4 * self.U(m, u)
        s2 = mp.sin(mp.pi * (al - u)) ** 4
        second = 0 if abs(s2) < mp.eps ** 0.75 else (-1) ** m * s2 * self.U(m, 1 - u)
        return first + second

    def Tp(self, u):
        key = str(u)
        if key not in self._T:
            u = mp.mpmathify(u)
            al = self.al
            A, B, da = u + mp.mpf(1) / 2 + al, u + mp.mpf(3) / 2 - al, u + mp.mpf(1) / 2
            C, Dd, db = u + al, u + 1 - al, u
            o10 = ordered(A, B, da, 1, C, Dd, db, 0, 4, self.N, self.K)
            o01 = ordered(A, B, da, 0, C, Dd, db, 1, 4, self.N, self.K)
            self._T[key] = 2 * (o10 - o01)
        return self._T[key]

    def s(self, u):
        return mp.sin(2 * mp.pi * (u + self.al)) ** 4 / 16

    def mid(self, u):
        al = self.al
        f = mp.sin(mp.pi * (al - u)) ** 4 * mp.cos(mp.pi * (u + al)) ** 4
        if abs(f) < mp.eps ** 0.75:
            return mp.mpc(0)
        x, z = u + mp.mpf(1) / 2, 1 - u
        return f * 2 * (self.U(1, x) * self.U(0, z) + self.U(0, x) * self.U(1, z))

    def Xi(self, u):
        u = mp.mpmathify(u)
        out = self.s(u) * self.Tp(u) + self.mid(u)
        sl = self.s(-u)
        if abs(sl) > mp.eps ** 0.75:
            out += sl * self.Tp(mp.mpf(1) / 2 - u)
        return out

    # ordinary amplitudes: Psi_0 = a + c cos 2 pi u, Psi_1 = b sin 2 pi u
    def amps(self):
        al = self.al
        # b from u = alpha (second term vanishes): Psi_1(alpha) = b sin(2 pi alpha)
        b = self.Psi(1, al) / mp.sin(2 * mp.pi * al)
        p_al = self.Psi(0, al)               # a + c cos(2 pi alpha)
        p_q = self.Psi(0, mp.mpf(1) / 4)     # a
        a = p_q
        c = (p_al - a) / mp.cos(2 * mp.pi * al)
        return a, b, c

    def cks(self):
        """Fourier coefficients c_0,c_1,c_2 of Xi in cos(2 pi k(u+1/4)); c_1=2ab, c_3=0 used."""
        a, b, c = self.amps()
        c1 = 2 * a * b
        al = self.al
        # E(u) = [Xi(u)+Xi(u+1/2)]/2 = c0 - c2 cos(4 pi u); Xi(u+1/2) = Xi(u) + 4ab sin(2 pi u)
        E_al = self.Xi(al) + 2 * a * b * mp.sin(2 * mp.pi * al)
        E_q = self.Xi(mp.mpf(1) / 4) + 2 * a * b
        # c0 - c2 cos(4 pi al) = E_al ; c0 + c2 = E_q
        cc = mp.cos(4 * mp.pi * al)
        c2 = (E_q - E_al) / (1 + cc)
        c0 = E_q - c2
        return c0, c1, c2, dict(a=a, b=b, c=c, E_al=E_al, E_q=E_q)


def bell(xs):
    E = [mp.mpc(1)]
    for m in range(1, len(xs) + 1):
        E.append(mp.fsum(xs[h - 1] / mp.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m)
    return E


def Bweights(r, sig):
    """B_{r,k}(sigma), k=0..r-1, fp:finiteFunctional with q -> sigma (complex allowed)."""
    us = []
    for h in range(1, r):
        L = (-1) ** (h + 1) * mp.psi(h - 1, 1 - sig) - mp.psi(h - 1, sig)
        us.append(r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - L))
    out = []
    for k in range(r):
        xp = [us[0] + 2j * mp.pi * k] + us[1:]
        xm = [us[0] - 2j * mp.pi * k] + us[1:]
        out.append((mp.expj(mp.pi * k * sig) * bell(xp)[r - 1] + mp.expj(-mp.pi * k * sig) * bell(xm)[r - 1]) / 2)
    return out


def W4(gamma, N=120, K=48, full=False):
    g = mp.mpmathify(gamma)
    sig = mp.mpf(3) / 2 - g
    d = D3(g, N, K)
    c0, c1, c2, info = d.cks()
    cs = [c0, c1, c2, mp.mpc(0)]
    Bw = Bweights(4, sig)
    E4 = -mp.fsum(Bw[k] * cs[k] for k in range(4)) / (mp.pi * mp.sin(mp.pi * sig)) ** 4
    pref = mp.gamma(mp.mpf(3) / 2) * mp.gamma(g) / mp.gamma(mp.mpf(3) / 2 - g)
    W = pref ** 4 * E4
    if full:
        return W, dict(ck=cs, B=Bw, pref=pref, **info)
    return W
