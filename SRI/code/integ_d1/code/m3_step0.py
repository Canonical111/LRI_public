"""M3 step 0 (generated from m2_step0.py): second order in u. Original docstring:
M2 step 0: the map from the raw two-bubble cluster J2(K,delta) = sum_k delta^k J2k(w) (w = 1-K, Laurent)
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
KD, JMIN, JMAX = 3, -20, 16            # delta order; Laurent window in w
NPTS, RAD = 128, mp.mpf('0.05')
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
def J3_BA_fun(w):
    Kc = 1 - w
    a10 = 2*(2*Kc - 1)*mp.gamma(1 - 2*Kc)
    b = lambda n: -(-1)**(n+1)*mp.gamma(mp.mpf(1)/2 + n*(1 - Kc))/(mp.sqrt(mp.pi)*mp.factorial(n)*mp.gamma(1 - n*Kc))
    a3 = a10**3*b(3)/b(1)**3
    return a3/(2*(1 + 6*(Kc - 1)))
J3_known = series_from({0: laurent(J3_BA_fun)})
J2_full = None
def pipeline3(J2, J3):
    a1 = 2*((1 + 2*(K - 1))*J1 - D*K*J1.dK())
    a2 = 2*((1 + 4*(K - 1))*J2 - D*K*J2.dK())
    a3 = 2*((1 + 6*(K - 1))*J3 - D*K*J3.dK())
    c1 = a1; c2 = a2 - a1*a1*mp.mpf('0.5'); c3 = a3 - a1*a2 + a1*a1*a1*(mp.mpf(1)/3)
    pre = (2 - D)*mp.mpf('0.25')
    un = [pre*(2*n*(K - 1)*cn - D*K*cn.dK()) for n, cn in ((1, c1), (2, c2), (3, c3))]
    bn = [2*(n + 1)*(K - 1)*un[n] - D*K*un[n].dK() for n in range(3)]
    u1, u2, u3 = un; b1, b2, b3 = bn
    iu1 = u1.inv()
    # G = beta_u/(2u) as a series in P: (b1 + b2 P + b3 P^2) / (2 (u1 + u2 P + u3 P^2))
    q1 = u2*iu1; q2 = u3*iu1
    G0 = b1*iu1*mp.mpf('0.5')
    G1 = (b2 - b1*q1)*iu1*mp.mpf('0.5')
    G2 = (b3 - b2*q1 - b1*(q2 - q1*q1))*iu1*mp.mpf('0.5')
    tmd = 2 - D
    x1 = K*tmd*c1
    x2 = K*(tmd*c2 + tmd*tmd*c1*c1*mp.mpf('0.5'))
    F0p = G0.dK(); F0pp = F0p.dK()
    F1 = (G1 - F0p*x1)*iu1
    F1p = F1.dK()
    F2 = (G2 - F0p*x2 - F0pp*x1*x1*mp.mpf('0.5') - F1*u2 - F1p*x1*u1)*iu1*iu1
    return G0, F1, F2
import json as _js
def show(Sr, label, kmax=KD, jmin=-6, jmax=3):
    for k in range(kmax + 1):
        row = [(j, Sr.c.get((k, j), 0)) for j in range(jmin, jmax + 1)]
        print(f'{label} delta^{k}:', '  '.join(f'w^{j}:{mp.nstr(v, 10)}' for j, v in row if abs(v) > 1e-25))
_pv.verify_frozen('M2_flow_coefficients.json')        # upstream must be the frozen M2 record
r2 = _js.load(open(_os.path.join(_pv.RES, 'M2_flow_coefficients.json')))['raw_laurent']
J2_meas = S({(int(k), int(j)): mp.mpf(v) for k, d in r2.items() for j, v in d.items() if int(j) <= JMAX})
# use the exact BA delta^0 part, measured delta^1..3 parts
J2_use = S({key: v for key, v in J2_known.c.items()})
J2_use = J2_use + S({key: v for key, v in J2_meas.c.items() if key[0] >= 1})
G0, F1c, F2base = pipeline3(J2_use, J3_known)
show(F1c, 'F1 (check)', jmin=-3, jmax=2)
show(F2base, 'F2 with J3 = J3^(0) only', jmin=-8, jmax=2)
resp = {}
for k in range(1, KD + 1):
    for j in range(-14, 6):
        _, _, F2b = pipeline3(J2_use, J3_known + S({(k, j): mp.mpf(1)}))
        dF = F2b - F2base
        resp[(k, j)] = {key: v for key, v in dF.c.items() if abs(v) > mp.mpf(10)**(-25)}
_prov = _pv.step0_provenance(__file__, [_os.path.join(_pv.RES, 'M2_flow_coefficients.json')],
                             dict(KD=KD, JMIN=JMIN, JMAX=JMAX, NPTS=NPTS, RAD=str(RAD), dps=mp.mp.dps))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm3_step0_response.json'), json.dumps({'provenance': _prov, 'data':
    {f'{k},{j}': {f'{a},{b}': str(v) for (a, b), v in d.items()} for (k, j), d in resp.items()}}, indent=0))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm3_step0_F2base.json'), json.dumps({'provenance': _prov, 'data':
    {f'{a},{b}': str(v) for (a, b), v in F2base.c.items()}}, indent=0))
print('saved M3 responses')
