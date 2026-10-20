"""M2 step 0: the map from the raw two-bubble cluster J2(K,delta) = sum_k delta^k J2k(w) (w = 1-K, Laurent)
to the magnetization-scheme flow coefficients f_1_n_k, and the F-analyticity (pole-cancellation) relations.

Formalism (exact): log Z/L = (2h) sum_n P^n Jn(K_h, delta), P = y^2 (2h)^-2 e^{-2(K_h - v)/delta};
  dlogP/dlogh = 2(K_h - 1), dK_h/dlogh = -delta K_h.
  M = 1 + sum_n a_n P^n,  a_n = 2[(1 + 2n(K-1)) Jn - delta K dJn/dK].
  u = ((2-delta)/4) dlogM/dlogh,  X = K M^(2-delta) - 1,  F = beta_u/(2u),  F = F0(X) + F1(X) u + O(u^2).
J1 is exact (one bubble, Gamma and polygammas); the delta^0 part of J2 is exact (Bethe ansatz)."""
import mpmath as mp, json, sys
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import provenance as _pv
mp.mp.dps = 40
KD, JMIN, JMAX = 3, -16, 14            # delta order; Laurent window in w
NPTS, RAD = 128, mp.mpf('0.15')
class S:
    """truncated bivariate series sum c[k,j] delta^k w^j (k <= KD, j <= JMAX)"""
    def __init__(self, c=None): self.c = {key: v for key, v in (c or {}).items() if v != 0}
    def __add__(s, o): o = o if isinstance(o, S) else S({(0, 0): mp.mpf(o)}); r = dict(s.c)
    def __add__(s, o):
        o = o if isinstance(o, S) else S({(0, 0): mp.mpf(o)})
        r = dict(s.c)
        for key, v in o.c.items(): r[key] = r.get(key, 0) + v
        return S(r)
    __radd__ = __add__
    def __neg__(s): return S({key: -v for key, v in s.c.items()})
    def __sub__(s, o): return s + (-(o if isinstance(o, S) else S({(0, 0): mp.mpf(o)})))
    def __rsub__(s, o): return (-s) + o
    def __mul__(s, o):
        if not isinstance(o, S): return S({key: v*o for key, v in s.c.items()})
        r = {}
        for (k1, j1), v1 in s.c.items():
            for (k2, j2), v2 in o.c.items():
                k, j = k1 + k2, j1 + j2
                if k <= KD and j <= JMAX: r[(k, j)] = r.get((k, j), 0) + v1*v2
        return S(r)
    __rmul__ = __mul__
    def dK(s):   # d/dK = -d/dw
        return S({(k, j - 1): -j*v for (k, j), v in s.c.items() if j != 0})
    def lead(s):
        k0 = min(k for k, _ in s.c); j0 = min(j for k, j in s.c if k == k0); return k0, j0
    def inv(s):
        # s = c0 w^j0 (1 + rest), require leading term at delta^0
        k0, j0 = s.lead(); assert k0 == 0
        c0 = s.c[(0, j0)]
        rest = S({(k, j - j0): v/c0 for (k, j), v in s.c.items()}) - 1
        r, term = S({(0, 0): mp.mpf(1)}), S({(0, 0): mp.mpf(1)})
        for _ in range(60):
            term = term*(-rest)
            if not term.c: break
            r = r + term
        return S({(k, j - j0): v/c0 for (k, j), v in r.c.items()})
W = S({(0, 1): mp.mpf(1)}); D = S({(1, 0): mp.mpf(1)})
K = 1 - W
def laurent(fun):
    """Laurent coefficients at w=0 of fun(w) via the trapezoidal contour rule; returns {j: c_j}."""
    pts = [RAD*mp.expjpi(2*mp.mpf(m)/NPTS) for m in range(NPTS)]
    vals = [fun(p) for p in pts]
    return {j: mp.re(sum(v*p**(-j) for v, p in zip(vals, pts))/NPTS) for j in range(JMIN, JMAX + 1)}
def mfun(s, nmax):
    psi = [mp.polygamma(k, s) for k in range(nmax + 1)]
    m = [mp.mpf(1)]
    for n in range(nmax):
        m.append(sum(mp.binomial(n, k)*psi[k]*m[n-k] for k in range(n+1)))
    return m
def J1_parts(w):
    Kc = 1 - w; s = 1 - 2*Kc; m = mfun(s, 7); g = mp.gamma(s)
    return [g, g*(-Kc*m[2]), g*(-(Kc/3)*m[3] + (Kc**2/2)*m[4]), g*(-(Kc/12)*m[4] + (Kc**2/3)*m[5] - (Kc**3/6)*m[6])]
def J20(w):
    Kc = 1 - w
    a10 = 2*(2*Kc - 1)*mp.gamma(1 - 2*Kc)
    R = mp.sqrt(mp.pi)*mp.gamma(mp.mpf(5)/2 - 2*Kc)*mp.gamma(1 - Kc)**2/(2*mp.gamma(1 - 2*Kc)*mp.gamma(mp.mpf(3)/2 - Kc)**2)
    return a10**2*R/(2*(4*Kc - 3))
def series_from(parts_by_k):
    c = {}
    for k, coeffs in parts_by_k.items():
        for j, v in coeffs.items():
            if abs(v) > mp.mpf(10)**(-30): c[(k, j)] = v
    return S(c)
J1 = series_from({k: laurent(lambda w, k=k: J1_parts(w)[k]) for k in range(KD + 1)})
J2_known = series_from({0: laurent(J20)})
def pipeline(J2):
    a1 = 2*((1 + 2*(K - 1))*J1 - D*K*J1.dK())
    a2 = 2*((1 + 4*(K - 1))*J2 - D*K*J2.dK())
    c2 = a2 - a1*a1*mp.mpf('0.5')
    pre = (2 - D)*mp.mpf('0.25')
    u1 = pre*(2*(K - 1)*a1 - D*K*a1.dK())
    u2 = pre*(4*(K - 1)*c2 - D*K*c2.dK())
    b1 = 2*(K - 1)*u1 - D*K*u1.dK()
    b2 = 4*(K - 1)*u2 - D*K*u2.dK()
    iu1 = u1.inv()
    G0 = b1*iu1*mp.mpf('0.5')
    G1 = (b2 - b1*u2*iu1)*iu1*mp.mpf('0.5')
    x1 = K*(2 - D)*a1
    F1 = (G1 - G0.dK()*x1)*iu1
    return G0, F1
G0, F1base = pipeline(J2_known)
def show(Sr, label, kmax=KD, jmin=-6, jmax=3):
    for k in range(kmax + 1):
        row = [(j, Sr.c.get((k, j), 0)) for j in range(jmin, jmax + 1)]
        print(f'{label} delta^{k}:', '  '.join(f'w^{j}:{mp.nstr(v, 10)}' for j, v in row if abs(v) > 1e-25))
show(G0, 'G0 = F(0,X,delta)', jmin=-4, jmax=2)
show(F1base, 'F1 with J2 = J2^(0) only')
# linear response of F1 to each Laurent monomial delta^k w^j of J2 (k = 1..3)
resp = {}
for k in range(1, KD + 1):
    for j in range(-12, 6):
        _, F1b = pipeline(J2_known + S({(k, j): mp.mpf(1)}))
        dF = F1b - F1base
        resp[(k, j)] = {key: v for key, v in dF.c.items() if abs(v) > mp.mpf(10)**(-25)}
_prov = _pv.step0_provenance(__file__, [], dict(KD=KD, JMIN=JMIN, JMAX=JMAX, NPTS=NPTS, RAD=str(RAD), dps=mp.mp.dps))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm2_step0_response.json'), json.dumps({'provenance': _prov, 'data':
    {f'{k},{j}': {f'{a},{b}': str(v) for (a, b), v in d.items()} for (k, j), d in resp.items()}}, indent=0))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm2_step0_F1base.json'), json.dumps({'provenance': _prov, 'data':
    {f'{a},{b}': str(v) for (a, b), v in F1base.c.items()}}, indent=0))
print('saved responses')
