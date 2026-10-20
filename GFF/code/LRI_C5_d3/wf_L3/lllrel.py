"""Integer-relation search by FLINT LLL, with a Gram-Schmidt lower bound for negative results.
Lattice rows (e_i | round(C x_i)), C = 0.1*10^dig/max|x|.  Any exact relation m gives a lattice vector of norm
<= |m|_inf*sqrt(n)*sqrt(1+n/4); every nonzero lattice vector has norm >= min_i |b_i*|.  Hence 'no relation with
|m|_inf < bound', bound = min|b_i*|/sqrt(n(1+n/4)), up to the stated accuracy of the inputs (not interval-certified)."""
import flint, mpmath as mp
LOG = []
def relation(name, target, basis, names, dig, quiet=False):
    with mp.workdps(dig + 20):
        vec = [mp.mpf(target)] + [mp.mpf(b) for b in basis]
        n = len(vec)
        xm = max(abs(v) for v in vec)
        C = mp.mpf(10) ** dig / xm / 10
        rows = []
        for i, v in enumerate(vec):
            r = [0] * n; r[i] = 1
            rows.append(r + [int(mp.nint(C * v))])
        R = flint.fmpz_mat(rows).lll().tolist()
        R = [[int(x) for x in r] for r in R]
        # Gram-Schmidt norms
        with mp.workdps(60):
            Bm = [[mp.mpf(x) for x in r] for r in R]
            Bs = []
            norms = []
            for b in Bm:
                v = b[:]
                for u, nu in zip(Bs, norms):
                    mu = mp.fsum(x * y for x, y in zip(b, u)) / nu
                    v = [x - mu * y for x, y in zip(v, u)]
                Bs.append(v); norms.append(mp.fsum(x * x for x in v))
            gsmin = mp.sqrt(min(norms))
            bound = gsmin / mp.sqrt(n * (1 + mp.mpf(n) / 4))
        best = None
        for r in R:
            m = r[:n]
            if m[0] == 0:
                continue
            res = abs(mp.fsum(a * b for a, b in zip(m, vec))) / max(abs(a * b) for a, b in zip(m, vec) if a)
            mx = max(abs(a) for a in m)
            if best is None or res < best[0]:
                best = (res, mx, m)
        res, mx, m = best
        hyg = n * mp.log10(max(mx, 1)) <= dig - 10
        ok = res < mp.mpf(10) ** (-(dig - 5)) and hyg
        if ok:
            msg = '%s RELATION (n=%d, max|c|=%d, rel.res %s): %s' % (name, n, mx, mp.nstr(res, 3),
                  ' + '.join('(%s)*%s' % (c, nm) for c, nm in zip(m, ['T'] + names) if c))
        else:
            msg = '%s: none (n=%d, %d digits; no relation with max|c| < %s; best LLL candidate max|c|=%s res %s)' % (
                name, n, dig, mp.nstr(bound, 3), mp.nstr(mp.mpf(mx), 3), mp.nstr(res, 2))
    LOG.append(msg)
    if not quiet:
        print(msg, flush=True)
    return (m if ok else None), bound
def tens(objs, els):
    b, nm = [], []
    for on, o in objs:
        for en, e in els:
            b.append(o * e); nm.append(on + '*' + en)
    return b, nm
