import mpmath as mp
LOG = []
def test(name, target, basis, names, dig, maxcoeff=None, quiet=False):
    """Hygiene: n*log10(maxcoeff) <= dig-10; relation accepted only if residual is at noise level (1e-(dig-5))."""
    with mp.workdps(dig + 5):
        vec = [mp.mpf(target)] + [mp.mpf(b) for b in basis]
        n = len(vec)
        mc = maxcoeff or int(mp.floor(mp.mpf(10) ** (mp.mpf(dig - 10) / n)))
        rel = mp.pslq(vec, tol=mp.mpf(10) ** (-(dig - 3)), maxcoeff=mc, maxsteps=5 * 10 ** 6)
        if rel and rel[0] != 0:
            res = abs(mp.fsum(a * b for a, b in zip(rel, vec))) / max(abs(a * b) for a, b in zip(rel, vec))
            ok = res < mp.mpf(10) ** (-(dig - 5))
            msg = '%s %s (rel. residual %s, n=%d, bound %d): %s' % (name, 'RELATION' if ok else 'rejected', mp.nstr(res, 3), n, mc,
                   ' + '.join('(%s)*%s' % (c, nm) for c, nm in zip(rel, ['T'] + names) if c))
        else:
            msg = '%s: none  (n=%d, |c|<=%d, %d digits)' % (name, n, mc, dig)
            rel = None
    LOG.append(msg)
    if not quiet: print(msg, flush=True)
    return rel
def tens(objs, els):
    b, nm = [], []
    for on, o in objs:
        for en, e in els:
            b.append(o * e); nm.append(on + '*' + en)
    return b, nm
