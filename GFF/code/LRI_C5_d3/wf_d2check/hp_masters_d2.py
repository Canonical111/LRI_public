#!/usr/bin/env python3
"""Independent d=2 check of L_2 and K_2 from the spectral kernel (condensed note gs:spectrum ... gs:Ksubtraction).

Adapted from LRI_C5_d3/hp_masters_d3.py (finite spins + Stirling-Hurwitz tail, Cauchy derivatives) to d = 2:
  q = 1/2,  a_l = l/2 + 1/4,  b_l = l/2 + 3/4,  d_0 = 1,  d_l = 2 (l >= 1),
  <f>_2 = (1/pi) sum_l d_l int_0^inf f dnu   (f symmetrized in nu).
Stirling centre: x = l/2 + c0 + i nu (c0 is a run parameter), so a_l = x + (1/4 - c0), b_l = x + (3/4 - c0).

Tail (l >= L, d_l = 2):  with  prod(Gamma ratios) ~ x^-P xb^-Pb sum_{k,kb} E_k Eb_kb x^-k xb^-kb  and
  int_R x^-p xb^-p' dnu = 2 pi n^(1-p-p') Gamma(p+p'-1)/(Gamma(p)Gamma(p')),   Re x = n/2,  n = l + 2 c0,
  sum_{l>=L} (1/pi) * 2 * (1/2) int_R f dnu = 2 pref sum E Eb Gamma(p+pb-1)/(Gamma(p)Gamma(pb)) zeta(p+pb-1, L + 2 c0).
(at d=3 the weight 2l+1 = 2n gave zeta(p+pb-2, L+1/2); at d=2 the weight is the constant 2.)

  W_r(2;b) = < t_{l,b}^r >,  t_{l,b} = Gamma(1) Gamma((2-b)/2)/Gamma(b/2) |Gamma(l/2+b/4+i nu)/Gamma(l/2+1-b/4+i nu)|^2
  Q_2 = W_3(1)/3,  P_4(2) = W_4(1),  L_2 = dW_4/db|_{b=1},  Z_2 = (1/9) d^2 W_3/db^2|_{b=1}
  F(tau) = < t^2 (R_tau - S_tau) >  (gs:RS),   K_2 = -A U/4 + (F_3 + c* F_2)/4,  A = 4 log 2, U = psi_2(1/2) = -14 zeta(3),
  c* = psi_0(1) + psi_0(1) = -2 gamma.
"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool

CFG = dict(dps=30, spins=16, kmax=20, M=24, rho='0.1', c0='0', breaks='0,0.3,1.5,6,inf', part='b')


def setcfg(c):
    CFG.update(c)
    mp.mp.dps = int(CFG['dps'])


def breaks():
    return [mp.inf if s == 'inf' else mp.mpf(s) for s in CFG['breaks'].split(',')]


def stirling_series(factors, K):
    """factors: list of (al, be, m) for (Gamma(x+al)/Gamma(x+be))^m.  prod = x^(-P) sum_k E_k x^-k."""
    lead = sum(m * (al - be) for al, be, m in factors)
    c = [mp.mpf(0)] * (K + 1)
    for al, be, m in factors:
        for k in range(1, K + 1):
            c[k] += m * (-1) ** (k + 1) * (mp.bernpoly(k + 1, al) - mp.bernpoly(k + 1, be)) / (k * (k + 1))
    E = [mp.mpf(1)] + [0] * K
    for k in range(1, K + 1):
        E[k] = mp.fsum(j * c[j] * E[k - j] for j in range(1, k + 1)) / k
    return -lead, E


def hz(s, a, N=200, J=45):
    """Hurwitz zeta(s, a) for Re s > 1 by direct sum + Euler-Maclaurin at A = a + N, at raised precision.
    (mpmath 1.3 mp.zeta(s, a) with INTEGER a and complex s returns zeta(s) - sum_{n<a} n^-s, which has an
    absolute error ~10^-dps that is enormous relative to a^-s at large Re s; it poisoned the c0 = 0 tails.)"""
    with mp.workdps(mp.mp.dps + 25):
        s = mp.mpmathify(s); a = mp.mpmathify(a)
        tot = mp.fsum((a + n) ** (-s) for n in range(N))
        A = a + N
        em = A ** (1 - s) / (s - 1) + A ** (-s) / 2
        poch = s                                       # (s)_{2j-1}
        Ap = A ** (-s - 1)
        for j in range(1, J + 1):
            if j > 1:
                poch *= (s + 2 * j - 3) * (s + 2 * j - 2)
                Ap /= A * A
            em += mp.bernoulli(2 * j) / mp.factorial(2 * j) * poch * Ap
        return +(tot + em)


def tail(pref, fx, fxb, L, K, c0):
    """sum_{l>=L} with weight 2: 2 pref sum_j Gamma(2P-1+j) zeta(2P-1+j, L+2c0) sum_{k+kb=j} E_k Eb_kb/(Gamma(P+k)Gamma(Pb+kb))."""
    P, E = stirling_series(fx, K)
    Pb, Eb = stirling_series(fxb, K)
    h = L + 2 * c0
    rg = [mp.rgamma(P + k) for k in range(K + 1)]
    rgb = [mp.rgamma(Pb + k) for k in range(K + 1)]
    s = 0
    for j in range(K + 1):
        inner = mp.fsum(E[k] * Eb[j - k] * rg[k] * rgb[j - k] for k in range(j + 1) if E[k] != 0 and Eb[j - k] != 0)
        if inner == 0:
            continue
        sj = P + Pb - 1 + j
        s += inner * mp.gamma(sj) * hz(sj, h)
    return 2 * pref * s


def lgr(z, al, be):
    return mp.loggamma(z + al) - mp.loggamma(z + be)


def spectral_multi(prefs, fams, L, K, c0):
    """<f_i> for several integrands sharing one quadrature.  fams[i] = (fx, fxb); f_i = prefs[i] prod factors.
    Returns list of values (finite spins l < L directly, plus the tail)."""
    BR = breaks()
    tots = [mp.mpf(0)] * len(fams)
    for l in range(L):
        dl = 1 if l == 0 else 2
        sc = mp.mpf(l + 1) / 2                     # nu-scale for the quadrature (works at l = 0)
        cen = mp.mpf(l) / 2 + c0
        for i, (fx, fxb) in enumerate(fams):
            def g(y):
                nu = sc * y
                x, xb = cen + 1j * nu, cen - 1j * nu
                A1 = sum(m * lgr(x, al, be) for al, be, m in fx)
                B1 = sum(m * lgr(xb, al, be) for al, be, m in fxb)
                if fx is fxb:
                    return mp.exp(A1 + B1)
                A2 = sum(m * lgr(xb, al, be) for al, be, m in fx)
                B2 = sum(m * lgr(x, al, be) for al, be, m in fxb)
                return (mp.exp(A1 + B1) + mp.exp(A2 + B2)) / 2
            tots[i] += dl * sc / mp.pi * prefs[i] * mp.quad(g, BR)
    return [tots[i] + tail(prefs[i], fx, fxb, L, K, c0) for i, (fx, fxb) in enumerate(fams)]


def wheels(b):
    """(W_3(2;b), W_4(2;b)) with one shared log t per node."""
    BR = breaks()
    L, K, c0 = int(CFG['spins']), int(CFG['kmax']), mp.mpf(CFG['c0'])
    al, be = b / 4 - c0, 1 - b / 4 - c0
    lpref = mp.loggamma((2 - b) / 2) - mp.loggamma(b / 2)
    W = [mp.mpf(0), mp.mpf(0)]
    for l in range(L):
        dl = 1 if l == 0 else 2
        sc = mp.mpf(l + 1) / 2
        cen = mp.mpf(l) / 2 + c0
        cache = {}

        def logt(y):                               # W_3 and W_4 quadratures share nodes: cache log t
            v = cache.get(y)
            if v is None:
                nu = sc * y
                x, xb = cen + 1j * nu, cen - 1j * nu
                v = cache[y] = lpref + lgr(x, al, be) + lgr(xb, al, be)
            return v
        W[0] += dl * sc / mp.pi * mp.quad(lambda y: mp.exp(3 * logt(y)), BR)
        W[1] += dl * sc / mp.pi * mp.quad(lambda y: mp.exp(4 * logt(y)), BR)
    for i, r in enumerate((3, 4)):
        fr = [(al, be, r)]
        W[i] += tail(mp.exp(r * lpref), fr, fr, L, K, c0)
    return W


def Kmixed(tau):
    L, K, c0 = int(CFG['spins']), int(CFG['kmax']), mp.mpf(CFG['c0'])
    a, bb = mp.mpf(1) / 4 - c0, mp.mpf(3) / 4 - c0
    t2 = [(a, bb, 2)]
    pref = mp.mpf(1)                               # Gamma(2q)^2 = Gamma(1)^2
    Rx, Rxb = t2 + [(a, a + tau, 1)], t2 + [(bb - tau, bb, 1)]
    Sx = t2 + [(a - tau / 4, a, 2), (bb, bb + tau / 4, 2)]
    vR, vS = spectral_multi([pref, pref], [(Rx, Rxb), (Sx, Sx)], L, K, c0)
    return vR - vS


def job(k):
    setcfg(json.loads(os.environ['C5D2_CFG']))
    M = int(CFG['M'])
    th = 2 * mp.pi * k / M
    z = mp.mpf(CFG['rho']) * mp.expj(th)
    if CFG['part'] == 'b':
        v = wheels(1 + z)
    else:
        v = [Kmixed(z)]
    return k, [str(x) for x in v]


if __name__ == '__main__':
    out = sys.argv[1]
    keys = ['dps', 'spins', 'kmax', 'M', 'rho', 'c0', 'breaks', 'part']
    c = dict(CFG)
    for a in sys.argv[2:]:
        kk, vv = a.split('=', 1)
        assert kk in keys, kk
        c[kk] = vv
    os.environ['C5D2_CFG'] = json.dumps(c)
    setcfg(c)
    st = time.time()
    if c['part'] == 'check':                     # centre values only
        W3, W4 = wheels(mp.mpf(1))
        rec = dict(c, W3=str(W3), W4=str(W4), Q2=str(W3 / 3), seconds=time.time() - st)
        json.dump(rec, open(out, 'w'), indent=1)
        print(json.dumps(rec, indent=1))
        sys.exit()
    M = int(c['M'])
    ks = list(range(M // 2 + 1))
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', 3))
    print('cfg', c, 'tasks', len(ks), 'workers', workers, flush=True)
    with Pool(workers) as pool:
        res = dict(pool.map(job, ks, chunksize=1))
    json.dump(dict(c, seconds=time.time() - st, values={str(k): res[k] for k in ks}), open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st), flush=True)
