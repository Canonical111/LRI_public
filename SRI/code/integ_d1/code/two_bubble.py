"""Two-bubble (four-kink) connected cluster J2(K, delta) of the s<1 kink gas in a field, analytically continued in K.

J2 = J2gap - J1 * J1t,
J2gap = int dr1 dr2 dgam e^{-r1-r2} [W4 E4 - W2W2 E2]   (gap gam between the bubbles, 0..inf),
J1t   = int r W2(r) e^{-r} dr  (overlap term of the Mayer cluster).
Weights: W = prod_{pairs} x_ij^{2K q_i q_j}, and the delta-expansion of f_delta = (x^delta - 1)/delta gives
E = exp(K d Lam2 + (K/3) d^2 Lam3 + (K/12) d^3 Lam4),  Lam_r = sum_pairs q q (ell + L_ij)^r,  L_ij = log x_ij.

Radial variable R = r1 + r2: r1 = R t, r2 = R (1-t), gam = R g. Then ell^m -> Gamma^{(m)}(3 - 4K) exactly.
Angular domain: t in [0, 1/2] (doubled by bubble exchange), g in [0, inf). Pieces:
  A1: t <= g <= 1/2, W4 only     g = sig/2, t = sig s/2
  A2: g <= t <= 1/2, W4 only     t = sig/2, g = sig s/2
  AW: t, g in [0, 1/2], W2W2 only (independent of g)
  BC: t in [0,1/2], g in [1/2, inf), combined W2W2 [C E4 - E2], cluster property manifest; g = 1/(2v).
Each piece is sig^{e1} s^{e2} * sum_{p,q} (log sig)^p (log s)^q G_pq(sig, s). Analytic continuation: Taylor
subtraction in each variable to order -floor(e(w=0)) (Cauchy-integral derivatives), with analytic integrals
int_0^1 x^c log^p x dx = (-1)^p p! / (c+1)^{p+1}."""
import mpmath as mp
from functools import lru_cache

# ---------------------------------------------------------------- polynomials in (ell, Ls, Lt)
class P:
    __slots__ = ('c',)
    def __init__(self, c=None): self.c = c or {}
    @staticmethod
    def const(v): return P({(0, 0, 0): v})
    @staticmethod
    def lin(c0, a_ell, a1, a2):
        d = {}
        if c0 != 0: d[(0, 0, 0)] = c0
        if a_ell: d[(1, 0, 0)] = mp.mpf(a_ell)
        if a1: d[(0, 1, 0)] = mp.mpf(a1)
        if a2: d[(0, 0, 1)] = mp.mpf(a2)
        return P(d)
    def __add__(s, o):
        if not isinstance(o, P): o = P.const(o)
        r = dict(s.c)
        for k, v in o.c.items(): r[k] = r.get(k, 0) + v
        return P(r)
    __radd__ = __add__
    def __sub__(s, o):
        if not isinstance(o, P): o = P.const(o)
        r = dict(s.c)
        for k, v in o.c.items(): r[k] = r.get(k, 0) - v
        return P(r)
    def __mul__(s, o):
        if not isinstance(o, P): return P({k: v * o for k, v in s.c.items()})
        r = {}
        for (a, b, c), v in s.c.items():
            for (d, e, f), u in o.c.items():
                key = (a + d, b + e, c + f); r[key] = r.get(key, 0) + v * u
        return P(r)
    __rmul__ = __mul__
    def pw(s, n):
        r = P.const(mp.mpf(1))
        for _ in range(n): r = r * s
        return r

def E_series(K, Lam):
    """delta^0..3 coefficients of exp(K d Lam2 + K/3 d^2 Lam3 + K/12 d^3 Lam4)."""
    L2, L3, L4 = Lam[2], Lam[3], Lam[4]
    E1 = K * L2
    E2 = (K / 3) * L3 + (K * K / 2) * (L2 * L2)
    E3 = (K / 12) * L4 + (K * K / 3) * (L3 * L2) + (K ** 3 / 6) * (L2 * L2 * L2)
    return [P.const(mp.mpf(1)), E1, E2, E3]

def Lam_of(pairs, rmax=4):
    """pairs: list of (qq, linear P for ell + L_ij). Returns {r: sum qq (ell+L)^r}."""
    out = {}
    for r in range(2, rmax + 1):
        acc = P()
        for qq, lin in pairs:
            acc = acc + lin.pw(r) * qq
        out[r] = acc
    return out

# ---------------------------------------------------------------- one bubble (closed forms)
def bell_m(s, nmax):
    psi = [mp.polygamma(k, s) for k in range(nmax + 1)]
    m = [mp.mpf(1)]
    for n in range(nmax):
        m.append(sum(mp.binomial(n, k) * psi[k] * m[n - k] for k in range(n + 1)))
    return m
def one_bubble(K, extra_r):
    """int r^{extra} W2(r) e^{-r} dr, delta^0..3, with W2 = exp(-2K f_delta(r)) expanded (log insertions)."""
    s = 1 - 2 * K + extra_r
    m = bell_m(s, 7); g = mp.gamma(s)
    return [g, g * (-K * m[2]), g * (-(K / 3) * m[3] + (K ** 2 / 2) * m[4]),
            g * (-(K / 12) * m[4] + (K ** 2 / 3) * m[5] - (K ** 3 / 6) * m[6])]

# ---------------------------------------------------------------- the angular pieces
def gamma_derivs(a, nmax=6):
    m = bell_m(a, nmax); g = mp.gamma(a)
    return [g * m[n] for n in range(nmax + 1)]

def radial_fold(poly, Gd):
    """replace ell^m by Gamma^{(m)}(3-4K): returns dict {(p,q): value}."""
    out = {}
    for (m, p, q), v in poly.c.items():
        out[(p, q)] = out.get((p, q), 0) + v * Gd[m]
    return out

LOG2 = mp.log(2)

def piece_A(which, K, sig, s, Gd):
    """A1/A2 (W4 only). Returns ({k: {(p,q): G}}, e1, e2) with the monomial sig^{e1} s^{e2} removed."""
    tK = 2 * K
    if which == 'A1':      # g = sig/2, t = sig s/2
        t = sig * s / 2; g = sig / 2
        # (qq, alpha_sig, beta_s, regular part)
        X = {'01': (-1, 1, 1, mp.mpf(1) / 2), '23': (-1, 0, 0, 1 - t), '12': (-1, 1, 0, mp.mpf(1) / 2),
             '02': (+1, 1, 0, (1 + s) / 2), '13': (+1, 0, 0, g + 1 - t), '03': (-1, 0, 0, 1 + g)}
    else:                  # A2: t = sig/2, g = sig s/2
        t = sig / 2; g = sig * s / 2
        X = {'01': (-1, 1, 0, mp.mpf(1) / 2), '23': (-1, 0, 0, 1 - t), '12': (-1, 1, 1, mp.mpf(1) / 2),
             '02': (+1, 1, 0, (1 + s) / 2), '13': (+1, 0, 0, g + 1 - t), '03': (-1, 0, 0, 1 + g)}
    e1 = 1 + sum(tK * qq * a for qq, a, b, r in X.values())
    e2 = sum(tK * qq * b for qq, a, b, r in X.values())
    reg = mp.mpf(1) / 4
    for qq, a, b, r in X.values():
        reg *= r ** (tK * qq)
    pairs = [(qq, P.lin(mp.log(r), 1, a, b)) for qq, a, b, r in X.values()]
    E = E_series(K, Lam_of(pairs))
    return {k: {pq: v * reg for pq, v in radial_fold(E[k], Gd).items()} for k in range(4)}, e1, e2

def piece_AW(K, sig, s, Gd):
    """W2W2 over t, g in [0,1/2]: t = sig/2, g = s/2 (integrand independent of s)."""
    tK = 2 * K
    t = sig / 2
    X = {'01': (-1, 1, 0, mp.mpf(1) / 2), '23': (-1, 0, 0, 1 - t)}
    e1 = sum(tK * qq * a for qq, a, b, r in X.values())
    reg = mp.mpf(1) / 4
    for qq, a, b, r in X.values():
        reg *= r ** (tK * qq)
    pairs = [(qq, P.lin(mp.log(r), 1, a, b)) for qq, a, b, r in X.values()]
    E = E_series(K, Lam_of(pairs))
    return {k: {pq: v * reg for pq, v in radial_fold(E[k], Gd).items()} for k in range(4)}, e1, mp.mpf(0)

def piece_BC(K, sig, v, Gd):
    """t = sig/2 in [0,1/2], g = 1/(2v) in [1/2, inf): W2W2 [C E4 - E2], cluster property manifest.
    Returned G already divided by v^2 (the O(v^2) decay), so e2 = 0."""
    tK = 2 * K
    t = sig / 2
    # intra pairs
    intra = [(-1, P.lin(mp.log(mp.mpf(1) / 2), 1, 1, 0)), (-1, P.lin(mp.log(1 - t), 1, 0, 0))]
    e1 = -tK
    reg = (mp.mpf(1) / 2) ** (-tK) * (1 - t) ** (-tK) / 4          # Jacobian 1/4 v^-2 (v^-2 cancels the decay)
    # cross pairs: L = -Lv + log(1/2) + eps; q q: 02 +, 13 +, 12 -, 03 -
    one_p_2v = 1 + 2 * v
    e02 = mp.log1p(sig * v)                                         # log(1 + sig v)
    D13 = mp.log1p(-sig * v / one_p_2v)                             # log(1+2v-sig v) - log(1+2v)
    A03 = mp.log1p(2 * v)
    X1 = mp.log1p(sig * (2 - sig) * v * v / one_p_2v)               # sum qq eps = e02 + (A03 + D13) - A03
    def S(mpow):     # sum_cross qq eps^m, accurate:  e02^m + (A03+D13)^m - A03^m
        if mpow == 1: return X1
        return e02 ** mpow + sum(mp.binomial(mpow, j) * A03 ** (mpow - j) * D13 ** j for j in range(1, mpow + 1))
    B = P.lin(mp.log(mp.mpf(1) / 2), 1, 0, -1)                      # ell - Lv + log(1/2)
    Lc = {}
    for r in (2, 3, 4):
        acc = P()
        for mm in range(1, r + 1):
            acc = acc + B.pw(r - mm) * (mp.binomial(r, mm) * S(mm))
        Lc[r] = acc
    L2i = Lam_of(intra)
    L4_2 = L2i[2] + Lc[2]
    d = [P(), K * Lc[2],
         (K / 3) * Lc[3] + (K * K / 2) * (Lc[2] * (L4_2 + L2i[2])),
         (K / 12) * Lc[4] + (K * K / 3) * (Lc[3] * L4_2 + L2i[3] * Lc[2])
         + (K ** 3 / 6) * (Lc[2] * (L4_2 * L4_2 + L4_2 * L2i[2] + L2i[2] * L2i[2]))]
    E4 = E_series(K, {2: L4_2, 3: L2i[3] + Lc[3], 4: L2i[4] + Lc[4]})
    Cm1 = mp.expm1(tK * X1)
    inv_v2 = 1 / (v * v)
    out = {}
    for k in range(4):
        comb = E4[k] * Cm1 + d[k]
        out[k] = {pq: val * reg * inv_v2 for pq, val in radial_fold(comb, Gd).items()}
    return out, e1, mp.mpf(0)

# ---------------------------------------------------------------- numerical machinery
def ts_nodes(level, dps):
    """tanh-sinh nodes/weights on [0,1]."""
    h = mp.mpf(2) ** (-level)
    xs, ws = [], []
    kmax = int(mp.ceil(mp.mpf(4.0) / h))
    for kk in range(-kmax, kmax + 1):
        tt = kk * h
        u = mp.pi / 2 * mp.sinh(tt)
        x = (mp.tanh(u) + 1) / 2
        wgt = h * mp.pi / 4 * mp.cosh(tt) / mp.cosh(u) ** 2
        if x <= 0 or x >= 1 or wgt < mp.mpf(10) ** (-dps - 5): continue
        xs.append(x); ws.append(wgt)
    return xs, ws

def cauchy_derivs(f, nmax, rad, npts):
    """Taylor coefficients f^{(n)}(0)/n!, n < nmax, of a function returning {key: value}."""
    acc = {}
    for j in range(npts):
        z = rad * mp.expjpi(2 * mp.mpf(j) / npts)
        val = f(z)
        for key, x in val.items():
            a = acc.setdefault(key, [0] * nmax)
            for n in range(nmax):
                a[n] += x * z ** (-n)
    return {key: [x / npts for x in a] for key, a in acc.items()}

def analytic_int(c, p):
    return (-1) ** p * mp.factorial(p) / (c + 1) ** (p + 1)

def flatten(G):   # {k: {(p,q): v}} -> {(k,p,q): v}
    return {(k, p, q): v for k, d in G.items() for (p, q), v in d.items()}

def integrate_piece(fun, K, Gd, nodes, cauchy=(mp.mpf('0.25'), 64), nmax=28, x0=mp.mpf('0.05')):
    """int_0^1 int_0^1 sig^{e1} s^{e2} sum (log sig)^p (log s)^q G_kpq  dsig ds  -> {k: value}.
    Analytic continuation by Taylor subtraction (orders N1, N2). Near a subtracted boundary (x < x0) the remainder
    is evaluated from its Taylor series (Cauchy coefficients up to nmax), never by differencing, so no roundoff is
    amplified by the negative powers."""
    xs, ws = nodes
    G0, e1, e2 = fun(K, mp.mpf('0.5'), mp.mpf('0.5'), Gd)
    a1 = int(mp.floor(mp.re(e1) + mp.mpf('0.5'))); a2 = int(mp.floor(mp.re(e2) + mp.mpf('0.5')))
    N1, N2 = max(0, -a1), max(0, -a2)
    rad, npc = cauchy
    F = lambda x, y: flatten(fun(K, x, y, Gd)[0])
    res = {}
    def addto(k, val): res[k] = res.get(k, 0) + val
    M1 = nmax if N1 else 0
    M2 = nmax if N2 else 0
    # Taylor tables: in sig at every s-node, in s at every sig-node, and the 2D table at the origin
    Tsig = [cauchy_derivs(lambda z, y=y: F(z, y), M1 + 1, rad, npc) if N1 else None for y in xs]
    Ts = [cauchy_derivs(lambda z, x=x: F(x, z), M2 + 1, rad, npc) if N2 else None for x in xs]
    C00 = {}
    if N1 and N2:
        raw = cauchy_derivs(lambda z1: {kk + (n,): vv for kk, lst in
                                        cauchy_derivs(lambda z2: F(z1, z2), M2 + 1, rad, npc).items()
                                        for n, vv in enumerate(lst)}, M1 + 1, rad, npc)
        for (k_, p_, q_, n2), lst in raw.items():
            mat = C00.setdefault((k_, p_, q_), [[0] * (M2 + 1) for _ in range(M1 + 1)])
            for n1 in range(M1 + 1):
                mat[n1][n2] = lst[n1]
    def RR(i, j, key, Gval):
        """R_sig R_s G at node (xs[i], xs[j])."""
        x, y = xs[i], xs[j]
        sx, sy = (N1 and x < x0), (N2 and y < x0)
        if not sx and not sy:
            r = Gval
            if N1: r -= sum(Tsig[j][key][n] * x ** n for n in range(N1)) if key in Tsig[j] else 0
            if N2: r -= sum(Ts[i][key][m] * y ** m for m in range(N2)) if key in Ts[i] else 0
            if N1 and N2 and key in C00:
                r += sum(C00[key][n][m] * x ** n * y ** m for n in range(N1) for m in range(N2))
            return r
        if sx and not sy:
            cs = Tsig[j].get(key)
            if cs is None: return 0
            r = 0
            for n in range(N1, M1 + 1):
                cn = cs[n]
                if N2 and key in C00: cn -= sum(C00[key][n][m] * y ** m for m in range(N2))
                r += cn * x ** n
            return r
        if sy and not sx:
            ds = Ts[i].get(key)
            if ds is None: return 0
            r = 0
            for m in range(N2, M2 + 1):
                dm = ds[m]
                if N1 and key in C00: dm -= sum(C00[key][n][m] * x ** n for n in range(N1))
                r += dm * y ** m
            return r
        if key not in C00: return 0
        return sum(C00[key][n][m] * x ** n * y ** m for n in range(N1, M1 + 1) for m in range(N2, M2 + 1))
    keys = None
    for i, x in enumerate(xs):
        lx = mp.log(x)
        for j, y in enumerate(xs):
            ly = mp.log(y)
            need_G = not ((N1 and x < x0) or (N2 and y < x0))
            Gv = F(x, y) if need_G else None
            if keys is None and Gv is not None: keys = list(Gv.keys())
            klist = Gv.keys() if Gv is not None else (keys or list(F(mp.mpf('0.5'), mp.mpf('0.5')).keys()))
            w = ws[i] * ws[j] * x ** e1 * y ** e2
            for key in klist:
                k, p, q = key
                r = RR(i, j, key, Gv[key] if Gv is not None else None)
                if r != 0: addto(k, w * r * lx ** p * ly ** q)
    # T_sig R_s : analytic in sig, numeric in s
    if N1:
        for j, y in enumerate(xs):
            ly = mp.log(y)
            for key, lst in Tsig[j].items():
                k, p, q = key
                for n in range(N1):
                    if N2 and y < x0:
                        r = sum(C00[key][n][m] * y ** m for m in range(N2, M2 + 1)) if key in C00 else 0
                    else:
                        r = lst[n]
                        if N2 and key in C00: r -= sum(C00[key][n][m] * y ** m for m in range(N2))
                    addto(k, ws[j] * y ** e2 * ly ** q * r * analytic_int(e1 + n, p))
    # R_sig T_s
    if N2:
        for i, x in enumerate(xs):
            lx = mp.log(x)
            for key, lst in Ts[i].items():
                k, p, q = key
                for m in range(N2):
                    if N1 and x < x0:
                        r = sum(C00[key][n][m] * x ** n for n in range(N1, M1 + 1)) if key in C00 else 0
                    else:
                        r = lst[m]
                        if N1 and key in C00: r -= sum(C00[key][n][m] * x ** n for n in range(N1))
                    addto(k, ws[i] * x ** e1 * lx ** p * r * analytic_int(e2 + m, q))
    # T_sig T_s
    if N1 and N2:
        for key, mat in C00.items():
            k, p, q = key
            for n1 in range(N1):
                for n2 in range(N2):
                    addto(k, mat[n1][n2] * analytic_int(e1 + n1, p) * analytic_int(e2 + n2, q))
    return res

def J2(K, level=6, cauchy=(mp.mpf('0.25'), 64)):
    """J2^{(k)}(K), k = 0..3 (delta-expansion coefficients), analytically continued."""
    Gd = gamma_derivs(3 - 4 * K)
    nodes = ts_nodes(level, mp.mp.dps)
    tot = {}
    for fun, sign in ((lambda K_, a, b, G: piece_A('A1', K_, a, b, G), 1),
                      (lambda K_, a, b, G: piece_A('A2', K_, a, b, G), 1),
                      (piece_AW, -1),
                      (piece_BC, 1)):
        r = integrate_piece(fun, K, Gd, nodes, cauchy)
        for k, v in r.items(): tot[k] = tot.get(k, 0) + 2 * sign * v
    J1 = one_bubble(K, 0); J1t = one_bubble(K, 1)
    for k in range(4):
        tot[k] = tot.get(k, 0) - sum(J1[i] * J1t[k - i] for i in range(k + 1))
    return [tot.get(k, 0) for k in range(4)]

def J2_BA(K):
    """exact delta = 0 two-bubble cluster from the Bethe-ansatz magnetization formula."""
    a10 = 2 * (2 * K - 1) * mp.gamma(1 - 2 * K)
    R = mp.sqrt(mp.pi) * mp.gamma(mp.mpf(5) / 2 - 2 * K) * mp.gamma(1 - K) ** 2 / (
        2 * mp.gamma(1 - 2 * K) * mp.gamma(mp.mpf(3) / 2 - K) ** 2)
    return a10 ** 2 * R / (2 * (4 * K - 3))
