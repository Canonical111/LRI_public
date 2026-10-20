#!/usr/bin/env python3
"""K_d as a tau-jet of the finite-sample formula (tag R_part).

  J_{2tau} = C(tau) <t^2 R_tau>_d,   <t^2 R_tau>_d = sum_j w_j(q,tau) Xi(t_j;tau)   (rblocks.py, regularized blocks),
  F(tau)   = J_{2tau} - C(tau)^2 X(tau)^4,   X = Gamma(q-tau/2)/Gamma(q+tau/2)     [= C(tau) <t^2 (R_tau - S_tau)>, O(tau)]
  K_d      = -A U/4 + (1/4) [tau^2] F(tau)                                        (gs:Kspectral / gs:Ksubtraction)
  check    : [tau^0] F = 0 ;  [tau^1] F = <t^2 E_2>_d ;   also K_d = (1/4)[tau^2](J_{2tau} - J^Gamma_{2tau}) (gs:Kdefinition).
Taylor coefficients by the trapezoidal (FFT) rule on |tau| = r (conjugate symmetry: only the upper half is evaluated).
usage: kjet.py d [r] [N] [K] [M] [dps] [out.json]
"""
import sys, time, json
import mpmath as mp
import rblocks as rb


def Bd(d, a, b):
    G, rG = mp.gamma, mp.rgamma
    return G(d / 2) * G((d - a) / 2) * G((d - b) / 2) * G((a + b - d) / 2) * rG(a / 2) * rG(b / 2) * rG((2 * d - a - b) / 2)


def JGamma(d, tau):
    t = 2 * tau
    B1 = Bd(d, d / 2, d - t)
    return B1 ** 2 + 2 / t * (B1 - Bd(d, d / 2 + 2 * t, d - t))


def run(d, r=mp.mpf('0.1'), N=32, K=14, M=160, verbose=True):
    q = d / 4
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    U = mp.psi(2, q)
    Fs, Js, taus = {}, {}, {}
    st = time.time()
    for s in range(N // 2 + 1):
        tau = r * mp.expj(2 * mp.pi * s / N)
        if s == 0 or s == N // 2:
            tau = mp.mpf(mp.re(tau))
        tr = rb.tR(q, tau, K, M)
        C = rb.Cfac(q, tau)
        J = C * tr
        X = mp.gamma(q - tau / 2) * mp.rgamma(q + tau / 2)
        Fs[s] = J - C ** 2 * X ** 4
        Js[s] = J - JGamma(d, tau)
        taus[s] = tau
        if verbose:
            print('  s %2d  tau %s  F %s  (%.0fs)' % (s, mp.nstr(tau, 6), mp.nstr(Fs[s], 12), time.time() - st), flush=True)
    for s in range(N // 2 + 1, N):
        Fs[s] = mp.conj(Fs[N - s]); Js[s] = mp.conj(Js[N - s]); taus[s] = mp.conj(taus[N - s])
    coef = lambda vals, k: mp.re(mp.fsum(vals[s] * taus[s] ** (-k) for s in range(N)) / N)
    F0, F1, F2 = coef(Fs, 0), coef(Fs, 1), coef(Fs, 2)
    K_d = -A * U / 4 + F2 / 4
    K_def = coef(Js, 2) / 4
    decay = {k: mp.nstr(abs(coef(Fs, k)), 3) for k in (3, 6, 10, 14, 18, 22, 26, 30)}
    return dict(d=str(d), r=str(r), N=N, K=K, M=M, dps=mp.mp.dps, K_d=mp.nstr(K_d, mp.mp.dps - 5), K_def=mp.nstr(K_def, mp.mp.dps - 5),
                F0=mp.nstr(F0, 5), tE2=mp.nstr(F1, mp.mp.dps - 8), Jdef_low=[mp.nstr(coef(Js, k), 5) for k in (-2, -1, 0, 1)],
                F_taylor_abs=decay, F_samples={str(s): [mp.nstr(mp.re(Fs[s]), mp.mp.dps - 5), mp.nstr(mp.im(Fs[s]), mp.mp.dps - 5)] for s in range(N // 2 + 1)},
                seconds=round(time.time() - st, 1))


if __name__ == '__main__':
    a = sys.argv[1:]
    d = a[0]
    mp.mp.dps = int(a[5]) if len(a) > 5 else 40
    r = mp.mpf(a[1]) if len(a) > 1 else mp.mpf('0.1')
    N = int(a[2]) if len(a) > 2 else 32
    K = int(a[3]) if len(a) > 3 else 14
    M = int(a[4]) if len(a) > 4 else 160
    rec = run(mp.mpf(d), r, N, K, M)
    print(json.dumps(rec, indent=1))
    if len(a) > 6:
        json.dump(rec, open(a[6], 'w'), indent=1)
