#!/usr/bin/env python3
"""Direct check of the residue-lattice summation identity implied by the one-mode property (c1 = 0) of the S-family periodization:

  Sigma0 := sum_{l>=0} d_l(d) sum_{n>=0} [ Gamma(l+n+mu) Gamma(n+1-kappa) / (Gamma(l+n+2q) Gamma(n+1)) ]^2
          = pi tan(pi mu) Gamma(tau) Gamma(mu)^4 / ( 2 sin^2(pi kappa) Gamma(2q) Gamma(2q-tau) Gamma(kappa)^4 ),
  mu = q - tau/2, kappa = q + tau/2 (converges for tau > 2q - 1 when 2 kappa > 1; always for d <= 2).

Equivalently  P := sum_l d_l sum_n [leading double-pole coefficient of g_l(s)^2 at s = alpha_l + n] = W_S tan(pi mu)/(2 pi).
Spin sum by partial sums + exact fit of the remainder with exponents L^(2q-1-tau-j), L^(-2tau-j).
usage: sigma0_check.py d tau dps Lmax K
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H
from spec_S import mult_fp


def main():
    dps, Lmax, K = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    mp.mp.dps = dps
    d, tau = mp.mpf(sys.argv[1]), mp.mpf(sys.argv[2])
    q = d / 4; mu, kap = q - tau / 2, q + tau / 2
    st = time.time()
    N0 = 60
    Nmax = N0 + 4 * Lmax + 2
    A2 = [(mp.gamma(m + mu) / mp.gamma(m + 2 * q)) ** 2 for m in range(Nmax + Lmax + 2)]
    B2 = [(mp.gamma(n + 1 - kap) / mp.gamma(n + 1)) ** 2 for n in range(Nmax + 2)]
    inner = []
    for l in range(Lmax):
        N = N0 + 4 * l
        s = mp.fsum(A2[l + n] * B2[n] for n in range(N))
        P, E = H.stirling_series([(l + mu, l + 2 * q, 2), (1 - kap, mp.mpf(1), 2)], K)
        s += mp.fsum(E[k] * H.hz(P + k, N) for k in range(K + 1) if E[k] != 0)
        inner.append(s)
    dl = [mult_fp(d, l) for l in range(Lmax)]
    part = [mp.mpf(0)] * (Lmax + 1)
    for l in range(Lmax):
        part[l + 1] = part[l] + dl[l] * inner[l]
    exps = []
    for j in range(14):
        exps += [2 * q - 1 - tau - j, -2 * tau - j]
    exps = sorted(exps, key=lambda e: -e)
    fits = []
    for nterm in (8, 12, 16, 20):
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
    val = fits[-1]
    closed = mp.pi * mp.tan(mp.pi * mu) * mp.gamma(tau) * mp.gamma(mu) ** 4 / (
        2 * mp.sin(mp.pi * kap) ** 2 * mp.gamma(2 * q) * mp.gamma(2 * q - tau) * mp.gamma(kap) ** 4)
    out = dict(d=sys.argv[1], tau=sys.argv[2], dps=dps, Lmax=Lmax, K=K, Sigma0_fit=mp.nstr(val, 30),
               fit_spread=mp.nstr(max(abs(x - val) for x in fits), 3), closed=mp.nstr(closed, 30),
               rel=mp.nstr(abs(val - closed) / abs(closed), 4), seconds=round(time.time() - st, 1))
    print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
