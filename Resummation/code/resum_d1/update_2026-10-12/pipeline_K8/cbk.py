#!/usr/bin/env python3
"""Core module of the K-generalized 1d pipeline (update 2026-10-12, evening).

Generalizes reproduction/lri_curve/calculate.py (= baseline/calculate.py) and the Pade-Borel helpers of
reproduction/instanton_ablation/ablation.py to the short-range (strong-endpoint) series imposed through C^SR_K:

  t = sqrt(x), q = 4x = 1 - eps, v = 1 - 2 sqrt(x),
  S_K = sum_{n=0}^{K} C^SR_n t^n,   F = S_K + q^{(K+1)/2} R[H],   H = (F - S_K) q^{-(K+1)/2},

with H expanded in eps from the GFF coefficients C_0..C_N ('endpoint_epsilon', action A_eps) or re-expanded in
v via eps = 2v - v^2 ('endpoint_v', action A_v = A_eps/2). 'direct' is the GFF series alone and does not depend
on K. K = 4 is the archived construction (S_4 = archived EP_A, EP_B terms); the K-dependence enters only through
S_K and the power (K+1)/2. Same as update_2026-10-12/sr_endpoint.py for the endpoint_v CB and PB pieces.

Helper functions conv, qpower, compose, polynomial, formal_check, laguerre, integral_grid, adaptive_integral,
mp_integral are copied unchanged in substance from calculate.py; denominator_degrees, rational_series, make_pb,
pb_adaptive are copied from ablation.py. No HT, NRG or MC value enters anything here.

2026-10-13 (C8(1) final): C8 and its allowance come from update_2026-10-13/C8_1_ext/c8_1_switch.py. LRI_C8_1=final
(default): C8(1) = 8059766.723129955, allowance 17000. LRI_C8_1=previous: the evidence.json value 8066723.342964563,
allowance 33000 (reproduces the 2026-10-12/13 tables). C_PREVIOUS keeps the previous coefficients for code regressions
against the archived tables. All stages write below SW.out_root()/pipeline_K8/ (RES, PLOT_DATA; Figure 05 input FIG05),
never into this directory. Previous version: history/C8_1_before_ext_20261013/update_2026-10-12/pipeline_K8/.
"""
import json
import math
import sys
import warnings
from functools import lru_cache
from pathlib import Path
import mpmath as mp
import numpy as np
from scipy.linalg import eigh_tridiagonal
from scipy.integrate import quad, IntegrationWarning

mp.mp.dps = 65
HERE = Path(__file__).resolve().parent
PKG = HERE.parent.parent
sys.path.insert(0, str(PKG/'update_2026-10-13'/'C8_1_ext'))
import c8_1_switch as SW
EV = json.loads((HERE/'inputs/evidence.json').read_text())
MODE = SW.MODE
C8IN = SW.c8_inputs()


def coefficients(c8):
    return [mp.mpf('.5'), -mp.mpf(1)/6, mp.mpf('0.6571312639810638'),
            mp.mpf('-3.719856322901833422489885712662776926'),
            mp.mpf('45.42488010356'), mp.mpf('-731.13947662454'),
            mp.mpf(EV['C6_headline']['C6_unrounded']), mp.mpf(str(EV['C7']['C7_full'])),
            mp.mpf(c8)]


C = coefficients(C8IN['C8'])
C_PREVIOUS = coefficients(SW.c8_inputs('previous')['C8'])
assert C_PREVIOUS[8] == mp.mpf(str(EV['C8']['C8_full']))
ALLOWANCE_C8_PREVIOUS = SW.c8_inputs('previous')['allowance']
ROOT = SW.out_root()/'pipeline_K8'                     # outputs of this pipeline for the active C8
RES = ROOT/'results'
PLOT_DATA = ROOT/'plot_data_1d_K8.json'
FIG05 = SW.out_root()/'fig05_K8_inputs.json'
MISMATCH = SW.out_root()/'instanton_mismatch'
ACTION = 9*mp.pi**2/mp.gamma(mp.mpf(1)/4)**4
z2, z3, z4, z5, z6 = (mp.zeta(k) for k in (2, 3, 4, 5, 6))
CSR = {0: mp.mpf(1), 1: mp.mpf(-2), 2: mp.mpf(1)/2,
       3: mp.mpf(39)/16 + 2*z2,
       4: 4 - 4*z2 - 8*z3,
       5: mp.mpf(11249)/1024 - mp.mpf(361)/16*z2 + 24*z3 + mp.mpf(49)/2*z4,
       6: 26 - 38*z2 + 104*z3 - 80*z4 - 272*z5 + 112*z2*z3,
       7: (mp.mpf(1798583)/32768 - mp.mpf(90637)/1024*z2 + mp.mpf(453)/4*z3 - mp.mpf(16835)/64*z4
           + 1224*z5 - 540*z2*z3 + mp.mpf(4335)/8*z6 - 320*z3**2),
       8: mp.mpf('247.3812048049935484073550747661')}
KS = (4, 5, 6, 7, 8)
MODES = ('direct', 'endpoint_epsilon', 'endpoint_v')
ALLOWANCES = [(6, mp.mpf('4.9e-7')), (7, mp.mpf(41)), (8, mp.mpf(C8IN['allowance']))]
XKEY = [0, .001, .01, .025, .05, .0625, .075, .0875, .1, .1125,
        .125, .1375, .15, .1625, .1727335, .175, .1875, .2, .225, .24, .249, .25]
X = np.unique(np.r_[np.linspace(0, .25, 1001), XKEY])                       # 1004 points (curve grid)
XKEY_ABL = [0, .001, .01, .025, .05, .0625, .075, .1, .125, .15, .175, .2, .225, .24, .249, .25]
X_ABL = np.unique(np.round(np.r_[np.linspace(0, .25, 501), XKEY_ABL, .0875, .1125, .1375, .1727335], 12))


def conv(a, b, n):
    return [sum(a[j]*b[k-j] for j in range(k+1) if j < len(a) and k-j < len(b)) for k in range(n+1)]


def qpower(p, n):                       # coefficients of (1-eps)^p
    return [(-1)**k*mp.binomial(p, k) for k in range(n+1)]


def compose(a, z, n):
    out = [mp.mpf(0)]*(n+1); power = [mp.mpf(1)]+[mp.mpf(0)]*n
    for a_k in a:
        out = [u+a_k*v for u, v in zip(out, power)]
        power = conv(power, z, n)
    return out


def csr(K):
    return [CSR[n] for n in range(K+1)]


def base(x, K):
    """S_K(x) = sum_{n<=K} C^SR_n x^{n/2} in double precision."""
    t = np.sqrt(np.asarray(x, dtype=float))
    return sum(float(a)*t**n for n, a in enumerate(csr(K)))


def power(K):
    return (K+1)/2


def ssk(K, order):
    """eps-expansion of S_K: S_K = sum_n C^SR_n 2^{-n} q^{n/2}, q = 1 - eps."""
    return [sum(a/mp.mpf(2)**n*qpower(mp.mpf(n)/2, order)[k] for n, a in enumerate(csr(K))) for k in range(order+1)]


def series(mode, order, c=None, K=4):
    c = (C if c is None else c)[:order+1]
    if mode == 'direct':
        return list(c)
    s = ssk(K, order); p = mp.mpf(K+1)/2
    h = conv([u-v for u, v in zip(c, s)], qpower(-p, order), order)
    check = [u+v for u, v in zip(s, conv(h, qpower(p, order), order))]
    assert max(abs(u-v)/(1+abs(v)) for u, v in zip(check, c)) < mp.mpf('1e-55')
    return compose(h, [0, 2, -1], order) if mode == 'endpoint_v' else h


def original_coefficient(cmode, mode, n, K=4):
    """Map a mode series (direct / H in eps / H in v) back to the GFF coefficient C_n."""
    if mode == 'direct':
        return cmode[n]
    if mode == 'endpoint_v':             # v(eps) = 1 - sqrt(1-eps)
        v = [mp.mpf(0)]+[-(-1)**k*mp.binomial(mp.mpf('.5'), k) for k in range(1, n+1)]
        cmode = compose(cmode, v, n)
    return ssk(K, n)[n]+conv(cmode, qpower(mp.mpf(K+1)/2, n), n)[n]


def pref(mode):
    return ACTION/2 if mode == 'endpoint_v' else ACTION


def argument(mode, x):
    x = np.asarray(x, dtype=float)
    return 1-2*np.sqrt(x) if mode == 'endpoint_v' else 1-4*x


def polynomial(c, b, alpha, A):
    """[w^k] (1-w)^alpha B_b(4 A w/(1-w)^2)."""
    n = len(c)-1; b = mp.mpf(b); alpha = mp.mpf(alpha)
    return [sum(c[j]/mp.gamma(j+b+1)*(4*A)**j*(-1)**(k-j)*mp.binomial(alpha-2*j, k-j) for j in range(k+1))
            for k in range(n+1)]


def wseries(A, n):
    """w(t) = sum (-1)^(k-1) Catalan_k (t/4A)^k (independent inverse map)."""
    return [mp.mpf(0)]+[(-1)**(k-1)*mp.binomial(2*k, k)/(k+1)/(4*A)**k for k in range(1, n+1)]


def formal_check(c, b, alpha, A, p):
    n = len(c)-1
    bp = conv(p, qpower(-mp.mpf(alpha), n), n)
    bt = compose(bp, wseries(A, n), n)
    return float(max(abs(bt[k]*mp.gamma(k+b+1)-c[k])/(1+abs(c[k])) for k in range(n+1)))


@lru_cache(None)
def laguerre(n, b):
    k = np.arange(n, dtype=float); j = np.arange(1, n, dtype=float)
    t, v = eigh_tridiagonal(2*k+b+1, np.sqrt(j*(j+b)))
    wt = math.gamma(b+1)*v[0, :]**2
    assert np.isfinite(t).all() and np.isfinite(wt).all()
    assert abs(wt.sum()/math.gamma(b+1)-1) < 2e-13
    return t, wt


def integral_grid(p, b, alpha, A, arguments, nquad=240):
    t, wt = laguerre(nquad, b)
    z = np.asarray(arguments)[:, None]*t[None, :]/float(A)
    root = np.sqrt(1+z)
    w = z/(root+1)**2
    values = np.polynomial.polynomial.polyval(w, np.asarray(p, dtype=float))/(1-w)**alpha
    return values.dot(wt)


def dimension(mode, order, b=3, alpha=0, afactor=1, x=X, c=None, nquad=240, K=4):
    """CB approximant. afactor scales a=1/A, not A itself."""
    A = pref(mode)/mp.mpf(str(afactor)); cs = series(mode, order, c, K)
    p = polynomial(cs, b, alpha, A)
    x = np.asarray(x, dtype=float)
    y = integral_grid(p, b, alpha, A, argument(mode, x), nquad)
    return y if mode == 'direct' else base(x, K)+(4*x)**power(K)*y


def adaptive_integral(p, b, alpha, A, arg):
    def f(t):
        if t == 0:
            return float(p[0]) if b == 0 else 0.
        logw = -t+b*math.log(t)
        if logw < -740:
            return 0.
        z = arg*t/float(A); w = z/(math.sqrt(1+z)+1)**2
        return math.exp(logw)*np.polynomial.polynomial.polyval(w, [float(v) for v in p])/(1-w)**alpha
    return quad(f, 0, np.inf, epsabs=2e-12, epsrel=2e-12, limit=400)


def mp_integral(p, b, alpha, A, arg):
    arg = mp.mpf(str(arg))
    def f(t):
        z = arg*t/A; w = z/(mp.sqrt(1+z)+1)**2
        return mp.exp(-t)*t**b*mp.polyval(p[::-1], w)/(1-w)**alpha
    return mp.quad(f, [0, 1, 4, 12, 40, mp.inf])


# ---------------- Pade-Borel (no action) ----------------
def denominator_degrees(n):
    c = n//2
    ms = list(range(max(1, c-1), min(n, c+1+(n % 2))+1))
    return sorted(ms, key=lambda m: (abs(n-2*m), m))


def rational_series(p, q, n):
    r = []
    for k in range(n+1):
        r.append(((p[k] if k < len(p) else 0)-sum(q[j]*r[k-j] for j in range(1, min(k, len(q)-1)+1)))/q[0])
    return r


def make_pb(c, m, b):
    bc = [v/mp.gamma(k+b+1) for k, v in enumerate(c)]
    p, q = mp.pade(bc, len(c)-1-m, m)
    roots = np.roots([float(v) for v in q[::-1]])
    allowed = not any(z.real > 0 and abs(z.imag) < 1e-8*max(1, abs(z)) for z in roots)
    test = rational_series(p, q, len(c)-1)
    rel = max(abs(u-v)/(1+abs(v)) for u, v in zip(test, bc))
    assert rel < mp.mpf('1e-50')
    return {'p': p, 'q': q, 'roots': roots, 'allowed': allowed, 'formal': float(rel), 'b': b, 'm': m, 'n': len(c)-1}


def pb_adaptive(ap, arg):
    p = [float(v) for v in ap['p']]; q = [float(v) for v in ap['q']]; b = ap['b']
    def f(t):
        if t == 0:
            return p[0]/q[0] if b == 0 else 0.
        weight = -t+b*math.log(t)
        if weight < -740:
            return 0.
        return math.exp(weight)*np.polynomial.polynomial.polyval(arg*t, p)/np.polynomial.polynomial.polyval(arg*t, q)
    with warnings.catch_warnings():
        warnings.simplefilter('error', IntegrationWarning)
        return quad(f, 0, np.inf, epsabs=2e-11, epsrel=2e-11, limit=400)


def pb_remainder_grid(ap, args, check_points):
    """GL-240 remainder with adaptive checks at check_points (indices); adaptive fallback if they disagree."""
    t, wt = laguerre(240, ap['b']); z = np.asarray(args)[:, None]*t[None, :]
    p = np.array([float(v) for v in ap['p']]); q = np.array([float(v) for v in ap['q']])
    vals = (np.polynomial.polynomial.polyval(z, p)/np.polynomial.polynomial.polyval(z, q)).dot(wt)
    errs = []
    for i in check_points:
        ad, er = pb_adaptive(ap, args[i]); errs.append(abs(vals[i]-ad))
    fallback = bool(max(errs) > 2e-9)
    if fallback:
        vals = np.array([pb_adaptive(ap, a)[0] for a in args])
    return vals, float(max(errs)), fallback


def pb_dimension(ap, mode, x, K=4):
    x = np.asarray(x, dtype=float); args = argument(mode, x)
    checks = [int(np.argmin(abs(x-xx))) for xx in (0, .025, .1, .2, .249) if np.min(abs(x-xx)) < 1e-12]
    if not checks:
        checks = list(range(len(x)))
    vals, err, fb = pb_remainder_grid(ap, args, checks)
    ap['laguerre_adaptive_max_remainder_difference'] = err; ap['adaptive_fallback'] = fb
    return vals if mode == 'direct' else base(x, K)+(4*x)**power(K)*vals


def pb_mp_check(ap, mode, xx, K=4):
    """Independent 65-digit integral of a PB approximant at one x."""
    b = ap['b']
    arg = mp.mpf(1)-2*mp.sqrt(mp.mpf(str(xx))) if mode == 'endpoint_v' else 1-4*mp.mpf(str(xx))
    val = mp.quad(lambda t: mp.exp(-t)*t**b*mp.polyval(ap['p'][::-1], arg*t)/mp.polyval(ap['q'][::-1], arg*t),
                  [0, 1, 4, 12, 40, mp.inf])
    if mode == 'direct':
        return val
    t = mp.sqrt(mp.mpf(str(xx)))
    return sum(a*t**n for n, a in enumerate(csr(K)))+(4*mp.mpf(str(xx)))**(mp.mpf(K+1)/2)*val
