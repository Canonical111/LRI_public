#!/usr/bin/env python3
"""Spin-summed Fourier coefficients of the generic-d periodization of the S family.

Xi(t) = sin^2(pi t) sin^2(pi(t+2 alpha0)) sum_l d_l sum_{n in Z} g_l(alpha_l+n+t)^2 = c0 + c1 cos(2 pi (t + alpha0)),
c0 + c1 = sin^4(pi alpha0) F_+,   c0 - c1 = cos^4(pi alpha0) F_-,   F_pm = sum_l d_l f_pm(l)   (lattice sums, see lattice_check.py).
Residue functional (proved):  sin^2(pi alpha0) F_+ - cos^2(pi alpha0) F_- = 2 pi sin(2 pi alpha0) C X^2 / Gamma(2q)^2.
Here we evaluate F_+ and F_- separately (convergent iff tau > 2q - 1 when 2 kappa > 1) by partial sums over spins and a least-squares
fit of the remainder with the known exponents L^(2q-1-tau-j) and L^(-2tau-j), to test whether c0, c1 are separately elementary.
usage: explore_c01.py d tau dps Lmax K
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import mpmath as mp
import hp_general_d_copy as H
from spec_S import mult_fp, S_closed


def main():
    d, tau = mp.mpf(sys.argv[1]), mp.mpf(sys.argv[2])
    dps, Lmax, K = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    mp.mp.dps = dps
    d, tau = mp.mpf(sys.argv[1]), mp.mpf(sys.argv[2])
    q = d / 4; a0, b0 = q / 2 - tau / 4, 3 * q / 2 + tau / 4; kap = b0 - a0
    h = mp.mpf(1) / 2
    N0 = 60
    Nmax = N0 + 4 * Lmax + 2
    lo, hi = -(Nmax + Lmax + 2), Nmax + Lmax + 2
    st = time.time()
    # tables of phi(k)^2 and phi(k+1/2)^2
    P2 = {k: (mp.gamma(k + a0) / mp.gamma(k + b0)) ** 2 for k in range(lo, hi)}
    H2 = {k: (mp.gamma(k + h + a0) / mp.gamma(k + h + b0)) ** 2 for k in range(lo, hi)}
    print('tables %.0f s' % (time.time() - st), flush=True)
    rp = (mp.sin(mp.pi * b0) / mp.sin(mp.pi * a0)) ** 2
    rm = (mp.cos(mp.pi * b0) / mp.cos(mp.pi * a0)) ** 2

    def tail(factors, pref, N):
        P, E = H.stirling_series(factors, K)
        return pref * mp.fsum(E[k] * H.hz(P + k, N) for k in range(K + 1) if E[k] != 0)

    fp, fm = [], []
    for l in range(Lmax):
        N = N0 + 4 * l
        pos = mp.fsum(P2[l + n] * P2[-n] for n in range(N)) + tail([(l + a0, l + b0, 2), (1 - b0, 1 - a0, 2)], rp, N)
        mid = mp.fsum(P2[l + n] * P2[-n] for n in range(-l, 0))
        fp.append(2 * pos - P2[l] * P2[0] + mid)
        pos = mp.fsum(H2[l + n] * H2[-n - 1] for n in range(N)) + tail([(l + h + a0, l + h + b0, 2), (h + 1 - b0, h + 1 - a0, 2)], rm, N)
        mid = mp.fsum(H2[l + n] * H2[-n - 1] for n in range(-l, 0))
        fm.append(2 * pos + mid)
    print('lattice sums %.0f s' % (time.time() - st), flush=True)
    dl = [mult_fp(d, l) for l in range(Lmax)]
    W = S_closed(d, tau) / mp.gamma(2 * q) ** 2
    s2, c2 = mp.sin(mp.pi * a0) ** 2, mp.cos(mp.pi * a0) ** 2
    # check of the residue functional per spin is done in lattice_check.py; here the spin sums
    res = {}
    for name, f in (('F_plus', fp), ('F_minus', fm), ('Resfun', [s2 * x - c2 * y for x, y in zip(fp, fm)])):
        part = [0] * (Lmax + 1)
        for l in range(Lmax):
            part[l + 1] = part[l] + dl[l] * f[l]
        exps = []
        for j in range(12):
            exps += [2 * q - 1 - tau - j, -2 * tau - j]
        exps = sorted(set([mp.nstr(e, 30) for e in exps]), key=lambda s: -mp.mpf(s))
        exps = [mp.mpf(e) for e in exps]
        fits = []
        for nterm in (8, 12, 16):
            Ls = sorted(set(int(mp.nint(Lmax * mp.mpf(1) / 8 * mp.power(8, mp.mpf(i) / nterm))) for i in range(nterm + 1)))
            if len(Ls) != nterm + 1:
                continue
            with mp.workdps(dps + 20):
                A = mp.matrix(nterm + 1, nterm + 1); bvec = mp.matrix(nterm + 1, 1)
                for i, L in enumerate(Ls):
                    A[i, 0] = 1
                    for j in range(nterm):
                        A[i, j + 1] = mp.mpf(L) ** exps[j]
                    bvec[i] = part[L]
                sol = mp.lu_solve(A, bvec)
            fits.append(sol[0])
        res[name] = dict(value=mp.nstr(fits[-1], 30), spread=mp.nstr(max(abs(x - fits[-1]) for x in fits), 3))
    resfun_exact = 2 * mp.pi * mp.sin(2 * mp.pi * a0) * W
    out = dict(d=sys.argv[1], tau=sys.argv[2], dps=dps, Lmax=Lmax, K=K, results=res,
               resfun_exact=mp.nstr(resfun_exact, 30), W=mp.nstr(W, 30),
               c0=mp.nstr((s2 ** 2 * mp.mpf(res['F_plus']['value']) + c2 ** 2 * mp.mpf(res['F_minus']['value'])) / 2, 25),
               c1=mp.nstr((s2 ** 2 * mp.mpf(res['F_plus']['value']) - c2 ** 2 * mp.mpf(res['F_minus']['value'])) / 2, 25),
               seconds=round(time.time() - st, 1))
    print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
