"""M4 step 0 (generated from m3_step0.py): third order in u (four-bubble cluster J4 -> f_3_n_k).
M3 step 0: second order in u. Original docstring:
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
def J4_BA_fun(w):
    Kc = 1 - w
    a10 = 2*(2*Kc - 1)*mp.gamma(1 - 2*Kc)
    b = lambda n: -(-1)**(n+1)*mp.gamma(mp.mpf(1)/2 + n*(1 - Kc))/(mp.sqrt(mp.pi)*mp.factorial(n)*mp.gamma(1 - n*Kc))
    return a10**4*b(4)/b(1)**4/(2*(1 + 8*(Kc - 1)))
J4_known = series_from({0: laurent(J4_BA_fun)})
def pipeline4(J2, J3, J4):
    a = [None]
    for n, Jn in ((1, J1), (2, J2), (3, J3), (4, J4)):
        a.append(2*((1 + 2*n*(K - 1))*Jn - D*K*Jn.dK()))
    # log M coefficients c_n from M = 1 + sum a_n P^n
    c1 = a[1]; c2 = a[2] - a[1]*a[1]*mp.mpf('0.5')
    c3 = a[3] - a[1]*a[2] + a[1]*a[1]*a[1]*(mp.mpf(1)/3)
    c4 = a[4] - a[1]*a[3] - a[2]*a[2]*mp.mpf('0.5') + a[1]*a[1]*a[2] - a[1]*a[1]*a[1]*a[1]*mp.mpf('0.25')
    cs = [c1, c2, c3, c4]
    pre = (2 - D)*mp.mpf('0.25')
    un = [pre*(2*(n+1)*(K - 1)*cs[n] - D*K*cs[n].dK()) for n in range(4)]
    bn = [2*(n+1)*(K - 1)*un[n] - D*K*un[n].dK() for n in range(4)]
    iu1 = un[0].inv()
    # G = sum_n bn P^n / (2 sum_n un P^n): series in P via ratio r_n
    q = [un[n]*iu1 for n in range(4)]            # q0 = 1
    bt = [bn[n]*iu1 for n in range(4)]
    G = []
    for m in range(4):     # G_m = (bt_m - sum_{j=1..m} q_j G'_{m-j}) with G' = 2G
        acc = bt[m]
        for j in range(1, m + 1):
            acc = acc - q[j]*G[m - j]*2
        G.append(acc*mp.mpf('0.5'))
    tmd = 2 - D
    # X = K exp(tmd log M) - 1 = sum x_n P^n
    L1, L2, L3 = tmd*c1, tmd*c2, tmd*c3
    x1 = K*L1
    x2 = K*(L2 + L1*L1*mp.mpf('0.5'))
    x3 = K*(L3 + L1*L2 + L1*L1*L1*(mp.mpf(1)/6))
    # F(u,X) = F0 + F1 u + F2 u^2 + F3 u^3; match orders in P
    F0 = G[0]; F0p = F0.dK(); F0pp = F0p.dK(); F0ppp = F0pp.dK()
    u1, u2, u3 = un[0], un[1], un[2]
    F1 = (G[1] - F0p*x1)*iu1
    F1p = F1.dK(); F1pp = F1p.dK()
    F2 = (G[2] - F0p*x2 - F0pp*x1*x1*mp.mpf('0.5') - F1*u2 - F1p*x1*u1)*iu1*iu1
    F2p = F2.dK()
    P3 = (F0p*x3 + F0pp*x1*x2 + F0ppp*x1*x1*x1*(mp.mpf(1)/6)
          + F1*u3 + F1p*(x1*u2 + x2*u1) + F1pp*x1*x1*u1*mp.mpf('0.5')
          + F2*u1*u2*2 + F2p*x1*u1*u1)
    F3 = (G[3] - P3)*iu1*iu1*iu1
    return F0, F1, F2, F3
import json as _js
def show(Sr, label, kmax=KD, jmin=-6, jmax=3):
    for k in range(kmax + 1):
        row = [(j, Sr.c.get((k, j), 0)) for j in range(jmin, jmax + 1)]
        print(f'{label} delta^{k}:', '  '.join(f'w^{j}:{mp.nstr(v, 10)}' for j, v in row if abs(v) > 1e-25))
_pv.verify_frozen('M2_flow_coefficients.json'); _pv.verify_frozen('M3_flow_coefficients.json')   # frozen upstream records
r2 = _js.load(open(_os.path.join(_pv.RES, 'M2_flow_coefficients.json')))['raw_laurent']
J2_meas = S({(int(k), int(j)): mp.mpf(v) for k, d in r2.items() for j, v in d.items() if int(j) <= JMAX})
# use the exact BA delta^0 part, measured delta^1..3 parts
J2_use = S({key: v for key, v in J2_known.c.items()})
J2_use = J2_use + S({key: v for key, v in J2_meas.c.items() if key[0] >= 1})
r3 = _js.load(open(_os.path.join(_pv.RES, 'M3_flow_coefficients.json')))['raw_laurent']
J3_use = S({key: v for key, v in J3_known.c.items()})
J3_use = J3_use + S({(int(k), int(j)): mp.mpf(v) for k, d in r3.items() for j, v in d.items() if int(k) >= 1 and int(j) <= JMAX})
F0c, F1c, F2c, F3base = pipeline4(J2_use, J3_use, J4_known)
show(F2c, 'F2 (check vs M3)', kmax=1, jmin=-2, jmax=1)
show(F3base, 'F3 with J4 = J4^(0) only', kmax=1, jmin=-9, jmax=1)
resp = {}
for j in range(-16, 4):
    _, _, _, F3b = pipeline4(J2_use, J3_use, J4_known + S({(1, j): mp.mpf(1)}))
    dF = F3b - F3base
    resp[(1, j)] = {key: v for key, v in dF.c.items() if abs(v) > mp.mpf(10)**(-25) and key[0] <= 1}
_prov = _pv.step0_provenance(__file__, [_os.path.join(_pv.RES, 'M2_flow_coefficients.json'), _os.path.join(_pv.RES, 'M3_flow_coefficients.json')],
                             dict(KD=KD, JMIN=JMIN, JMAX=JMAX, NPTS=NPTS, RAD=str(RAD), dps=mp.mp.dps))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm4_step0_response.json'), json.dumps({'provenance': _prov, 'data':
    {f'{k},{j}': {f'{a},{b}': str(v) for (a, b), v in d.items()} for (k, j), d in resp.items()}}, indent=0))
_pv.atomic_write_text(_os.path.join(_pv.RES, 'm4_step0_F3base.json'), json.dumps({'provenance': _prov, 'data':
    {f'{a},{b}': str(v) for (a, b), v in F3base.c.items() if a <= 1}}, indent=0))
print('saved M4 responses')
for jj in range(-12, 1):
    terms = {src: d[(1, jj)] for src, d in resp.items() if (1, jj) in d}
    lead = sorted(terms)[-1] if terms else None
    print(f'  F3[d^1 w^{jj}]: const {mp.nstr(F3base.c.get((1, jj), 0), 8)}  leading J4 source {lead} coef {mp.nstr(terms[lead], 6) if lead else "-"}')
