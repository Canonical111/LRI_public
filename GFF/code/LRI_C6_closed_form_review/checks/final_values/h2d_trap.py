# Step 3: genuine 2D Mellin-Barnes integrals by tensor-product trapezoid rules (double precision).
# ds dt/(2 pi i)^2 ; contours parametrized analytically; results compared over h, range, tilt.
import numpy as np, sys, time, json
from h2d_common import *

def trap2(logK_fn, s, ds, t, dt, block=400):
    """-(1/4pi^2) sum_ij exp(logK(s_i,t_j)) ds_i dt_j  (ds, dt already include the step h)."""
    tot = 0j
    for i0 in range(0, len(s), block):
        si = s[i0:i0 + block][:, None]
        L = logK_fn(si, t[None, :])
        tot += np.sum(np.exp(L)*ds[i0:i0 + block][:, None]*dt[None, :])
    return -tot/(4*PI**2)

def contour(sig, tau, h, X):
    xi = np.arange(-X, X + h/2, h)
    s = sig - tau*(np.cosh(xi) - 1) + 1j*np.sinh(xi)
    ds = (-tau*np.sinh(xi) + 1j*np.cosh(xi))*h
    return xi, s, ds

def line(sig, h, U):
    u = np.arange(-U, U + h/2, h)
    return u, sig + 1j*u, 1j*np.ones_like(u)*h

res = {}
which = sys.argv[1] if len(sys.argv) > 1 else 'all'

if which in ('all', 'HW'):
    # H_W: s on Re s=1/4 (sinh map, no tilt), t on Re t=1/8 (uniform), kernel N_aW(s)P(t)/(1/2-s-t)^2
    lN = lambda s: logN_alpha(s, alphaW)
    for (hx, hw, X, Wm) in [(0.02, 0.03, 11, 9), (0.01, 0.02, 11, 9), (0.007, 0.015, 12, 10), (0.005, 0.012, 13, 10)]:
        t0 = time.time()
        _, s, ds = contour(0.25, 0.0, hx, X)
        _, t, dt = line(0.125, hw, Wm)
        LN = lN(s); LP = logP_t(t)
        f = lambda si, tj: LN[np.searchsorted(s.imag, si.imag.ravel())].reshape(si.shape) if False else None
        # direct block evaluation
        tot = 0j
        for i0 in range(0, len(s), 300):
            si = s[i0:i0 + 300][:, None]
            L = LN[i0:i0 + 300][:, None] + LP[None, :] - 2*np.log(0.5 - si - t[None, :])
            tot += np.sum(np.exp(L)*ds[i0:i0 + 300][:, None]*dt[None, :])
        v = -tot/(4*PI**2)
        print(f"H_W trap hx={hx} hw={hw} X={X} W={Wm}: {v.real:.15f}  (Im {v.imag:.1e})  [{len(s)}x{len(t)}, {time.time()-t0:.1f}s]", flush=True)
        res.setdefault('HW', []).append([hx, hw, X, Wm, v.real, v.imag])

if which in ('all', 'H7'):
    # H7: s on Re s=1/4 (uniform), t on Re t=1/16 (sinh map); kernel A7(s) cot(2 pi t)/((1/2-t)(1/2-s-t))
    for (hu, hz, U, Z) in [(0.05, 0.015, 15, 28), (0.035, 0.011, 15, 30), (0.025, 0.008, 16, 33)]:
        t0 = time.time()
        _, s, ds = line(0.25, hu, U)
        _, t, dt = contour(1/16, 0.0, hz, Z)
        LA = logA7(s, beta7)
        ct = cot2pi(t)/(0.5 - t)
        tot = 0j
        for i0 in range(0, len(s), 100):
            si = s[i0:i0 + 100][:, None]
            M = np.exp(LA[i0:i0 + 100])[:, None]*(ct[None, :]/(0.5 - si - t[None, :]))
            tot += np.sum(M*ds[i0:i0 + 100][:, None]*dt[None, :])
        v = -tot/(4*PI**2)
        print(f"H7 trap hu={hu} hz={hz} U={U} Z={Z}: {v.real:.15f}  (Im {v.imag:.1e})  [{len(s)}x{len(t)}, {time.time()-t0:.1f}s]", flush=True)
        res.setdefault('H7', []).append([hu, hz, U, Z, v.real, v.imag])

if which in ('all', 'HP'):
    # H_star: both contours tilted: s(xi) = 1/4 - tau(cosh xi - 1) + i sinh xi; kernel Psi+(s)Psi-(t)/Gamma(1-s-t)
    cfgs = [(0.3, 0.08, 40), (0.3, 0.05, 40), (0.3, 0.035, 40), (0.15, 0.035, 40), (0.5, 0.035, 40), (0.3, 0.025, 44)]
    if len(sys.argv) > 2: cfgs = [tuple(float(x) for x in c.split(':')) for c in sys.argv[2:]]
    for (tau, h, X) in cfgs:
        t0 = time.time()
        xi, s, ds = contour(0.25, tau, h, X)
        LPp = logPsi(s, betap); LPm = logPsi(s, betam)   # t-contour = same parametrization
        # partial sums by truncation radius (box |xi|,|zeta| <= R) to monitor the algebraic edge tails
        Rs = [16, 20, 24, 28, 30, 32, 34]
        part = {R: 0j for R in Rs if R <= X}
        for i0 in range(0, len(s), 200):
            si = s[i0:i0 + 200][:, None]
            L = LPp[i0:i0 + 200][:, None] + LPm[None, :] - lg(1 - si - s[None, :])
            M = np.exp(L)*ds[i0:i0 + 200][:, None]*ds[None, :]
            xa = np.abs(xi[i0:i0 + 200])[:, None]; xb = np.abs(xi)[None, :]
            mx = np.maximum(xa, xb)
            for R in part:
                part[R] += np.sum(M[mx <= R + 1e-9])
        vals = {R: -v/(4*PI**2) for R, v in part.items()}
        line_ = "  ".join(f"R{R}:{vals[R].real:.12f}" for R in sorted(vals))
        v = vals[max(vals)]
        print(f"H* trap tau={tau} h={h} X={X}: {v.real:.13f} (Im {v.imag:.1e}) [{len(s)}^2, {time.time()-t0:.1f}s]\n    {line_}", flush=True)
        res.setdefault('HP', []).append([tau, h, X, {str(R): [vals[R].real, vals[R].imag] for R in vals}])
json.dump(res, open(f'h2d_trap_{which}.json', 'w'), indent=1)
