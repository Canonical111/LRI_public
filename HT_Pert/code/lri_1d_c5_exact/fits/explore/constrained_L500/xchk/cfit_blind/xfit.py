#!/usr/bin/env python
"""Blind high-precision tail fits of exact finite-cutoff C_n(Lambda), 1d LRI HT.

Model for order n (top log power at Lambda^{-1/2} is n-2):
  C_n(L) = I + sum_{j=1..J} L^{-j/2} sum_{k=0..kmax(j)} a_{jk} log^k L
  kmax(1) = n-2, kmax(j>=2) = ksub.
Intercept I: 'fixed' (exact value subtracted) or 'free' (column of ones).
Top coefficient a_{1,n-2}: 'free' (column) or 'fixed' (deferred: we solve the
same least-squares problem for two right-hand sides, y and f = L^{-1/2} log^{n-2} L,
so that for any value t of the top coefficient the fit of y - t f has
coefficients c(y) - t c(f) and residuals r(y) - t r(f)).

Least squares: Householder QR in mpmath (dps given per task) after scaling every
column to unit 2-norm.  Data are float64 values converted exactly to mpf.
"""
import sys, os, json, time
import numpy as np
import mpmath as mp
from mpmath import mpf

DATA = {}


def load_data(datadir):
    a = np.load(os.path.join(datadir, 'c4_1d_L2000.npz'))
    b = np.load(os.path.join(datadir, 'c5_1d_L500.npz'))
    L4 = a['even_L'].astype(np.int64)
    d = {}
    d['2'] = (L4, a['C2'][4 * L4])
    d['3'] = (L4, a['C3'][4 * L4])
    d['4'] = (L4, a['even_C4Dconn'])
    L5 = b['even_L'].astype(np.int64)
    d['5'] = (L5, b['even_C5Dconn'])
    for k, (L, v) in d.items():
        assert np.all(np.isfinite(v)), k
        assert np.all(np.diff(L) == 2) and L[0] == 2
    return d


def exact_intercept(n):
    if n == 2:
        return (mp.pi + 4 * mp.log(2)) / 9
    if n == 3:
        return mpf('-3.71985632290183342249')
    if n == 4:
        return mpf('45.42488010356')
    raise ValueError(n)


def householder_lstsq(cols, rhss):
    """cols: list of n columns (lists of mpf, length m); rhss: list of RHS lists.
    Returns (coef list per rhs, Rinv-based unit-noise sigma per coefficient)."""
    n = len(cols)
    m = len(cols[0])
    sc = [mp.sqrt(mp.fdot(c, c)) for c in cols]
    R = [[v / s for v in c] for c, s in zip(cols, sc)]
    As = [list(c) for c in R]
    B = [list(r) for r in rhss]
    diag = [None] * n
    for k in range(n):
        sub = R[k][k:]
        nrm = mp.sqrt(mp.fdot(sub, sub))
        if nrm == 0:
            raise ZeroDivisionError('rank deficient')
        alpha = -nrm if sub[0] >= 0 else nrm
        v = list(sub)
        v[0] = v[0] - alpha
        vv = mp.fdot(v, v)
        diag[k] = alpha
        R[k][k] = alpha
        for i in range(k + 1, m):
            R[k][i] = mpf(0)
        for j in range(k + 1, n):
            cj = R[j]
            t = 2 * mp.fdot(v, cj[k:]) / vv
            cj[k:] = [c - t * vi for c, vi in zip(cj[k:], v)]
        for bj in B:
            t = 2 * mp.fdot(v, bj[k:]) / vv
            bj[k:] = [c - t * vi for c, vi in zip(bj[k:], v)]
    # upper triangular U[i][j] = R[j][i]
    def U(i, j):
        return R[j][i]
    coefs = []
    for bj in B:
        z = [mpf(0)] * n
        for i in range(n - 1, -1, -1):
            s = bj[i] - mp.fsum(U(i, j) * z[j] for j in range(i + 1, n))
            z[i] = s / U(i, i)
        coefs.append([z[i] / sc[i] for i in range(n)])
    # Rinv (upper triangular) for unit-noise covariance (A_scaled^T A_scaled)^-1 = Rinv Rinv^T
    Rinv = [[mpf(0)] * n for _ in range(n)]
    for j in range(n):
        Rinv[j][j] = 1 / U(j, j)
        for i in range(j - 1, -1, -1):
            s = mp.fsum(U(i, l) * Rinv[l][j] for l in range(i + 1, j + 1))
            Rinv[i][j] = -s / U(i, i)
    sig = [mp.sqrt(mp.fsum(Rinv[i][j] ** 2 for j in range(i, n))) / sc[i] for i in range(n)]
    # crude condition estimate of scaled matrix: max|diag R| / min|diag R| (lower bound)
    dabs = [abs(d) for d in diag]
    cond_lb = max(dabs) / min(dabs)
    # pseudo-inverse rows p_i (coef_i = p_i . y) for requested indices
    def prow(i):
        u = [Rinv[i][j] for j in range(n)]          # row i of Rinv = R^-T e_i
        z = [mp.fsum(Rinv[a][b] * u[b] for b in range(a, n)) for a in range(n)]
        return [mp.fsum(As[a][r] * z[a] for a in range(n)) / sc[i] for r in range(m)]
    return coefs, sig, cond_lb, prow


def run_task(t):
    t0 = time.time()
    mp.mp.dps = t['dps']
    n = t['n']
    L, v = DATA[str(n)]
    sel = (L >= t['lo']) & (L <= t['hi'])
    Ls = [int(x) for x in L[sel]]
    ys = [mpf(float(x)) for x in v[sel]]
    xs = [mpf(x) for x in Ls]
    lg = [mp.log(x) for x in xs]
    rt = [1 / mp.sqrt(x) for x in xs]
    if t['icpt'] == 'fixed':
        I = exact_intercept(n)
        ys = [y - I for y in ys]
    cols, labels = [], []
    if t['icpt'] == 'free':
        cols.append([mpf(1)] * len(xs)); labels.append('I')
    top = n - 2
    for j in range(1, t['J'] + 1):
        if 'kcaps' in t:
            kmax = t['kcaps'][j - 1]
        else:
            kmax = top if j == 1 else t['ksub']
        pw = [r ** j for r in rt]
        for k in range(kmax + 1):
            if j == 1 and k == top and t['top'] == 'fixed':
                continue
            cols.append([p * l ** k for p, l in zip(pw, lg)]); labels.append('j%dk%d' % (j, k))
    rhss = [ys]
    if t['top'] == 'fixed':
        f = [r * l ** top for r, l in zip(rt, lg)]
        rhss.append(f)
    coefs, sig, cond_lb, prow = householder_lstsq(cols, rhss)
    out = dict(t)
    out.update(npts=len(xs), ncols=len(cols), labels=labels, cond_lb=mp.nstr(cond_lb, 3))
    out['coef_y'] = {lab: mp.nstr(c, 30) for lab, c in zip(labels, coefs[0])}
    out['sig_unit'] = {lab: mp.nstr(s, 6) for lab, s in zip(labels, sig)}
    def resid(rhs, cf):
        return [r - mp.fsum(c * col[i] for c, col in zip(cf, cols)) for i, r in enumerate(rhs)]
    ry = resid(ys, coefs[0])
    if t['top'] == 'fixed':
        out['coef_f'] = {lab: mp.nstr(c, 30) for lab, c in zip(labels, coefs[1])}
        rf = resid(rhss[1], coefs[1])
        out['res_y'] = [float(r) for r in ry]
        out['res_f'] = [float(r) for r in rf]
        # stats for the candidate top values
        cand = {}
        for name, tv in t.get('top_cands', {}).items():
            tv = mpf(tv)
            rr = [a - tv * b for a, b in zip(ry, rf)]
            cc = {lab: mp.nstr(a - tv * b, 20) for lab, a, b in zip(labels, coefs[0], coefs[1])}
            cand[name] = dict(top=mp.nstr(tv, 20), coef=cc,
                              maxres=float(max(abs(r) for r in rr)),
                              rms=float(mp.sqrt(mp.fsum(r * r for r in rr) / len(rr))))
        out['cands'] = cand
    else:
        out['maxres'] = float(max(abs(r) for r in ry))
        out['rms'] = float(mp.sqrt(mp.fsum(r * r for r in ry) / len(ry)))
        out['res_y'] = ['%.3e' % float(r) for r in ry]
    plab = 'I' if 'I' in labels else ('j1k%d' % top if ('j1k%d' % top) in labels else None)
    if plab is not None:
        p = prow(labels.index(plab))
        out['p_lab'] = plab
        out['p'] = [float(x) for x in p]
        # self-check: p . y reproduces the coefficient
        out['p_check'] = float(mp.fsum(a * b for a, b in zip(p, ys)) - coefs[0][labels.index(plab)])
    out['Lfirst'], out['Llast'] = Ls[0], Ls[-1]
    out['secs'] = round(time.time() - t0, 2)
    return out


def init(datadir):
    global DATA
    DATA = load_data(datadir)


def main():
    import multiprocessing as mpc
    taskfile, outfile, datadir = sys.argv[1], sys.argv[2], sys.argv[3]
    nproc = int(sys.argv[4]) if len(sys.argv) > 4 else mpc.cpu_count()
    tasks = [json.loads(l) for l in open(taskfile) if l.strip()]
    # longest first: cost ~ npts * ncols^2
    def cost(t):
        npts = (min(t['hi'], 2000 if t['n'] < 5 else 500) - t['lo']) // 2 + 1
        nc = (sum(k + 1 for k in t['kcaps']) if 'kcaps' in t else t['J'] * (t['ksub'] + 1)) + 3
        return npts * nc * nc * t['dps']
    tasks.sort(key=cost, reverse=True)
    print('tasks', len(tasks), 'nproc', nproc, flush=True)
    t0 = time.time()
    with mpc.Pool(nproc, initializer=init, initargs=(datadir,)) as pool, open(outfile, 'w') as fo:
        for i, r in enumerate(pool.imap_unordered(run_task, tasks)):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            if i % 20 == 0:
                print(i, r['id'], r['secs'], round(time.time() - t0, 1), flush=True)
    print('done', round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
