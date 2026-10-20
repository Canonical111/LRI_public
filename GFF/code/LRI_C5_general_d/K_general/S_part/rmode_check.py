#!/usr/bin/env python3
"""Spin-summed Fourier modes of the generic-d wheel periodization for a general power r (side check of route S_part).

Phi_r(x) = [Gamma(x+alpha0)/Gamma(x+beta0)]^r,  alpha0 = q/2 - tau/4, beta0 = 3q/2 + tau/4,
S_r(z) = sum_{L>=0} d_L sum_{m in Z} Phi_r(m+z) Phi_r(L-m-z),
Xi_r(z) = [sin(pi(z-alpha0)) sin(pi(z+alpha0))]^r S_r(z) = sum_{k=0}^{r-1} c_k cos(2 pi k z)   (fp:finiteFourier, z = t + q/2 at tau = 0).
r = 2, tau > 0 is the S family (claim c_1 = 0);  r = 3, 4 at tau = 0 are the 3Q_d, P_4(d) wheels of fp:wheelStart.
Samples at z_j, j = 0..r (one more than unknowns), least squares; prints c_k and the residual.  Also evaluates the residue
functional  -Res_{z=alpha0} S_r  = sum_l d_l int ds/(2 pi i) g_l^r  and compares with W_r = <t^r>_d / Gamma(2q)^r if given.
usage: rmode_check.py d tau r dps Lmax K [W_ref]
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H
from spec_S import mult_fp


def S_of_z(d, tau, r, z, Lmax, K, dps):
    q = d / 4; a0, b0 = q / 2 - tau / 4, 3 * q / 2 + tau / 4
    Phi = lambda x: (mp.gamma(x + a0) * mp.rgamma(x + b0)) ** r
    rp = (mp.sin(mp.pi * (b0 + z)) / mp.sin(mp.pi * (a0 + z))) ** r
    rm = (mp.sin(mp.pi * (b0 - z)) / mp.sin(mp.pi * (a0 - z))) ** r

    def stail(factors, pref, N):
        P, E = H.stirling_series(factors, K)
        return pref * mp.fsum(E[k] * H.hz(P + k, N) for k in range(K + 1) if E[k] != 0)

    cache = {}
    def ph(x):
        k = mp.nstr(x, dps + 5)
        if k not in cache:
            cache[k] = Phi(x)
        return cache[k]

    part = [mp.mpf(0)]
    for L in range(Lmax):
        M = 60 + 4 * L
        s = mp.fsum(ph(m + z) * ph(L - m - z) for m in range(-M + 1, L + M))
        s += stail([(z + a0, z + b0, r), (z - L + 1 - b0, z - L + 1 - a0, r)], rm, L + M)
        s += stail([(1 - z - b0, 1 - z - a0, r), (L - z + a0, L - z + b0, r)], rp, M)
        part.append(part[-1] + mult_fp(d, L) * s)
    if d == 1:
        return part[2], 0
    kap = b0 - a0
    e1, e2 = 4 * q - 1 - r * kap, 4 * q - 2 * r * kap          # remainder exponents (plus integer shifts)
    exps = sorted([e1 - j for j in range(14)] + [e2 - j for j in range(14)], key=lambda e: -e)
    fits = []
    for nterm in (12, 16, 20):
        Ls = sorted(set(int(mp.nint(Lmax * mp.mpf(1) / 8 * mp.power(8, mp.mpf(i) / nterm))) for i in range(nterm + 1)))
        if len(Ls) != nterm + 1:
            continue
        with mp.workdps(dps + 30):
            A = mp.matrix(nterm + 1, nterm + 1); bvec = mp.matrix(nterm + 1, 1)
            for i, L in enumerate(Ls):
                A[i, 0] = 1
                for j in range(nterm):
                    A[i, j + 1] = mp.mpf(L) ** exps[j]
                bvec[i] = part[L]
            fits.append(mp.lu_solve(A, bvec)[0])
    return fits[-1], max(abs(f - fits[-1]) for f in fits)


if __name__ == '__main__':
    d, tau, r = sys.argv[1], sys.argv[2], int(sys.argv[3])
    dps, Lmax, K = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    mp.mp.dps = dps
    d, tau = mp.mpf(d), mp.mpf(tau); q = d / 4; a0 = q / 2 - tau / 4
    st = time.time()
    zs = [mp.mpf(x) for x in ('0.02', '0.08', '0.25', '0.37', '0.45', '0.29')][:r + 1]
    Xi, spreads = [], []
    for z in zs:
        S, sp = S_of_z(d, tau, r, z, Lmax, K, dps)
        Xi.append((mp.sin(mp.pi * (z - a0)) * mp.sin(mp.pi * (z + a0))) ** r * S); spreads.append(sp)
    A = mp.matrix(r + 1, r); b = mp.matrix(r + 1, 1)
    for i, z in enumerate(zs):
        for k in range(r):
            A[i, k] = mp.cos(2 * mp.pi * k * z)
        b[i] = Xi[i]
    c, res = mp.qr_solve(A, b)
    # residue functional at z = alpha0 (t = 0): -Res S_r, with S_r = Xi_r(z)/[sin(pi(z-a0)) sin(pi(z+a0))]^r
    f = lambda z: sum(c[k] * mp.cos(2 * mp.pi * k * z) for k in range(r)) / (mp.sin(mp.pi * (z - a0)) * mp.sin(mp.pi * (z + a0))) ** r
    rho = min(a0, mp.mpf(1) / 4) / 2
    resid = mp.quad(lambda th: f(a0 + rho * mp.expj(th)) * rho * mp.expj(th), [0, mp.pi, 2 * mp.pi]) / (2 * mp.pi)
    out = dict(d=sys.argv[1], tau=sys.argv[2], r=r, dps=dps, Lmax=Lmax, c=[mp.nstr(x, 20) for x in c], lsq_residual=mp.nstr(res, 3),
               rel_top_mode=mp.nstr(abs(c[r - 1]) / max(abs(x) for x in c), 3), max_fit_spread=mp.nstr(max(spreads), 3),
               W_from_modes=mp.nstr(-resid, 20), seconds=round(time.time() - st, 1))
    if len(sys.argv) > 7:
        W = mp.mpf(sys.argv[7]) / mp.gamma(2 * q) ** r
        out['W_ref'] = mp.nstr(W, 20); out['rel_W'] = mp.nstr(abs(-resid - W) / abs(W), 3)
    print(json.dumps(out), flush=True)
