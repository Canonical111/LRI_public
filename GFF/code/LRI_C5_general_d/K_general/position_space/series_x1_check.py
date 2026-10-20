"""Six-family series at x = (1,1) (unit arguments) for the generic test kite, partial sums over [0,M)^2, vs the MB value."""
import numpy as np
from scipy.special import gammaln, gamma as G, rgamma
import mpmath as mp
from kite_general import mb_value
d, nu1, nu2, nu3, a3, a4 = 1.7, 0.395, 0.387, 0.380, 0.159, 0.620
h = d / 2; lam = nu1 + nu2 + nu3 - h; cw = a3 + a4 - h
def lgs(x):   # log|Gamma(x)| and sign, real x
    from scipy.special import gammasgn
    return gammaln(x), gammasgn(x)
def term(z1, z2, skip1, skip2, wfam=False):
    # returns log|T| and sign of the product of remaining Gammas (without residue factors)
    L = np.zeros_like(z1); S = np.ones_like(z1)
    def add(x, s=1):
        nonlocal L, S
        l, sg = lgs(x); L += s * l; S *= sg
    if skip1 != 'a': add(-z1)
    if skip1 != 'b': add(nu2 - lam - z1)
    add(h - a3 + z1); add(a3 - z1, -1)
    if skip2 != 'a': add(-z2)
    if skip2 != 'b': add(nu1 - lam - z2)
    add(h - a4 + z2); add(a4 - z2, -1)
    w = z1 + z2
    add(lam + w); add(nu3 + w); add(d - a3 - a4 + w, -1)
    if not wfam: add(cw - w)
    return L, S
P0 = G(h) ** 2 * rgamma(nu1) * rgamma(nu2) * rgamma(nu3) * rgamma(d - nu1 - nu2 - nu3)
Mmax = 3000
m = np.arange(Mmax, dtype=float)
lf = gammaln(m + 1)
res = {}
for name, (o1, s1), (o2, s2) in [('00', (0, 'a'), (0, 'a')), ('01', (0, 'a'), (nu1 - lam, 'b')),
                                 ('10', (nu2 - lam, 'b'), (0, 'a')), ('11', (nu2 - lam, 'b'), (nu1 - lam, 'b'))]:
    I, J = np.meshgrid(m, m, indexing='ij')
    L, S = term(o1 + I, o2 + J, s1, s2)
    T = S * (-1.0) ** (I + J) * np.exp(L - lf[:, None] - lf[None, :])
    res[name] = T
for name, (o2, s2) in [('w0', (0, 'a')), ('w1', (nu1 - lam, 'b'))]:
    K_, J = np.meshgrid(m, m, indexing='ij')
    z2 = o2 + J; z1 = cw + K_ - z2
    L, S = term(z1, z2, None, s2, wfam=True)
    T = S * (-1.0) ** (K_ + J) * np.exp(L - lf[:, None] - lf[None, :])
    res[name] = T
v, info = mb_value(d, nu1, nu2, nu3, a3, a4, '-0.104', '-0.104', digits=16)
mbv = float(v.real.mid())
print('MB value at x=1:', mbv)
Ms = [100, 200, 400, 800, 1600, 3000]
parts = []
for M in Ms:
    tot = sum(P0 * T[:M, :M].sum() for T in res.values())
    parts.append(tot)
    print('M=%5d  partial sum = %.12f   diff = %.3e' % (M, tot, tot - mbv))
