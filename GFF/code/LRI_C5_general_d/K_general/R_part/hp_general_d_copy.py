#!/usr/bin/env python3
"""High-precision reference values of the five-loop masters at GENERIC dimension d (condensed note Sec. 16):
   W_r(d;b) = <t_{l,b}^r>_d (gs:balancedWheel), P4(d) = W_4(d;d/2), 3Q_d = W_3(d;d/2),
   L_d = dW_4/db, Z_d = (1/9) d^2W_3/db^2 at b = d/2 (gs:wheelJets),
   K_d = -AU/4 + (F_3 + c* F_2)/4 with F(tau) = <t_l^2 (R_tau - S_tau)>_d (gs:Kspectral, gs:RS).

Spectral trace <f>_d = (1/pi) sum_l d_l(d) int_0^inf f dnu,  d_0 = 1,  d_l = (2l+d-2) Gamma(l+d-2)/(Gamma(d-1) l!)  (gs:spectrum).
Spins l < L: direct tanh-sinh quadrature of the nu-symmetrized integrand.  Spins l >= L: with x = l/2 + i nu every factor is a
Gamma ratio Gamma(x+al)/Gamma(x+be) (or in xb = l/2 - i nu); its Stirling expansion and the exact integral
   int_R x^-p xb^-p' dnu = 2 pi l^(1-p-p') Gamma(p+p'-1)/(Gamma(p)Gamma(p'))
give per-spin terms l^(1-p-p'); the multiplicity is expanded as
   d_l = [Gamma(d-1)]^-1 (2l+d-2) l^(d-3) sum_j g_j l^-j     (Stirling for Gamma(l+d-2)/Gamma(l+1)),
so the spin tail is a finite sum of Hurwitz zeta values zeta(s, L), computed by Euler-Maclaurin (NOT mpmath.zeta, whose
complex-s values have an absolute error floor ~10^-dps).  b- and tau-derivatives: Cauchy integrals on circles.

usage: hp_general_d.py OUT.json d DPS SPINS KMAX M PART RHO      PART in {b, t}   (b: W3, W4 on the b-circle; t: F on the tau-circle)
       hp_general_d.py check d DPS SPINS KMAX                       (centre values only, serial)
"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool


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


_hz = {}
def hz(s, a, N=24, J=60):
    """Hurwitz zeta for Re s > 1, a >= ~30: direct sum + Euler-Maclaurin at a+N, raised precision, cached."""
    key = (mp.nstr(s, mp.mp.dps + 5), str(a), mp.mp.dps)
    if key in _hz:
        return _hz[key]
    with mp.workdps(mp.mp.dps + 25):
        s = mp.mpmathify(s); a = mp.mpf(a)
        tot = mp.fsum((a + n) ** (-s) for n in range(N))
        A = a + N
        em = A ** (1 - s) / (s - 1) + A ** (-s) / 2
        poch = s; Ap = A ** (-s - 1)
        for j in range(1, J + 1):
            if j > 1:
                poch *= (s + 2 * j - 3) * (s + 2 * j - 2); Ap /= A * A
            em += mp.bernoulli(2 * j) / mp.factorial(2 * j) * poch * Ap
        v = +(tot + em)
    _hz[key] = v
    return v


def multiplicity(d, l):
    if l == 0:
        return mp.mpf(1)
    return (2 * l + d - 2) * mp.gamma(l + d - 2) * mp.rgamma(d - 1) * mp.rgamma(l + 1)


def tail(pref, fx, fxb, L, K, d):
    P, E = stirling_series(fx, K)
    Pb, Eb = stirling_series(fxb, K)
    Pd, g = stirling_series([(d - 2, mp.mpf(1), 1)], K)          # Gamma(l+d-2)/Gamma(l+1) = l^(d-3) sum g_j l^-j
    H = []
    for m in range(K + 1):
        H.append(mp.fsum(E[k] * Eb[m - k] * mp.gamma(P + Pb + m - 1) * mp.rgamma(P + k) * mp.rgamma(Pb + m - k)
                         for k in range(m + 1) if E[k] != 0 and Eb[m - k] != 0))
    tot = 0
    for m in range(K + 1):
        if H[m] == 0:
            continue
        for j in range(K + 1 - m):
            s1 = P + Pb + m + j + 1 - d
            tot += H[m] * g[j] * (2 * hz(s1, L) + (d - 2) * hz(s1 + 1, L))
    return pref * mp.rgamma(d - 1) * tot


def lgr(z, al, be):
    return mp.loggamma(z + al) - mp.loggamma(z + be)


def spectral(pref, fx, fxb, L, K, d, breaks):
    tot = 0
    for l in range(L):
        sc = mp.mpf(max(l, 1)) / 2

        def g(y):
            nu = sc * y
            out = 0
            for sgn in (1, -1):
                x, xb = mp.mpf(l) / 2 + sgn * 1j * nu, mp.mpf(l) / 2 - sgn * 1j * nu
                out += mp.exp(sum(m * lgr(x, al, be) for al, be, m in fx) + sum(m * lgr(xb, al, be) for al, be, m in fxb))
            return out / 2
        tot += multiplicity(d, l) * sc / mp.pi * mp.quad(g, breaks)
    return pref * tot + tail(pref, fx, fxb, L, K, d)


def nu_tail(fx, fxb, l, Y, K):
    """int_Y^inf of the nu-symmetrized integrand at spin l.  With x = c + i nu (c = l/2): Gamma(x+al)/Gamma(x+be) = Gamma(w+al+c)/Gamma(w+be+c),
    w = i nu, so the Stirling expansion in w with offsets shifted by c gives a pure power series in 1/nu:
       f ~ (i nu)^-P (-i nu)^-Pb sum_{k,kb} E_k Eb_kb (i nu)^-k (-i nu)^-kb,   int_Y^inf nu^-s dnu = Y^(1-s)/(s-1).
    The nu -> -nu half of the symmetrization swaps i -> -i."""
    c = mp.mpf(l) / 2
    sh = lambda fl: [(al + c, be + c, m) for al, be, m in fl]
    P, E = stirling_series(sh(fx), K); Pb, Eb = stirling_series(sh(fxb), K)
    tot = 0
    for sgn in (1, -1):
        for k in range(K + 1):
            for kb in range(K + 1 - k):
                p1, p2 = P + k, Pb + kb
                sig = p1 + p2
                tot += E[k] * Eb[kb] * mp.expj(-sgn * mp.pi * p1 / 2) * mp.expj(sgn * mp.pi * p2 / 2) * Y ** (1 - sig) / (sig - 1)
    return tot / 2


def spectral_combo(terms, L, K, d, breaks):
    """sum_i sign_i * pref_i <prod factors_i>: finite spins integrate the COMBINED integrand (needed when the separate nu-integrals
    diverge, e.g. t^2 R and t^2 S at small d), tails are added term by term (analytic in tau)."""
    tot = 0
    for l in range(L):
        sc = mp.mpf(max(l, 1)) / 2

        def g(y):
            nu = sc * y
            out = 0
            for sgn in (1, -1):
                x, xb = mp.mpf(l) / 2 + sgn * 1j * nu, mp.mpf(l) / 2 - sgn * 1j * nu
                for sg, pref, fx, fxb in terms:
                    out += sg * pref * mp.exp(sum(m * lgr(x, al, be) for al, be, m in fx) + sum(m * lgr(xb, al, be) for al, be, m in fxb))
            return out / 2
        if os.environ.get('HPG_NUTAIL', '0') == '1':
            Y = 20 * (mp.mpf(l) / 2 + 1)
            ys = [y for y in breaks if y != mp.inf and y * sc < Y] + [Y / sc]
            val = mp.quad(g, ys) + sum(sg * pref * nu_tail(fx, fxb, l, Y, K) for sg, pref, fx, fxb in terms) / sc
        else:
            val = mp.quad(g, breaks)
        tot += multiplicity(d, l) * sc / mp.pi * val
    return tot + sum(sg * tail(pref, fx, fxb, L, K, d) for sg, pref, fx, fxb in terms)


def wheel(r, b, d, L, K, breaks):
    pref = (mp.gamma(d / 2) * mp.gamma((d - b) / 2) * mp.rgamma(b / 2)) ** r
    f = [(b / 4, d / 2 - b / 4, r)]
    if os.environ.get('HPG_NUTAIL', '0') == '1':
        return spectral_combo([(1, pref, f, f)], L, K, d, breaks)
    return spectral(pref, f, f, L, K, d, breaks)


def Kmixed(tau, d, L, K, breaks):
    q = d / 4
    a, bb = q / 2, 3 * q / 2
    t2 = [(a, bb, 2)]
    pref = mp.gamma(2 * q) ** 2
    Rx, Rxb = t2 + [(a, a + tau, 1)], t2 + [(bb - tau, bb, 1)]
    Sx = t2 + [(a - tau / 4, a, 2), (bb, bb + tau / 4, 2)]
    return spectral_combo([(1, pref, Rx, Rxb), (-1, pref, Sx, Sx)], L, K, d, breaks)


def cfg():
    return json.loads(os.environ['HPG_CFG'])


def job(k):
    c = cfg(); mp.mp.dps = c['dps']
    d = mp.mpf(c['d']); breaks = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, 40, mp.inf]
    th = 2 * mp.pi * k / c['M']
    if k < 0:                                      # off-diagonal real b = d/2 + rho_off * (+1, -1)
        b = d / 2 + (1 if k == -1 else -1) * mp.mpf(c['rho_off'])
        return k, [str(wheel(3, b, d, c['spins'], c['kmax'], breaks)), str(wheel(4, b, d, c['spins'], c['kmax'], breaks)), str(b)]
    if c['part'] == 'b':
        b = d / 2 + mp.mpf(c['rho']) * mp.expj(th)
        v = (wheel(3, b, d, c['spins'], c['kmax'], breaks), wheel(4, b, d, c['spins'], c['kmax'], breaks))
    else:
        v = (Kmixed(mp.mpf(c['rho']) * mp.expj(th), d, c['spins'], c['kmax'], breaks),)
    return k, [str(x) for x in v]


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        d, dps, L, K = mp.mpf(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        mp.mp.dps = dps; st = time.time(); br = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, 40, mp.inf]
        print('d =', d, ' W3(d/2)/3 =', mp.nstr(mp.re(wheel(3, d / 2, d, L, K, br)) / 3, dps - 2),
              ' W4(d/2) =', mp.nstr(mp.re(wheel(4, d / 2, d, L, K, br)), dps - 2), ' %.0f s' % (time.time() - st))
        sys.exit()
    out = sys.argv[1]
    c = dict(d=sys.argv[2], dps=int(sys.argv[3]), spins=int(sys.argv[4]), kmax=int(sys.argv[5]), M=int(sys.argv[6]), part=sys.argv[7], rho=sys.argv[8],
             rho_off=sys.argv[9] if len(sys.argv) > 9 else '0.05')
    os.environ['HPG_CFG'] = json.dumps(c)
    st = time.time(); ks = list(range(c['M'] // 2 + 1))
    if c['part'] == 'b':
        ks = [-1, -2] + ks
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 10))
    print('d', c['d'], 'part', c['part'], 'tasks', len(ks), 'workers', workers, flush=True)
    with Pool(workers) as pool:
        res = dict(pool.map(job, ks, chunksize=1))
    json.dump(dict(c, seconds=time.time() - st, values={str(k): res[k] for k in ks}), open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
