"""Independent recomputation of a0, b0 (and C1) from the retained spectrum:
 - blocks from the KPS Zamolodchikov recursion (kps_blocks.py), not the package's Casimir series
 - BRRZ Method-2 arrangement (arXiv:1703.05325 sec. 3-4), NOT the note's identity-subtracted arrangement:
     I_sig = int_R dmu [ 2 v^{-(3-S)} r^{-2S}(1+S(z)) + r^{-6}(1+S(z)) ],
     I_eps = int_R dmu [ 2 v^{-(3-S)} r^{-S-E} M(z)   + r^{-6}(1+E(z)) ],
   power divergences at r->0 removed by subtracting the angular-averaged identity and eps terms analytically.
 - own quadrature (r = r0 t^q map, r0 and node counts as arguments)
 b0 = -2 pi I_sig, a0 = -2 pi I_eps."""
import sys, json, time, numpy as np
from scipy.special import gammaln
from numpy.polynomial import legendre as L
sys.path.insert(0, '.')
from kps_blocks import KPS

def main(spec_path, NS=30, r0=0.25, nr=120, na=120, q=3, dmax=99.0):
    rows = [p for p in json.load(open(spec_path)) if p['Delta'] < dmax]
    S = next(p['Delta'] for p in rows if p['sector'] == 'odd' and p['ell'] == 0 and p['Delta'] < 1)
    E = next(p['Delta'] for p in rows if p['sector'] == 'even' and p['ell'] == 0 and 1 < p['Delta'] < 2)
    feps = next(p for p in rows if p['sector'] == 'even' and p['Delta'] == E)
    w = lambda l: np.exp(gammaln(l+1)-gammaln(l+.5)+gammaln(.5))
    t, wt = L.leggauss(nr); t = (t+1)/2; wt = wt/2
    x, wx = L.leggauss(na)
    grids = []
    # piece 0: small ball r<r0 (r0<1/2), full sphere; r = r0 * t^q
    r = r0*t**q; dr = r0*q*t**(q-1)*wt
    grids.append(('ball', r, dr, -np.ones_like(r), np.ones_like(r)))
    r = r0+(0.5-r0)*t; grids.append(('mid', r, (0.5-r0)*wt, -np.ones_like(r), np.ones_like(r)))
    r = 0.5+0.5*t; grids.append(('out', r, 0.5*wt, -np.ones_like(r), 1/(2*r)))
    pts = []
    for name, r, dr, lo, hi in grids:
        eta = lo[:, None]+(hi-lo)[:, None]*(x[None, :]+1)/2
        deta = (hi-lo)[:, None]*wx[None, :]/2
        z = r[:, None]*(eta+1j*np.sqrt(1-eta**2))
        pts.append((name, r[:, None]*np.ones_like(eta), eta, z, 2*np.pi*r[:, None]**2*dr[:, None]*deta))
    Ssum = [np.zeros(p[3].shape) for p in pts]; Esum = [np.zeros(p[3].shape) for p in pts]; Msum = [np.zeros(p[3].shape) for p in pts]
    Keven = KPS(0.0, 0.0, NS); Kodd = KPS(E-S, S-E, NS)
    # ball (r<r0) contribution of r^{-6}(1+X) with X=S or E: per block, angular average fitted by even polynomial,
    # then analytically continued term by term: 2pi * sum_k phi_k r0^{D-3+2k}/(D-3+2k)
    rc = 0.5*(r0+0.02)+0.5*(r0-0.02)*np.cos(np.pi*(np.arange(60)+0.5)/60)
    ec = np.cos(np.pi*(np.arange(60)+0.5)/60)  # unused
    xb, wb = L.leggauss(160)
    zc = rc[:, None]*(xb[None, :]+1j*np.sqrt(1-xb[None, :]**2))
    KF = 16
    def ball_ac(g, D, l):
        A = np.sum(wb[None, :]*g(zc), axis=1)          # int_{-1}^{1} g d eta
        phi = A/rc**D
        Vm = np.vstack([rc**(2*k) for k in range(KF)]).T
        coef, res, rk, sv = np.linalg.lstsq(Vm, phi, rcond=None)
        fiterr = np.max(abs(Vm@coef-phi))
        val = 0.0
        for k in range(KF):
            p_ = D-3+2*k
            if abs(p_) < 1e-9:
                resonant.append((D, l, k, float(coef[k])))   # must be ~0 (no log); skipped
                continue
            val += 2*np.pi*coef[k]*r0**p_/p_
        return val, fiterr
    ballS = 4*np.pi*r0**(-3)/(-3); ballE = ballS; maxfit = 0.0; resonant = []
    t0 = time.time()
    for p in sorted(rows, key=lambda p: p['ell']):
        l = p['ell']
        if p['sector'] == 'even':
            g = Keven.block_code_norm(p['Delta'], l)
            for i, P in enumerate(pts):
                gv = w(l)*g(P[3]); Ssum[i] += p['f']**2*gv; Esum[i] += p['f']*p['h']*gv
            bv, fe = ball_ac(g, p['Delta'], l); maxfit = max(maxfit, fe*w(l)*p['f']*max(p['f'], abs(p['h'])))
            ballS += w(l)*p['f']**2*bv; ballE += w(l)*p['f']*p['h']*bv
        else:
            g = Kodd.block_code_norm(p['Delta'], l)
            for i, P in enumerate(pts):
                Msum[i] += w(l)*p['f']**2*g(P[3])
    tb = time.time()-t0
    Is = 0.0; Ie = 0.0
    for i, (name, r, eta, z, dmu) in enumerate(pts):
        v = abs(1-z)**2
        Is += np.sum(dmu*2*v**(-(3-S))*r**(-2*S)*(1+Ssum[i]))
        Ie += np.sum(dmu*2*v**(-(3-S))*r**(-S-E)*Msum[i])
        if name == 'ball':
            Is += ballS; Ie += ballE
        else:
            Is += np.sum(dmu*r**(-6)*(1+Ssum[i]))
            Ie += np.sum(dmu*r**(-6)*(1+Esum[i]))
    b0 = -2*np.pi*Is; a0 = -2*np.pi*Ie
    out = dict(NS=NS, r0=r0, nr=nr, na=na, q=q, dmax=dmax, n_ops=len(rows), b0=b0, a0=a0, C1=a0/b0, block_time=tb, max_ball_fit_err=maxfit, resonant_coefs=resonant)
    print(json.dumps(out), flush=True)
    return out

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--NS', type=int, default=30); ap.add_argument('--r0', type=float, default=0.25)
    ap.add_argument('--nr', type=int, default=120); ap.add_argument('--na', type=int, default=120); ap.add_argument('--q', type=int, default=3)
    ap.add_argument('--dmax', type=float, default=99.0)
    a = ap.parse_args()
    main(a.spec, a.NS, a.r0, a.nr, a.na, a.q, a.dmax)
