#!/usr/bin/env python3
"""refcheck ROUTE A: spectral trace with the EXPLICIT polygamma weights of the condensed note
   (gs:w12, gs:LZspectral, gs:Kweights, gs:Kspectral), NOT the b-/tau-circle Cauchy derivatives of hp_general_d.py.

   <f>_d = (1/pi) sum_l d_l(d) int_0^inf f dnu ,   t = Gamma(2q) Gamma(a+i nu)Gamma(a-i nu)/(Gamma(b+i nu)Gamma(b-i nu)),
   a = l/2 + q/2, b = a + q, q = d/4.
   components:  W3 = <t^3> (=3Q),  W4 = <t^4> (=P4),  L = <4 t^4 w1>,  Z = <t^3 (w1^2 + w2/3)>,
                Kint = <t^2 [(c*-p)E2 - h k/2 - 5 r/32]>  (K = -AU/4 + Kint/4),  chk = <3 t^3 w1>  (must vanish).
   Re/Im of polygammas at a+i nu are continued analytically: Re F(a+i nu) -> [F(a+i nu)+F(a-i nu)]/2,
   Im F(a+i nu) -> [F(a+i nu)-F(a-i nu)]/(2i), so the per-spin value is analytic in complex l.

   nu-integral: own sinh-sinh double-exponential trapezoid, nu = s sinh((pi/2) sinh u), s = |a|, step halving to convergence.
   spin sum:    sum_{l<L} f(l) + Abel-Plana tail
                sum_{n>=0} f(L+n) = int_L^inf f(x) dx + f(L)/2 - 2 int_0^inf Im f(L+iy)/(e^{2 pi y}-1) dy,
                f(l) = d_l(d) * I(l) continued to real/complex l (independent of any large-spin asymptotic expansion).
   x-integral: x = L + L exp((pi/2) sinh u);  y-integral: y = exp(u - exp(-u)); both DE trapezoids with step halving.
   Precision: per-spin work precision dps + log10|l| + 10 so that a = l/2+q/2, b = a+q, l+d-2 are exact at huge l.

usage:  routeA_spectral.py OUT.json d DPS L [workers] [b]      (d=1: finite sum over l=0,1; b != d/2: W3, W4 only)
"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool

NC = 6
NAMES = ['W3', 'W4', 'Lint', 'Zint', 'Kint', 'chk']
G = {}


def init(d, dps, b=None):
    mp.mp.dps = dps
    G['dps'] = dps
    d = mp.mpf(d); q = d / 4
    G['d'] = d; G['q'] = q
    G['b'] = d / 2 if b in (None, 'None', '') else mp.mpf(b)
    G['diag'] = (G['b'] == d / 2)
    G['al0'] = G['b'] / 4                       # alpha = l/2 + b/4  (= l/2 + q/2 on the diagonal)
    G['gsh'] = d / 2 - G['b'] / 2               # beta - alpha       (= q on the diagonal)
    G['pref'] = mp.gamma(d / 2) * mp.gamma(G['gsh']) / mp.gamma(G['b'] / 2)   # gs:balancedWheel prefactor (= Gamma(2q))
    G['G2q'] = mp.gamma(2 * q)
    G['psi0q'] = mp.digamma(q)
    G['cs'] = mp.digamma(1) + mp.digamma(2 * q)


def vec_integrand(a, nu, real):
    """returns list of NC values (complex if l complex) and an envelope for truncation"""
    q = G['q']
    z1 = a + mp.mpc(0, nu)
    if not G['diag']:                           # off-diagonal rim exponent: only W3, W4
        z3 = z1 + G['gsh']
        z2 = a - mp.mpc(0, nu); z4 = z2 + G['gsh']
        t = G['pref'] * mp.gamma(z1) / mp.gamma(z3) * mp.gamma(z2) / mp.gamma(z4)
        if real:
            t = mp.re(t)
        t3 = t ** 3
        return [t3, t3 * t, 0, 0, 0, 0], abs(t3)
    z3 = z1 + q
    g13 = mp.gamma(z1) / mp.gamma(z3)
    if real:
        z2 = mp.conj(z1); z4 = mp.conj(z3)
        t = G['G2q'] * (mp.re(g13) ** 2 + mp.im(g13) ** 2)
        P = {}
        for m in range(3):
            P[(m, 1)] = mp.psi(m, z1); P[(m, 3)] = mp.psi(m, z3)
            P[(m, 2)] = mp.conj(P[(m, 1)]); P[(m, 4)] = mp.conj(P[(m, 3)])
    else:
        z2 = a - mp.mpc(0, nu); z4 = z2 + q
        t = G['G2q'] * g13 * mp.gamma(z2) / mp.gamma(z4)
        P = {}
        for m in range(3):
            for i, z in ((1, z1), (2, z2), (3, z3), (4, z4)):
                P[(m, i)] = mp.psi(m, z)
    Re = lambda m, i, j: (P[(m, i)] + P[(m, j)]) / 2            # Re F(.+i nu) continued
    Im = lambda m, i, j: (P[(m, i)] - P[(m, j)]) / mp.mpc(0, 2)  # Im F(.+i nu) continued
    R0a, R0b = Re(0, 1, 2), Re(0, 3, 4)
    I0a, I0b = Im(0, 1, 2), Im(0, 3, 4)
    R1a, R1b = Re(1, 1, 2), Re(1, 3, 4)
    I1a, I1b = Im(1, 1, 2), Im(1, 3, 4)
    R2a, R2b = Re(2, 1, 2), Re(2, 3, 4)
    w1 = -G['psi0q'] + (R0a + R0b) / 2
    w2 = (R1a - R1b) / 8
    p = R0a + R0b
    h = I0a - I0b
    j = R1a - R1b
    k = I1a + I1b
    r = R2a + R2b
    E2 = -h * h / 2 - 5 * j / 8
    Kw = (G['cs'] - p) * E2 - h * k / 2 - 5 * r / 32
    t2 = t * t; t3 = t2 * t; t4 = t3 * t
    v = [t3, t4, 4 * t4 * w1, t3 * (w1 * w1 + w2 / 3), t2 * Kw, 3 * t3 * w1]
    if real:
        v = [mp.re(x) for x in v]
    env = abs(t3) * (1 + abs(w1)) ** 2 + abs(t2 * Kw)
    return v, env


def perspin(l, h0=mp.mpf(1) / 8, maxlev=6):
    """(1/pi) int_0^inf of the component vector at spin l (real or complex). returns (values, err_est, nodes)"""
    real = not isinstance(l, mp.mpc)
    extra = 10 + max(0, int(mp.log10(abs(l) + 1)))
    with mp.workdps(G['dps'] + extra):
        q = G['q']
        a = l / 2 + G['al0']
        s = abs(a)
        tol = mp.mpf(10) ** (-G['dps'] - 3)
        cache = {}

        def node(k, h):
            key = (k * h)
            if key in cache:
                return cache[key]
            u = k * h
            sh = mp.pi / 2 * mp.sinh(u)
            nu = s * mp.sinh(sh)
            w = s * mp.cosh(sh) * mp.pi / 2 * mp.cosh(u)
            v, env = vec_integrand(a, nu, real)
            cache[key] = ([x * w for x in v], env * w)
            return cache[key]
        # level 0: find truncation
        h = h0
        k = 0; small = 0; S = [0] * NC
        while True:
            vw, ew = node(k, h)
            fac = mp.mpf(1) / 2 if k == 0 else 1
            S = [S[i] + fac * vw[i] for i in range(NC)]
            scale = max(abs(x) for x in S) * h          # RELATIVE truncation (per-spin values can be tiny at huge l)
            if k > 8 and ew * h < tol * scale:
                small += 1
                if small >= 3:
                    break
            else:
                small = 0
            k += 1
            if k > 4000:
                raise RuntimeError('no truncation at l=%s' % l)
        kmax0 = k
        umax = kmax0 * h0
        prev = [x * h for x in S]
        err = None
        for lev in range(1, maxlev + 1):
            h = h0 / 2 ** lev
            K = int(umax / h)
            S = [0] * NC
            for kk in range(K + 1):
                vw, _ = node(kk, h)
                fac = mp.mpf(1) / 2 if kk == 0 else 1
                for i in range(NC):
                    S[i] += fac * vw[i]
            cur = [x * h for x in S]
            err = max(abs(cur[i] - prev[i]) for i in range(NC))
            prev = cur
            scale = max(abs(x) for x in cur)
            if err < tol * scale * 10 ** 2 and lev >= 2:
                break
        vals = [x / mp.pi for x in prev]
        return vals, err / max(abs(x) for x in prev), len(cache)     # relative step-halving difference


def mult(l):
    """d_l(d) continued in l (Gamma form; d_0 = 1 automatically)"""
    d = G['d']
    extra = 10 + max(0, int(mp.log10(abs(l) + 1)))
    with mp.workdps(G['dps'] + extra):
        if isinstance(l, mp.mpc) or l != 0:
            return (2 * l + d - 2) * mp.gammaprod([l + d - 2], [d - 1, l + 1])
        return mp.mpf(1)


def task(arg):
    kind, lre, lim = arg
    l = mp.mpf(lre) if lim == '0' else mp.mpc(lre, lim)
    st = time.time()
    vals, err, nn = perspin(l)
    m = mult(l) if G['d'] != 1 else (mp.mpf(1) if l in (0, 1) else mp.mpf(0))
    return arg, [str(m * x) for x in vals], str(err), nn, time.time() - st


def xnodes(L, hx, ulo, uhi):
    """x = L + L exp((pi/2) sinh u), u = k hx; returns list of (u, x, dx/du)"""
    out = []
    k = int(mp.floor(ulo / hx))
    while k * hx <= uhi:
        u = k * hx
        e = L * mp.exp(mp.pi / 2 * mp.sinh(u))
        out.append((u, L + e, e * mp.pi / 2 * mp.cosh(u)))
        k += 1
    return out


def ynodes(hy, ulo, uhi):
    """y = exp(u - exp(-u))"""
    out = []
    k = int(mp.floor(ulo / hy))
    while k * hy <= uhi:
        u = k * hy
        y = mp.exp(u - mp.exp(-u))
        out.append((u, y, y * (1 + mp.exp(-u))))
        k += 1
    return out


if __name__ == '__main__':
    out, d, dps, L = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else int(os.environ.get('SLURM_CPUS_PER_TASK', 3))
    b = sys.argv[6] if len(sys.argv) > 6 else None
    init(d, dps, b)
    t0 = time.time()
    hx = mp.mpf(1) / 16; hy = mp.mpf(1) / 16 if dps <= 45 else mp.mpf(1) / 32   # y-trapezoid error ~1e-48 at 1/16
    finite = (mp.mpf(d) == 1)
    tasks = []
    if finite:
        tasks = [('dir', '0', '0'), ('dir', '1', '0')]
    else:
        tasks = [('dir', str(l), '0') for l in range(L + 1)]   # includes f(L) for the Abel-Plana half term
        # x-integral nodes: lower limit where (x-L) < 10^-(dps+5); upper limit generous (checked by decay of contributions)
        Dd = (dps + 8) * mp.log(10)
        ulo = -mp.asinh(2 / mp.pi * (Dd + mp.log(L)))
        pl = 6 * G['gsh'] - G['d']                 # slowest spin-tail decay: f ~ x^(-1-pl) log^2 x  (pl = d/2 on the diagonal)
        uhi = mp.asinh(2 / mp.pi * Dd * mp.mpf('1.15') / pl)
        XN = xnodes(mp.mpf(L), hx, ulo, uhi)
        tasks += [('x', mp.nstr(x, dps + 15), '0') for (_, x, _) in XN]
        YN = ynodes(hy, -mp.log(Dd) - 1, mp.log(Dd / (2 * mp.pi)) + mp.mpf('0.7'))
        tasks += [('y', str(L), mp.nstr(y, dps + 15)) for (_, y, _) in YN]
    print('d', d, 'dps', dps, 'L', L, 'tasks', len(tasks), 'workers', workers, flush=True)
    with Pool(workers, initializer=init, initargs=(d, dps, b)) as pool:
        res = pool.map(task, tasks[::-1], chunksize=1)
    R = {tuple(a): (v, e, nn, tt) for a, v, e, nn, tt in res}
    json.dump(dict(d=d, dps=dps, L=L, hx=str(hx), hy=str(hy), seconds=time.time() - t0,
                   results=[[a[0], a[1], a[2], v, e, nn, tt] for a, (v, e, nn, tt) in R.items()]), open(out, 'w'), indent=0)
    # assemble
    vv = lambda a: [mp.mpmathify(x) for x in R[a][0]]
    tot = [mp.mpf(0)] * NC
    if finite:
        for l in ('0', '1'):
            tot = [tot[i] + vv(('dir', l, '0'))[i] for i in range(NC)]
        parts = {}
    else:
        for l in range(L):
            tot = [tot[i] + vv(('dir', str(l), '0'))[i] for i in range(NC)]
        direct = list(tot)
        fL = vv(('dir', str(L), '0'))
        # x integral, two step sizes (hx and 2hx subset) for an error estimate
        def xint(step):
            s = [mp.mpf(0)] * NC
            for (u, x, dxdu) in XN:
                kk = int(mp.nint(u / hx))
                if kk % step:
                    continue
                f = vv(('x', mp.nstr(x, dps + 15), '0'))
                s = [s[i] + f[i] * dxdu for i in range(NC)]
            return [x * hx * step for x in s]
        def yint(step):
            s = [mp.mpf(0)] * NC
            for (u, y, dydu) in YN:
                kk = int(mp.nint(u / hy))
                if kk % step:
                    continue
                f = vv(('y', str(L), mp.nstr(y, dps + 15)))
                s = [s[i] + mp.im(f[i]) / mp.expm1(2 * mp.pi * y) * dydu for i in range(NC)]
            return [x * hy * step for x in s]
        X1, X2 = xint(1), xint(2)
        Y1, Y2 = yint(1), yint(2)
        tail = [X1[i] + fL[i] / 2 - 2 * Y1[i] for i in range(NC)]
        tot = [tot[i] + tail[i] for i in range(NC)]
        parts = dict(direct=[str(x) for x in direct], xint=[str(x) for x in X1], xint_halfstep_diff=[mp.nstr(X1[i] - X2[i], 5) for i in range(NC)],
                     yint=[str(x) for x in Y1], yint_halfstep_diff=[mp.nstr(Y1[i] - Y2[i], 5) for i in range(NC)], fL=[str(x) for x in fL])
    q = G['q']
    A = mp.digamma(2 * q) + mp.digamma(1) - 2 * mp.digamma(q); U = mp.psi(2, q)
    if G['diag']:
        final = dict(threeQ=tot[0], Q=tot[0] / 3, P4=tot[1], L=tot[2], Z=tot[3], K=-A * U / 4 + tot[4] / 4, chk=tot[5])
    else:
        final = dict(W3=tot[0], W4=tot[1])
    maxerr = max(mp.mpmathify(R[a][1]) for a in R)
    J = json.load(open(out))
    J['final'] = {k: str(v) for k, v in final.items()}
    J['b'] = str(G['b'])
    J['parts'] = parts
    J['max_perspin_err'] = mp.nstr(maxerr, 5)
    json.dump(J, open(out, 'w'), indent=0)
    for k, v in final.items():
        print(k, mp.nstr(v, dps - 3))
    print('max per-spin step-halving diff', mp.nstr(maxerr, 5))
    if parts:
        print('x-int half-step diffs', parts['xint_halfstep_diff'])
        print('y-int half-step diffs', parts['yint_halfstep_diff'])
    print('seconds %.1f' % (time.time() - t0))
