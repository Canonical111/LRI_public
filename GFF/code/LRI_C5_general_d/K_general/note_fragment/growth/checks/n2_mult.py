#!/usr/bin/env python3
"""N2: multiplicity bound |d_l| <= C_q (1+l)^(4q-2)  (PROOF.md, eq. (2.3)).

d_0 = 1, d_{k+1} = 4q (2q+1)_k (4q-1)_k / ((2q)_k (2)_k)   (fp:degeneracy).
Prints C_q = sup_{l <= L} |d_l| (1+l)^(2-4q), the limit 2/|Gamma(4q-1)| of the ratio, and the sign pattern.
"""
import mpmath as mp

mp.mp.dps = 30


def dlist(q, L):
    d = [mp.mpf(1)]
    c = 4 * q
    for k in range(L):
        d.append(c)
        c = c * (2 * q + 1 + k) * (4 * q - 1 + k) / ((2 * q + k) * (2 + k))
    return d


L = 20000
print('L =', L)
for qs in ('0.02', '0.1', '0.2', '0.25', '0.3', '0.375', '0.5', '0.625', '0.75', '0.9', '0.99'):
    q = mp.mpf(qs)
    d = dlist(q, L)
    ratios = [abs(d[l]) * (1 + l) ** (2 - 4 * q) for l in range(L + 1)]
    lim = 2 / abs(mp.gamma(4 * q - 1)) if q != mp.mpf('0.25') else mp.mpf(0)
    neg = sum(1 for x in d if x < 0)
    print('q = %-5s  C_q = sup ratio = %-10s at l = %-6d  ratio(L) = %-10s  2/|Gamma(4q-1)| = %-10s  #negative d_l = %d'
          % (qs, mp.nstr(max(ratios), 6), ratios.index(max(ratios)), mp.nstr(ratios[-1], 6), mp.nstr(lim, 6), neg))
