"""Discrete Cauchy integral: Taylor coefficients from the values on |eps| = rho.

  c_n = (1/K) sum_k f(eps_k) eps_k^(-n),  eps_k = rho exp(2 pi i k/K),  n = 0..K-1
  (= exact Taylor coefficient + aliasing sum_{j>=1} f_{n+jK} rho^(jK)).
"""
import json, sys
from fractions import Fraction
import mpmath as mp


def load(fn):
    with open(fn) as f:
        return json.load(f)


def series(data, getter, nmax=None):
    meta = data['meta']
    K = meta['K']
    fr = Fraction(meta['rho'])
    mp.mp.prec = meta['prec'] + 64
    rho = mp.mpf(fr.numerator) / fr.denominator
    vals = {}
    for pt in data['points']:
        z = getter(pt)
        vals[pt['k']] = mp.mpc(mp.mpf(z[0]), mp.mpf(z[1]))
    if meta.get('half'):
        for k in range(K // 2 + 1, K):
            vals[k] = mp.conj(vals[K - k])
    assert len(vals) == K
    nmax = K if nmax is None else nmax
    coeffs = []
    for n in range(nmax):
        s = mp.mpc(0)
        for k in range(K):
            s += vals[k] * mp.expjpi(mp.mpf(-2 * k * n) / K)
        coeffs.append(s / K / rho ** n)
    return coeffs


def all_series(data, nmax=None):
    out = {'Delta': series(data, lambda p: p['Delta'], nmax),
           'r': series(data, lambda p: p['r'], nmax),
           'g': series(data, lambda p: p['g'], nmax)}
    for p in range(4):
        out[f'E{p}'] = series(data, lambda q, p=p: q['E'][str(p)], nmax)
    if data['points'][0]['vacua']:
        for l in data['points'][0]['vacua']:
            out[f'Ev{l}'] = series(data, lambda q, l=l: q['vacua'][l], nmax)
    return out


if __name__ == '__main__':
    d = load(sys.argv[1])
    c = series(d, lambda p: p['Delta'])
    K = d['meta']['K']
    rho = float(Fraction(d['meta']['rho']))
    for n in range(K):
        print(n, mp.nstr(c[n].real, 30), mp.nstr(c[n].imag, 3), ' |c_n| rho^n =', mp.nstr(abs(c[n]) * rho ** n, 3))
