#!/usr/bin/env python3
"""refcheck ROUTE B: the explicit residue (polygamma-hypergeometric) SERIES of the condensed note, taken literally:
   gs:seriesBase, gs:lambda, gs:etaTheta, gs:Fpolys, gs:QPseries, gs:Lseries, gs:Zseries, gs:rj, gs:Kpoly, gs:Kseries
   (no nu-integral, no Gamma-function spectral kernel, no b-/tau-derivatives).  Also the cancelled form gc:Kcancelled
   (gc:Knotation, gc:KregularPolynomial, gc:GaussDelta) of the K bracket as an algebra check.

   per spin l:  g_l(n) = summand of the inner n-series (n = 0,1,2,...), components
       [T^3 F3 (=3Q), -T^4 F4 (=P4), -T^4(4 mu1 F4 + F41) (=L), (1/9) T^3[(9mu1^2+3mu2)F3 + 6 mu1 F31 + F32] (=Z),
        M^2 S^2/8 - T^2 R/4 (=K + AU/4; bracket formed BEFORE summing), cancelled-form bracket (gc:Kcancelled)]
   OFF-DIAGONAL rim exponent b (only W3, W4): residue prefactor T = (x)_{l+n}(1-g)_n/((d/2)_{l+n} n!), x=b/2, g=d/2-x,
       lambda_m = psi_{m-1}(l+x+n) - psi_{m-1}(l+d/2+n) - (-1)^m chi_{m-1}(n;g) + (1+(-1)^m)psi_{m-1}(1) - psi_{m-1}(n+1)
       (the note's 'general balanced rim exponent' residue proof); W3 = sum T^3 F3, W4 = -sum T^4 F4.
   inner n-sum: Abel-Plana in continuous n (Pochhammers -> Gamma ratios, polygammas analytic in n):
       sum_{n>=0} g(n) = sum_{n<N} g(n) + g(N)/2 + int_N^inf g + i int_0^inf [g(N+iy)-g(N-iy)]/(e^{2pi y}-1) dy
       int_N^inf: x = N + exp(w - e^{-w}) (log-uniform at large x: the summand has singularities at every scale up to |l|,
       which a double-exponential map would push onto the real axis); trapezoid step 1/12 (check 1/6; 1/6 alone gave only ~1e-28).
   outer spin sum: sum_{l<L} d_l S(l) + Abel-Plana in continuous/complex l (inner sum done first).
   Work precision at a node: dps + log10(|l|+|n|) + 10.

usage:  routeB_residue.py OUT.json d DPS L [workers] [Nn] [b]
        routeB_residue.py spins OUT.json d DPS "l1 l2 re:im ..." [workers] [Nn] [b]
"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool

NC = 6
NAMES = ['W3', 'W4', 'L', 'Z', 'Kbr', 'Kbr_cancelled']
G = {}


def init(d, dps, b=None):
    mp.mp.dps = dps
    G['dps'] = dps
    d = mp.mpf(d); q = d / 4
    G['d'] = d; G['q'] = q
    G['b'] = d / 2 if b in (None, 'None', '') else mp.mpf(b)
    G['diag'] = (G['b'] == d / 2)
    with mp.workdps(dps + 20):
        xb = G['b'] / 2; gb = d / 2 - xb
        G['xb'] = xb; G['gb'] = gb
        G['psg'] = [mp.psi(k, gb) for k in range(4)]
        G['ps1mg'] = [mp.psi(k, 1 - gb) for k in range(4)]
        G['ps1'] = [mp.psi(k, 1) for k in range(4)]
        G['psq'] = [mp.psi(k, q) for k in range(4)]
        G['ps1mq'] = [mp.psi(k, 1 - q) for k in range(4)]
        G['cs'] = mp.digamma(1) + mp.digamma(2 * q)
        G['ps2q'] = mp.digamma(2 * q)
        G['M'] = mp.gamma(-q) * mp.gamma(2 * q) ** 2 / mp.gamma(3 * q)
        G['Tpref'] = mp.gamma(d / 2) / (mp.gamma(xb) * mp.gamma(1 - gb))      # (x)_m (1-g)_n / ((d/2)_m n!) Gamma-normalisation
        G['Spref'] = mp.gamma(3 * q) * mp.gamma(1 + q) / mp.gamma(2 * q)
        x = mp.pi * mp.cot(mp.pi * q)
        G['x'] = x; G['P'] = mp.pi ** 2
        G['Rinf'] = (mp.pi ** 2 + x ** 2) ** 2 / 2


def summand(l, n):
    """all components of the (l, n) term; l, n mpf or mpc"""
    q, d = G['q'], G['d']
    xb, gb = G['xb'], G['gb']
    m = l + n
    a = m + xb; b = m + d / 2                                  # = l+n+q, l+n+2q on the diagonal b = d/2
    n1g = n + 1 - gb; n1 = n + 1
    T = G['Tpref'] * mp.gamma(a) / mp.gamma(b) * mp.gamma(n1g) / mp.gamma(n1)
    sg = lambda k: (-1) ** k
    pa = [mp.psi(k, a) for k in range(4)]
    pb = [mp.psi(k, b) for k in range(4)]
    pn1g = [mp.psi(k, n1g) for k in range(4)]
    pn1 = [mp.psi(k, n1) for k in range(4)]
    chi = [sg(k) * pn1g[k] + G['psg'][k] - sg(k) * G['ps1mg'][k] for k in range(4)]          # chi_k(n;g) = psi_k(g-n)
    lam = [None] + [pa[j - 1] - pb[j - 1] - sg(j) * chi[j - 1] + (1 + sg(j)) * G['ps1'][j - 1] - pn1[j - 1] for j in range(1, 5)]
    l1, l2, l3, l4 = lam[1], lam[2], lam[3], lam[4]
    F3 = mp.mpf(9) / 2 * l1 ** 2 + mp.mpf(3) / 2 * l2
    F4 = mp.mpf(32) / 3 * l1 ** 3 + 8 * l1 * l2 + mp.mpf(2) / 3 * l3
    T2 = T * T; T3 = T2 * T; T4 = T3 * T
    if not G['diag']:
        return [T3 * F3, -T4 * F4, 0, 0, 0, 0]
    eta = [None] + [(pa[k] + sg(k) * chi[k]) / 2 for k in range(1, 4)]
    theta = [None] + [(pa[k + 1] - sg(k) * chi[k + 1]) / 4 for k in range(1, 3)]
    mu1 = (pa[0] - G['psq'][0] + pn1g[0] - G['ps1mq'][0]) / 2
    mu2 = (pa[1] - G['psq'][1] + pn1g[1] - G['ps1mq'][1]) / 4
    F31 = 9 * l1 * eta[1] + mp.mpf(3) / 2 * eta[2]
    F32 = 9 * eta[1] ** 2 + 9 * l1 * theta[1] + mp.mpf(3) / 2 * theta[2]
    F41 = 32 * l1 ** 2 * eta[1] + 8 * eta[1] * l2 + 8 * l1 * eta[2] + mp.mpf(2) / 3 * eta[3]
    S = G['Spref'] * mp.gamma(b) / mp.gamma(m + 3 * q) * mp.gamma(n1) / mp.gamma(n + 1 + q)    # (2q)_m n! / ((3q)_m (1+q)_n)
    r = [lam[j + 1] / 2 + pb[j] + pn1[j] - (1 - sg(j)) * G['ps1'][j] for j in range(4)]
    cs = G['cs']
    R = ((r[0] - cs) / 2 * (l1 ** 3 + 3 * l1 * l2 + l3) + mp.mpf(3) * r[1] / 4 * (l1 ** 2 + l2) - (l1 * r[2] + r[3]) / 4
         - l1 ** 4 / 12 + l1 ** 2 * l2 / 8 + 7 * l1 * l3 / 24 + l2 ** 2 / 8 + l4 / 12)
    Kbr = G['M'] ** 2 * S ** 2 / 8 - T2 * R / 4
    # cancelled form gc:Kcancelled with gc:KregularPolynomial (independent algebra; equals Kbr iff R = Rinf + P)
    x, P = G['x'], G['P']
    D = [None] + [pa[j - 1] - pb[j - 1] + pn1g[j - 1] - pn1[j - 1] for j in range(1, 5)]
    J = [None] + [pb[j] + pn1[j] for j in range(1, 4)]
    H = (pb[0] - G['ps2q']) + (pn1[0] - G['ps1'][0])
    D1, D2, D3, D4 = D[1], D[2], D[3], D[4]
    PP = (D1 ** 4 / 6 - 2 * x * D1 ** 3 / 3 + mp.mpf(5) / 4 * D1 ** 2 * D2 + mp.mpf(3) / 4 * D1 ** 2 * J[1]
          - (13 * P / 12 + x ** 2 / 4) * D1 ** 2
          - 5 * x / 2 * D1 * D2 + mp.mpf(5) / 12 * D1 * D3 - mp.mpf(3) / 2 * x * D1 * J[1] - D1 * J[2] / 4 + (4 * P * x / 3 + x ** 3) * D1
          + D2 ** 2 / 2 + mp.mpf(3) / 4 * D2 * J[1] + (-11 * P / 12 + x ** 2 / 4) * D2 - 5 * x / 12 * D3 - D4 / 24
          + H * (D1 ** 3 / 2 - mp.mpf(3) / 2 * x * D1 ** 2 + mp.mpf(3) / 2 * D1 * D2 - P * D1 - mp.mpf(3) / 2 * x * D2 + D3 / 2)
          - P / 2 * J[1] + x / 4 * J[2] - J[3] / 4)
    rr = lambda c: mp.gamma(c) ** 2 / (mp.gamma(c - q) * mp.gamma(c + q))
    Kc = T2 / 4 * (G['Rinf'] * (rr(m + 2 * q) ** 2 * rr(n + 1) ** 2 - 1) - PP)
    return [T3 * F3, -T4 * F4, -T4 * (4 * mu1 * F4 + F41), T3 * ((9 * mu1 ** 2 + 3 * mu2) * F3 + 6 * mu1 * F31 + F32) / 9, Kbr, Kc]


def g_at(l, n):
    extra = 10 + max(0, int(mp.log10(abs(l) + abs(n) + 1)))
    with mp.workdps(G['dps'] + extra):
        v = summand(l, n)
    return v


def slow_n_exponent():
    """smallest p with summand ~ n^{-1-p} at large n (logs allowed)"""
    g = G['gb']
    p = 6 * g - 1                                  # W3 / Z  (T ~ n^{-2g})
    if G['diag']:
        p = min(p, 4 * G['q'])                     # K bracket after cancellation ~ T^2 log n / n
    return p


def inner_sum(l, N, hw=None, hy=None):
    """sum_{n>=0} g_l(n) by Abel-Plana; returns (values, diagnostics)"""
    real = not isinstance(l, mp.mpc)
    dps = G['dps']
    if hw is None:
        hw = mp.mpf(1) / 12 if dps <= 45 else mp.mpf(1) / 16       # log-map trapezoid error ~ exp(-2 pi 1.7/hw)
    if hy is None:
        hy = mp.mpf(1) / 16 if dps <= 45 else mp.mpf(1) / 32
    Dd = (dps + 8) * mp.log(10)
    tot = [mp.mpf(0)] * NC
    for n in range(N):
        v = g_at(l, mp.mpf(n))
        tot = [tot[i] + v[i] for i in range(NC)]
    fN = g_at(l, mp.mpf(N))
    # int_N^inf: x = N + exp(w - e^{-w})
    p = slow_n_exponent()
    wlo = -mp.log(Dd) - mp.mpf('0.5')
    whi = mp.log(abs(l) + N + 1) + Dd * mp.mpf('1.15') / p + 6
    X = [[mp.mpf(0)] * NC, [mp.mpf(0)] * NC]
    k = int(mp.floor(wlo / hw)); nx = 0
    while k * hw <= whi:
        w = k * hw
        e = mp.exp(w - mp.exp(-w))
        v = g_at(l, N + e)
        wt = e * (1 + mp.exp(-w))
        X[0] = [X[0][i] + v[i] * wt for i in range(NC)]
        if k % 2 == 0:
            X[1] = [X[1][i] + v[i] * wt for i in range(NC)]
        k += 1; nx += 1
    X = [[x * hw for x in X[0]], [x * 2 * hw for x in X[1]]]
    # y-integral: y = exp(u - e^{-u})
    Y = [[mp.mpf(0)] * NC, [mp.mpf(0)] * NC]
    k = int(mp.floor((-mp.log(Dd) - 1) / hy)); ny = 0
    uhi = mp.log(Dd / (2 * mp.pi)) + mp.mpf('0.7')
    while k * hy <= uhi:
        u = k * hy
        y = mp.exp(u - mp.exp(-u))
        wt = y * (1 + mp.exp(-u))
        vp = g_at(l, mp.mpc(N, y))
        if real:
            c = [-2 * mp.im(vp[i]) for i in range(NC)]
        else:
            vm = g_at(l, mp.mpc(N, -y))
            c = [mp.mpc(0, 1) * (vp[i] - vm[i]) for i in range(NC)]
        e = mp.expm1(2 * mp.pi * y)
        Y[0] = [Y[0][i] + c[i] / e * wt for i in range(NC)]
        if k % 2 == 0:
            Y[1] = [Y[1][i] + c[i] / e * wt for i in range(NC)]
        k += 1; ny += 1
    Y = [[x * hy for x in Y[0]], [x * 2 * hy for x in Y[1]]]
    tot = [tot[i] + fN[i] / 2 + X[0][i] + Y[0][i] for i in range(NC)]
    sc = max(abs(tot[0]), abs(tot[1]))
    diag = dict(xdiff=max(abs(X[0][i] - X[1][i]) for i in range(NC)) / sc, ydiff=max(abs(Y[0][i] - Y[1][i]) for i in range(NC)) / sc,
                nx=nx, ny=ny)
    return tot, diag


def mult(l):
    d = G['d']
    extra = 10 + max(0, int(mp.log10(abs(l) + 1)))
    with mp.workdps(G['dps'] + extra):
        if isinstance(l, mp.mpc) or l != 0:
            return (2 * l + d - 2) * mp.gammaprod([l + d - 2], [d - 1, l + 1])
        return mp.mpf(1)


def task(arg):
    kind, lre, lim, Nn = arg
    l = mp.mpf(lre) if lim == '0' else mp.mpc(lre, lim)
    st = time.time()
    with mp.workdps(G['dps'] + 10 + max(0, int(mp.log10(abs(l) + 1)))):
        vals, diag = inner_sum(l, Nn)
    if G['d'] == 1:
        m = mp.mpf(1) if l in (0, 1) else mp.mpf(0)
    else:
        m = mult(l)
    return arg, [str(m * x) for x in vals], [str(x) for x in vals], {k: (mp.nstr(v, 5) if not isinstance(v, int) else v) for k, v in diag.items()}, time.time() - st


def x_nodes(L, h, ulo, uhi):
    out = []
    k = int(mp.floor(ulo / h))
    while k * h <= uhi:
        u = k * h
        e = L * mp.exp(mp.pi / 2 * mp.sinh(u))
        out.append((k, L + e, e * mp.pi / 2 * mp.cosh(u)))
        k += 1
    return out


def y_nodes(h, ulo, uhi):
    out = []
    k = int(mp.floor(ulo / h))
    while k * h <= uhi:
        u = k * h
        y = mp.exp(u - mp.exp(-u))
        out.append((k, y, y * (1 + mp.exp(-u))))
        k += 1
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'spins':
        out, d, dps, spins = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5].split()
        workers = int(sys.argv[6]) if len(sys.argv) > 6 else 3
        Nn = int(sys.argv[7]) if len(sys.argv) > 7 else 8
        b = sys.argv[8] if len(sys.argv) > 8 else None
        init(d, dps, b)
        tasks = [('spin', s.split(':')[0], s.split(':')[1] if ':' in s else '0', Nn) for s in spins]
        with Pool(workers, initializer=init, initargs=(d, dps, b)) as pool:
            res = pool.map(task, tasks, chunksize=1)
        json.dump(dict(d=d, dps=dps, Nn=Nn, b=str(G['b']), results=[[a[1], a[2], vm, v, dg, tt] for a, vm, v, dg, tt in res]), open(out, 'w'), indent=0)
        for a, vm, v, dg, tt in res:
            print(a[1], a[2], [s[:24] for s in v], dg, '%.1fs' % tt, flush=True)
        sys.exit()
    out, d, dps, L = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else int(os.environ.get('SLURM_CPUS_PER_TASK', 3))
    Nn = int(sys.argv[6]) if len(sys.argv) > 6 else 8
    b = sys.argv[7] if len(sys.argv) > 7 else None
    init(d, dps, b)
    t0 = time.time()
    h = mp.mpf(1) / 16
    hyo = h if dps <= 45 else h / 2
    finite = (mp.mpf(d) == 1)
    Dd = (dps + 8) * mp.log(10)
    pl = 6 * G['gb'] - G['d']          # slowest spin decay f ~ l^{-1-pl} (W3, Z)
    if finite:
        tasks = [('dir', '0', '0', Nn), ('dir', '1', '0', Nn)]
    else:
        tasks = [('dir', str(l), '0', Nn) for l in range(L + 1)]
        XN = x_nodes(mp.mpf(L), h, -mp.asinh(2 / mp.pi * (Dd + mp.log(L))), mp.asinh(2 / mp.pi * Dd * mp.mpf('1.15') / pl))
        tasks += [('x', mp.nstr(x, dps + 15), '0', Nn) for (_, x, _) in XN]
        YN = y_nodes(hyo, -mp.log(Dd) - 1, mp.log(Dd / (2 * mp.pi)) + mp.mpf('0.7'))
        tasks += [('y', str(L), mp.nstr(y, dps + 15), Nn) for (_, y, _) in YN]
    print('d', d, 'b', mp.nstr(G['b'], 10), 'dps', dps, 'L', L, 'Nn', Nn, 'tasks', len(tasks), 'workers', workers, flush=True)
    with Pool(workers, initializer=init, initargs=(d, dps, b)) as pool:
        res = pool.map(task, tasks[::-1], chunksize=1)          # huge/complex spins first
    R = {tuple(a[:3]): (vm, v, dg, tt) for a, vm, v, dg, tt in res}
    vv = lambda a: [mp.mpmathify(x) for x in R[a][0]]
    tot = [mp.mpf(0)] * NC
    parts = {}
    if finite:
        for l in ('0', '1'):
            tot = [tot[i] + vv(('dir', l, '0'))[i] for i in range(NC)]
    else:
        for l in range(L):
            tot = [tot[i] + vv(('dir', str(l), '0'))[i] for i in range(NC)]
        direct = list(tot)
        fL = vv(('dir', str(L), '0'))
        def xint(step):
            s = [mp.mpf(0)] * NC
            for (k, x, w) in XN:
                if k % step:
                    continue
                f = vv(('x', mp.nstr(x, dps + 15), '0'))
                s = [s[i] + f[i] * w for i in range(NC)]
            return [x * h * step for x in s]
        def yint(step):
            s = [mp.mpf(0)] * NC
            for (k, y, w) in YN:
                if k % step:
                    continue
                f = vv(('y', str(L), mp.nstr(y, dps + 15)))
                s = [s[i] + mp.im(f[i]) / mp.expm1(2 * mp.pi * y) * w for i in range(NC)]
            return [x * hyo * step for x in s]
        X1, X2 = xint(1), xint(2)
        Y1, Y2 = yint(1), yint(2)
        tail = [X1[i] + fL[i] / 2 - 2 * Y1[i] for i in range(NC)]
        tot = [tot[i] + tail[i] for i in range(NC)]
        parts = dict(direct=[str(x) for x in direct], xint=[str(x) for x in X1], xint_halfstep_diff=[mp.nstr(X1[i] - X2[i], 5) for i in range(NC)],
                     yint=[str(x) for x in Y1], yint_halfstep_diff=[mp.nstr(Y1[i] - Y2[i], 5) for i in range(NC)], fL=[str(x) for x in fL])
    q = G['q']
    A = mp.digamma(2 * q) + mp.digamma(1) - 2 * mp.digamma(q); U = mp.psi(2, q)
    if G['diag']:
        final = dict(threeQ=tot[0], Q=tot[0] / 3, P4=tot[1], L=tot[2], Z=tot[3], K=-A * U / 4 + tot[4], K_cancelled=-A * U / 4 + tot[5])
    else:
        final = dict(W3=tot[0], W4=tot[1])
    worst = dict(xdiff=max(mp.mpf(R[a][2]['xdiff']) for a in R), ydiff=max(mp.mpf(R[a][2]['ydiff']) for a in R))
    json.dump(dict(d=d, b=str(G['b']), dps=dps, L=L, Nn=Nn, h=str(h), seconds=time.time() - t0, final={k: str(v) for k, v in final.items()}, parts=parts,
                   worst_inner_rel_halfstep={k: mp.nstr(v, 5) for k, v in worst.items()},
                   results=[[a[0], a[1], a[2], vm, v, dg, tt] for a, (vm, v, dg, tt) in R.items()]), open(out, 'w'), indent=0)
    for k, v in final.items():
        print(k, mp.nstr(v, dps - 3))
    print('worst inner (n-sum) relative half-step diffs', {k: mp.nstr(v, 3) for k, v in worst.items()})
    if parts:
        print('x-int half-step diffs', parts['xint_halfstep_diff'])
        print('y-int half-step diffs', parts['yint_halfstep_diff'])
    print('seconds %.1f' % (time.time() - t0))
