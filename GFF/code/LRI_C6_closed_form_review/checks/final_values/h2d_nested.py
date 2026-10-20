# Step 3, second method: iterated adaptive quadrature (scipy QUADPACK) on the stated straight contours.
import numpy as np, time, json
from scipy.integrate import quad
from h2d_common import *
from scipy.special import loggamma as lgs
PI = np.pi
res = {}
EPS = dict(epsabs=1e-13, epsrel=1e-12, limit=400)

# ---------- H_W : s = 1/4+iu, t = 1/8+iw ; measure du dw/(4pi^2); K(-u,-w)=conj K(u,w)
def KW(u, w):
    s = 0.25 + 1j*u; t = 0.125 + 1j*w
    return np.exp(logN_alpha(np.array([s]), alphaW)[0] + logP_t(np.array([t]))[0]) / (0.5 - s - t)**2
def inner_W(u):
    pts = [-u] if abs(u) < 11 else None
    v, e = quad(lambda w: KW(u, w).real, -12, 12, points=pts, **EPS)
    return v
t0 = time.time()
a, ea = quad(inner_W, 0, 30, **EPS)
b, eb = quad(inner_W, 30, np.inf, **EPS)
HW = 2*(a + b)/(4*PI**2)
print(f"H_W nested quad = {HW:.14f}  (quad err est {2*(ea+eb)/(4*PI**2):.1e}; tail u>30 part {2*b/(4*PI**2):.2e}) {time.time()-t0:.1f}s", flush=True)
res['HW'] = HW

# ---------- H7 : s = 1/4+iu, t = 1/16+iw
def K7(u, w):
    s = 0.25 + 1j*u; t = 1/16 + 1j*w
    return np.exp(logA7(np.array([s]), beta7)[0]) * cot2pi(t) / ((0.5 - t)*(0.5 - s - t))
def inner_7(u):
    L = 40 + abs(u)
    f = lambda w: K7(u, w).real
    v1, _ = quad(f, -L, L, points=sorted({0.0, -u}), **EPS)
    v2, _ = quad(f, L, np.inf, **EPS)
    v3, _ = quad(f, -np.inf, -L, **EPS)
    return v1 + v2 + v3
t0 = time.time()
a, ea = quad(inner_7, 0, 16, **EPS)
H7 = 2*a/(4*PI**2)
print(f"H7 nested quad  = {H7:.14f}  (outer err est {2*ea/(4*PI**2):.1e}) {time.time()-t0:.1f}s", flush=True)
res['H7'] = H7
json.dump(res, open('h2d_nested.json', 'w'), indent=1)
