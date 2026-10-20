"""Integer-relation search via FLINT LLL, with the hygiene rule of the task:
   a hit counts only if n*log10(max|c|) <= digits-10, the residual is at noise level, and it reappears at a second precision.
For a negative result we report the LLL Gram-Schmidt bound: any integer relation a (with |a.x| < 10^-digits) has
Euclidean norm >= min_i |b_i*| of the reduced basis (up to the small scale term), hence max|a_i| >= that / sqrt(n)."""
import mpmath as mp
from flint import fmpz_mat

def lll_relation(vals, digits, names=None, extra=0):
    """vals: list of mpf (vals[0] = target).  digits: trusted digits.  Returns dict."""
    n = len(vals)
    D = digits - 2
    with mp.workdps(digits + 40):
        S = mp.mpf(10) ** D
        rows = []
        for i, v in enumerate(vals):
            r = [0] * n + [int(mp.nint(S * v))]
            r[i] = 1
            rows.append(r)
    M = fmpz_mat(rows)
    R = M.lll()
    best = None
    internal = []
    rl = R.tolist()
    with mp.workdps(digits + 40):
        for row in rl:
            a = [int(x) for x in row[:n]]
            if all(x == 0 for x in a):
                continue
            res = mp.fsum(ai * vi for ai, vi in zip(a, vals))
            scale = max(abs(ai * vi) for ai, vi in zip(a, vals) if ai != 0)
            rel = abs(res) / scale
            mx = max(abs(x) for x in a)
            cand = dict(coeffs=a, rel_residual=rel, maxcoeff=mx, target_coeff=a[0])
            if rel < mp.mpf(10) ** (-(digits - 12)):
                if a[0] == 0:
                    internal.append(cand)
                elif best is None or mx < best['maxcoeff']:
                    best = cand
        # Gram-Schmidt norms (floating, in mpmath) of the reduced basis
        B = [[mp.mpf(int(x)) for x in row] for row in rl]
        bstar = []
        for i in range(len(B)):
            v = list(B[i])
            for j in range(i):
                mu = mp.fsum(a * b for a, b in zip(B[i], bstar[j])) / mp.fsum(b * b for b in bstar[j])
                v = [a - mu * b for a, b in zip(v, bstar[j])]
            bstar.append(v)
        gs = [mp.sqrt(mp.fsum(x * x for x in v)) for v in bstar]
        bound = min(gs)
    out = dict(n=n, digits=digits, allowed_maxcoeff=float(mp.mpf(10) ** (mp.mpf(digits - 10) / n)),
               norm_bound=float(bound), maxcoeff_bound=float(bound / mp.sqrt(n)))
    if best is not None:
        ok = best['target_coeff'] != 0 and n * mp.log10(max(best['maxcoeff'], 2)) <= digits - 10
        out.update(found=True, admissible=bool(ok), **{k: (mp.nstr(v, 3) if k == 'rel_residual' else v) for k, v in best.items()})
        if names:
            out['relation'] = ' + '.join('%d*%s' % (c, nm) for c, nm in zip(best['coeffs'], names) if c)
    else:
        out['found'] = False
    if internal:
        out['internal_relations'] = [(' + '.join('%d*%s' % (c, nm) for c, nm in zip(r['coeffs'], names) if c) if names else r['coeffs']) for r in internal[:3]]
    return out
