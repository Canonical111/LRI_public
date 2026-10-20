#!/usr/bin/env python3
"""Per-spin Fourier coefficients c_k^{(l)} of Xi_l(t) (to see whether c_{+-2} vanish spin by spin)."""
import mpmath as mp
from check_perspin import Xi_l, modes_from_samples, setup
mp.mp.dps = 30
q, tau = setup('1.5', '0.3')
ts = [mp.mpf('0.0731') + mp.mpf(j) / 5 + 0.05j for j in range(5)]
for l in (0, 1, 2, 3):
    c = modes_from_samples([Xi_l(l, t, q, tau) for t in ts], ts)
    print('l', l, ' '.join('c%d=%s' % (k, mp.nstr(c[k], 8)) for k in range(-2, 3)), flush=True)
