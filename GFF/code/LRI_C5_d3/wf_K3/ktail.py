"""Spin tail sum_{l>=L} (2l+1) I_l at d=3 from the centered Stirling expansion (method of hp_masters_d3.py), with the
tau-dependence handled on a Cauchy circle: F(tau)=<t^2(R_tau-S_tau)>, K-part = (F3 + c* F2)/4."""
import mpmath as mp

def stirling_series(factors, K):
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
    P, E = stirling_series(fx, K)
    Pb, Eb = stirling_series(fxb, K)
    s = 0
    for k in range(K + 1):
        for kb in range(K + 1 - k):
            p, pb = P + k, Pb + kb
            s += E[k] * Eb[kb] * mp.gamma(p + pb - 1) * mp.rgamma(p) * mp.rgamma(pb) * mp.zeta(p + pb - 2, L + mp.mpf(1) / 2)
    return 2 * pref * s

def Ftail(tau, L, K):
    a, bb = mp.mpf(1) / 8, mp.mpf(7) / 8
    t2 = [(a, bb, 2)]
    pref = mp.gamma(mp.mpf(3) / 2) ** 2
    Rx, Rxb = t2 + [(a, a + tau, 1)], t2 + [(bb - tau, bb, 1)]
    Sx = t2 + [(a - tau / 4, a, 2), (bb, bb + tau / 4, 2)]
    return tail(pref, Rx, Rxb, L, K) - tail(pref, Sx, Sx, L, K)

def Ktail(L, K, M=48, rho='0.05'):
    rho = mp.mpf(rho)
    vals = []
    for k in range(M // 2 + 1):
        vals.append(Ftail(rho * mp.expj(2 * mp.pi * k / M), L, K))
    full = [vals[k] if k <= M // 2 else mp.conj(vals[M - k]) for k in range(M)]
    coef = lambda j: mp.fsum(full[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
    F = [coef(j) for j in range(4)]
    cstar = mp.digamma(1) + mp.digamma(mp.mpf(3) / 2)
    return (F[3] + cstar * F[2]) / 4, F
