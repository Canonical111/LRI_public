#!/usr/bin/env python3
"""High-precision d=3 nonprimitive masters K_3, L_3, Z_3 from the spectral kernel (condensed note Sec. 16).

Spectral trace at d=3: <f> = (1/pi) sum_l (2l+1) int_0^inf f dnu, with n = l+1/2 and x = n/2 + i nu.
Every integrand is a product of Gamma ratios Gamma(x+al)/Gamma(x+be) and Gamma(xb+al)/Gamma(xb+be), xb = n/2 - i nu.
Spins l < Lsp are integrated directly; the rest use the centered Stirling expansion
  log Gamma(x+al) - log Gamma(x+be) = (al-be) log x + sum_k (-1)^(k+1) [B_{k+1}(al) - B_{k+1}(be)]/(k(k+1)) x^-k
and the exact integral  int_R x^-p xb^-p' dnu = 2 pi n^(1-p-p') Gamma(p+p'-1)/(Gamma(p)Gamma(p')),
so that the spin tail is a finite sum of Hurwitz zeta values (the method of the archived d=3 check_spectral.py,
extended to unequal and complex offsets).

  W_r(3;b)  balanced wheel with rim exponent b (gs:balancedWheel):  L_3 = dW_4/db, Z_3 = (1/9) d^2 W_3/db^2 at b=3/2
  F(tau)    = <t^2 (R_tau - S_tau)> (gs:RS), symmetrized in nu:     K_3 = -A U/4 + (F_3 + c* F_2)/4
Derivatives are Cauchy integrals on circles in b and tau (W and F are analytic there).
"""
import sys, json, time
import mpmath as mp
from multiprocessing import Pool

DPS = int(sys.argv[2]) if len(sys.argv) > 2 else 50
LSP = int(sys.argv[3]) if len(sys.argv) > 3 else 64
KMAX = int(sys.argv[4]) if len(sys.argv) > 4 else 44
M = int(sys.argv[5]) if len(sys.argv) > 5 else 48
BREAKS = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, mp.inf]


def stirling_series(factors, K):
    """factors: list of (al, be, m) for (Gamma(x+al)/Gamma(x+be))^m.  Returns (P, E[0..K]) with
    prod = x^(-P) * sum_k E_k x^-k asymptotically."""
    lead = sum(m * (al - be) for al, be, m in factors)
    c = [mp.mpf(0)] * (K + 1)
    for al, be, m in factors:
        for k in range(1, K + 1):
            c[k] += m * (-1) ** (k + 1) * (mp.bernpoly(k + 1, al) - mp.bernpoly(k + 1, be)) / (k * (k + 1))
    E = [mp.mpf(1)] + [0] * K
    for k in range(1, K + 1):
        E[k] = mp.fsum(j * c[j] * E[k - j] for j in range(1, k + 1)) / k
    return -lead, E


def tail(pref, fx, fxb, L, K):
    """sum_{l>=L} (1/pi)(2l+1) int_0^inf [sym. integrand] = sum_{l>=L} 2 n^(2-p-p') Gamma(p+p'-1)/(Gamma(p)Gamma(p'))."""
    P, E = stirling_series(fx, K)
    Pb, Eb = stirling_series(fxb, K)
    s = 0
    for k in range(K + 1):
        for kb in range(K + 1 - k):
            if E[k] == 0 or Eb[kb] == 0:
                continue
            p, pb = P + k, Pb + kb
            s += E[k] * Eb[kb] * mp.gamma(p + pb - 1) * mp.rgamma(p) * mp.rgamma(pb) * mp.zeta(p + pb - 2, L + mp.mpf(1) / 2)
    return 2 * pref * s


def lgr(z, al, be):
    return mp.loggamma(z + al) - mp.loggamma(z + be)


def spectral(pref, fx, fxb, L, K):
    """<f> with f = pref * prod Gamma-ratio factors, symmetrized in nu, finite spins + tail."""
    tot = 0
    for l in range(L):
        n = mp.mpf(l) + mp.mpf(1) / 2

        def g(y):
            nu = n * y / 2
            out = 0
            for sgn in (1, -1):
                x, xb = n / 2 + sgn * 1j * nu, n / 2 - sgn * 1j * nu
                lv = sum(m * lgr(x, al, be) for al, be, m in fx) + sum(m * lgr(xb, al, be) for al, be, m in fxb)
                out += mp.exp(lv)
            return out / 2
        tot += n * n / mp.pi * pref * mp.quad(g, BREAKS)
    return tot + tail(pref, fx, fxb, L, K)


def wheel(r, b):
    s1 = (b - 1) / 4
    pref = (mp.gamma(mp.mpf(3) / 2) * mp.gamma((3 - b) / 2) * mp.rgamma(b / 2)) ** r
    f = [(s1, 1 - s1, r)]
    return spectral(pref, f, f, LSP, KMAX)


def Kmixed(tau):
    a, bb = mp.mpf(1) / 8, mp.mpf(7) / 8           # x-offsets of a_l = n/2 + 1/8, b_l = n/2 + 7/8 at q = 3/4
    t2 = [(a, bb, 2)]
    pref = mp.gamma(mp.mpf(3) / 2) ** 2
    # R_tau(s) = Gamma(a+s)Gamma(b-tau-s)/(Gamma(a+tau+s)Gamma(b-s)),  s = i nu
    Rx, Rxb = t2 + [(a, a + tau, 1)], t2 + [(bb - tau, bb, 1)]
    # S_tau(s) = [Gamma(a-tau/4+s)Gamma(a-tau/4-s)Gamma(b+s)Gamma(b-s)/(Gamma(b+tau/4+s)Gamma(b+tau/4-s)Gamma(a+s)Gamma(a-s))]^2
    Sx = t2 + [(a - tau / 4, a, 2), (bb, bb + tau / 4, 2)]
    return spectral(pref, Rx, Rxb, LSP, KMAX) - spectral(pref, Sx, Sx, LSP, KMAX)


def job(arg):
    kind, k = arg
    mp.mp.dps = DPS
    th = 2 * mp.pi * k / M
    if kind == 'b':
        b = mp.mpf(3) / 2 + mp.mpf('0.1') * mp.expj(th)
        return kind, k, (wheel(3, b), wheel(4, b))
    tau = mp.mpf('0.1') * mp.expj(th)
    return kind, k, Kmixed(tau)


if __name__ == '__main__':
    mp.mp.dps = DPS
    out = sys.argv[1]
    st = time.time()
    if len(sys.argv) > 6 and sys.argv[6] == 'check':
        Q3, P4 = wheel(3, mp.mpf(3) / 2) / 3, wheel(4, mp.mpf(3) / 2)
        print('check Q3 =', Q3, '\n      P4 =', P4, '  (%.0f s)' % (time.time() - st))
        sys.exit()
    half = M // 2
    tasks = [('b', k) for k in range(half + 1)] + [('t', k) for k in range(half + 1)]
    import os
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 10))
    print('tasks', len(tasks), 'workers', workers, flush=True)
    with Pool(workers) as pool:
        res = pool.map(job, tasks, chunksize=1)
    vals = {('b', k): v for kind, k, v in res if kind == 'b'}
    tv = {k: v for kind, k, v in res if kind == 't'}
    W3 = {k: vals[('b', k)][0] for k in range(half + 1)}
    W4 = {k: vals[('b', k)][1] for k in range(half + 1)}
    full = lambda d: [d[k] if k <= half else mp.conj(d[M - k]) for k in range(M)]
    W3f, W4f, Ff = full(W3), full(W4), full(tv)
    rho = mp.mpf('0.1')
    coef = lambda f, j: mp.fsum(f[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
    L3 = coef(W4f, 1)
    Z3 = 2 * coef(W3f, 2) / 9
    F = [coef(Ff, j) for j in range(5)]
    A = 2 + 4 * mp.log(2) - mp.pi
    U = 2 * mp.pi ** 3 - 56 * mp.zeta(3)
    cstar = mp.digamma(1) + mp.digamma(mp.mpf(3) / 2)
    K3 = -A * U / 4 + (F[3] + cstar * F[2]) / 4
    rec = dict(dps=DPS, spins=LSP, kmax=KMAX, M=M, seconds=time.time() - st,
               W3_center=str(coef(W3f, 0)), W4_center=str(coef(W4f, 0)),
               L3=str(L3), Z3=str(Z3), K3=str(K3), F=[str(x) for x in F],
               imag_parts=[str(mp.im(L3)), str(mp.im(Z3)), str(mp.im(K3))])
    json.dump(rec, open(out, 'w'), indent=1)
    for k in ('W3_center', 'W4_center', 'L3', 'Z3', 'K3'):
        print(k, rec[k])
    print('F0..F4 =', [mp.nstr(x, 12) for x in F], ' imag:', rec['imag_parts'], ' %.0f s' % rec['seconds'])
