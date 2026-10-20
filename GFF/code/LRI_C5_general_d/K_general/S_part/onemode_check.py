#!/usr/bin/env python3
"""Global one-mode test of the S-family periodization at generic d, at arbitrary real sample points z.

In lattice variables (m, n') = (l+n, -n) and z = alpha0 + t the spin-summed periodization is
   S(z) = sum_{L>=0} d_L c_L(z),   c_L(z) = sum_{m in Z} Phi(m+z) Phi(L-m-z),   Phi(x) = [Gamma(x+alpha0)/Gamma(x+beta0)]^2,
and Xi = sin^2(pi(z-alpha0)) sin^2(pi(z+alpha0)) S(z) = c0 + c1 cos(2 pi z)  (two-mode theorem).  Claim: c1 = 0, i.e. Xi(z) = c0 for all z,
with c0 = pi sin^3(2 pi alpha0) W / (2 cos(2 pi alpha0)),  W = Gamma(tau)Gamma(mu)^4/(Gamma(2q)Gamma(2q-tau)Gamma(kappa)^4).
usage: onemode_check.py d tau dps Lmax K z1 z2 ...
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H
from spec_S import mult_fp, S_closed


def run(d, tau, z, Lmax, K, dps):
    q = d / 4; a0, b0 = q / 2 - tau / 4, 3 * q / 2 + tau / 4; mu, kap = 2 * a0, b0 - a0
    Phi = lambda x: (mp.gamma(x + a0) / mp.gamma(x + b0)) ** 2
    rp = (mp.sin(mp.pi * (b0 + z)) / mp.sin(mp.pi * (a0 + z))) ** 2
    rm = (mp.sin(mp.pi * (b0 - z)) / mp.sin(mp.pi * (a0 - z))) ** 2

    def stail(factors, pref, N):
        P, E = H.stirling_series(factors, K)
        return pref * mp.fsum(E[k] * H.hz(P + k, N) for k in range(K + 1) if E[k] != 0)

    cache = {}
    def ph(x):
        k = mp.nstr(x, dps + 5)
        if k not in cache:
            cache[k] = Phi(x)
        return cache[k]

    cL = []
    for L in range(Lmax):
        M = 60 + 4 * L
        s = mp.fsum(ph(m + z) * ph(L - m - z) for m in range(-M + 1, L + M))
        # m >= L+M:  Phi(m+z) * rp^2-type reflection of Phi(L-m-z), variable m
        # reflection Phi(-x) = [sin pi(b0-x)/sin pi(a0-x)]^2 [Gamma(x+1-b0)/Gamma(x+1-a0)]^2, x = m+z-L  ->  trig factor rm
        s += stail([(z + a0, z + b0, 2), (z - L + 1 - b0, z - L + 1 - a0, 2)], rm, L + M)
        # m <= -M (m = -j, j >= M): reflection of Phi(-j+z) times Phi(L+j-z), variable j
        # x = j - z  ->  trig factor rp
        s += stail([(1 - z - b0, 1 - z - a0, 2), (L - z + a0, L - z + b0, 2)], rp, M)
        cL.append(s)
    dl = [mult_fp(d, L) for L in range(Lmax)]
    part = [mp.mpf(0)] * (Lmax + 1)
    for L in range(Lmax):
        part[L + 1] = part[L] + dl[L] * cL[L]
    exps = []
    for j in range(14):
        exps += [2 * q - 1 - tau - j, -2 * tau - j]
    exps = sorted(exps, key=lambda e: -e)
    fits = []
    for nterm in ((12, 16, 20) if d != 1 else ()):
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
    if d == 1:                      # d_L = (1, 1, 0, 0, ...): finite spin sum, no extrapolation
        Sz, fits = part[2], [part[2]]
    else:
        Sz = fits[-1]
    Xi = mp.sin(mp.pi * (z - a0)) ** 2 * mp.sin(mp.pi * (z + a0)) ** 2 * Sz
    W = S_closed(d, tau) / mp.gamma(2 * q) ** 2
    c0 = mp.pi * mp.sin(2 * mp.pi * a0) ** 3 * W / (2 * mp.cos(2 * mp.pi * a0))
    return Sz, Xi, c0, max(abs(f - Sz) for f in fits)


if __name__ == '__main__':
    dps, Lmax, K = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    mp.mp.dps = dps
    d, tau = mp.mpf(sys.argv[1]), mp.mpf(sys.argv[2])
    out = dict(d=sys.argv[1], tau=sys.argv[2], dps=dps, Lmax=Lmax, K=K, points={})
    st = time.time()
    for zs in sys.argv[6:]:
        z = mp.mpf(zs)
        Sz, Xi, c0, spread = run(d, tau, z, Lmax, K, dps)
        out['points'][zs] = dict(S=mp.nstr(Sz, 25), Xi=mp.nstr(Xi, 25), c0_closed=mp.nstr(c0, 25), rel=mp.nstr(abs(Xi - c0) / abs(c0), 4),
                                 fit_spread=mp.nstr(spread, 3))
    out['seconds'] = round(time.time() - st, 1)
    print(json.dumps(out), flush=True)
