"""Zero-mode paths and chi line patterns (copied from lri_1d_c4_exact/c4lib1d.py, which copied them from the 2D
c4_exact code of the HT2dPert session; pattern enumeration made recursive with leg budgets for K = 5).

Patterns are dicts over ALL pairs (i, j), i < j (zero entries included), as in C4P."""
import functools
from fractions import Fraction as Fr
from math import comb, factorial

from .common import MAXLEGS


def zero_mode_paths(p, zlegs):
    """Closed paths p = r_0 -> r_1 -> ... -> r_K = p, vertex i applying :Z^{zlegs[i]}: (normal ordered).
    Returns [(r_1..r_{K-1}, exact amplitude)], amplitude = prod C(k_i, j_i) * prod_{i<K} r_i! / prod m_i!."""
    K = len(zlegs)
    out = []

    def rec(i, r_prev, rs, cnum, mden):
        k = zlegs[i]
        targets = [p] if i == K - 1 else range(max(0, r_prev - k), r_prev + k + 1)
        for r in targets:
            d = r - r_prev
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2              # creations
            m = r_prev - (k - j)          # after the annihilations
            if m < 0:
                continue
            c = cnum * comb(k, j)
            md = mden * factorial(m)
            if i == K - 1:
                num = 1
                for rr in [p] + rs:
                    num *= factorial(rr)
                out.append((tuple(rs), Fr(c * num, md)))
            else:
                rec(i + 1, r, rs + [r], c, md)

    rec(0, p, [], 1, 1)
    return out


def pairs_of(K):
    return [(i, j) for i in range(K) for j in range(i + 1, K)]


@functools.lru_cache(maxsize=None)
def _patterns(kinds):
    K = len(kinds)
    prs = pairs_of(K)
    out = []
    budget = [MAXLEGS[k] for k in kinds]

    def rec(idx, cur):
        if idx == len(prs):
            out.append(tuple(cur))
            return
        i, j = prs[idx]
        for v in range(min(budget[i], budget[j]) + 1):
            budget[i] -= v
            budget[j] -= v
            cur.append(v)
            rec(idx + 1, cur)
            cur.pop()
            budget[i] += v
            budget[j] += v

    rec(0, [])
    return prs, out


def patterns(kinds):
    """All chi line patterns of a vertex sequence (each vertex has at most MAXLEGS legs)."""
    prs, lst = _patterns(tuple(kinds))
    return [dict(zip(prs, t)) for t in lst]


def slice_counts(n, K):
    return [sum(v for (i, j), v in n.items() if i <= s < j) for s in range(K - 1)]


def legs_of(n, K):
    return [sum(v for (a, b), v in n.items() if a == i or b == i) for i in range(K)]


def reverse_pattern(n, K):
    return {(K - 1 - j, K - 1 - i): v for (i, j), v in n.items()}


def pattern_key(n):
    return tuple(sorted(n.items()))
