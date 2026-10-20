#!/usr/bin/env python3
"""Side check: Z_4 = (1/9) d^2W_3(4;b)/db^2 at b=2 (d=4 analogue), spectral, to compare with zeta values.
Spectral trace at d=4: (1/pi) sum_l (l+1)^2 int_0^inf t^3 dnu, n=l+1, alpha = n/2+s1, beta = n/2+1-s1, s1=(b-2)/4."""
import sys, time
import mpmath as mp
sys.path.insert(0, '..')
import hp_masters_d3 as H
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
L = int(sys.argv[2]) if len(sys.argv) > 2 else 30
K = int(sys.argv[3]) if len(sys.argv) > 3 else 30
M = int(sys.argv[4]) if len(sys.argv) > 4 else 24

def tail4(pref, f, L, K):
    P, E = H.stirling_series(f, K)
    s = 0
    for k in range(K + 1):
        for kb in range(K + 1 - k):
            p, pb = P + k, P + kb
            s += E[k] * E[kb] * mp.gamma(p + pb - 1) * mp.rgamma(p) * mp.rgamma(pb) * mp.zeta(p + pb - 3, L + 1)
    return pref * s

def W3_4(b):
    s1 = (b - 2) / 4
    pref = (mp.gamma(2) * mp.gamma((4 - b) / 2) / mp.gamma(b / 2)) ** 3
    f = [(s1, 1 - s1, 3)]
    tot = 0
    for l in range(L):
        n = mp.mpf(l + 1)
        def g(y):
            nu = n * y / 2
            out = 0
            for sg in (1, -1):
                x, xb = n / 2 + sg * 1j * nu, n / 2 - sg * 1j * nu
                out += mp.exp(3 * (H.lgr(x, s1, 1 - s1) + H.lgr(xb, s1, 1 - s1)))
            return out / 2
        tot += n ** 3 / (2 * mp.pi) * pref * mp.quad(g, H.BREAKS)
    return tot + tail4(pref, f, L, K)

st = time.time()
print('W3(4;2) =', W3_4(mp.mpf(2)), ' 6 zeta3 =', 6 * mp.zeta(3))
rho = mp.mpf('0.1')
vals = []
for k in range(M // 2 + 1):
    vals.append(W3_4(2 + rho * mp.expj(2 * mp.pi * k / M)))
full = [vals[k] if k <= M // 2 else mp.conj(vals[M - k]) for k in range(M)]
c = lambda j: mp.fsum(full[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
print("W' =", c(1)); Z4 = 2 * c(2) / 9; print('Z4 =', Z4, ' %.0f s' % (time.time() - st))
z3, z5, pi = mp.zeta(3), mp.zeta(5), mp.pi
print(mp.identify(mp.re(Z4), ['zeta(3)', 'zeta(5)', 'pi**2*zeta(3)'], tol=mp.mpf(10) ** (-mp.mp.dps + 8)))
print(mp.pslq([mp.re(Z4), z5, pi ** 2 * z3, z3, pi**4], maxcoeff=10 ** 5, maxsteps=10 ** 6, tol=mp.mpf(10) ** (-mp.mp.dps + 8)))
