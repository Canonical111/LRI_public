"""Small-eps series algebra: dict {(k,j): (value, err)} meaning sum value * eps^k * log(eps)^j."""
import math


def smul(a, b, kmax=0):
    out = {}
    for (k1, j1), (v1, e1) in a.items():
        for (k2, j2), (v2, e2) in b.items():
            k = k1 + k2
            if k > kmax:
                continue
            key = (k, j1 + j2)
            v, e = out.get(key, (0.0, 0.0))
            out[key] = (v + v1 * v2, math.sqrt(e * e + (e1 * v2) ** 2 + (v1 * e2) ** 2))
    return out


def sadd(*terms):
    """terms: (coef, series)"""
    out = {}
    for c, s in terms:
        for key, (v, e) in s.items():
            v0, e0 = out.get(key, (0.0, 0.0))
            out[key] = (v0 + c * v, math.sqrt(e0 * e0 + (c * e) ** 2))
    return out


def exact(d):
    """series from exact numbers {(k,j): v}"""
    return {k: (float(v), 0.0) for k, v in d.items()}


def show(s, kmin=-9, kmax=9, name=''):
    for key in sorted(s):
        if kmin <= key[0] <= kmax:
            v, e = s[key]
            print('%s eps^%d log^%d : %.15g  +- %.2g' % (name, key[0], key[1], v, e))


Z2 = exact({(-1, 0): 1, (0, 1): 1, (0, 0): -1})
Q2 = exact({(0, 1): -1, (0, 0): -1, (1, 0): 1})
