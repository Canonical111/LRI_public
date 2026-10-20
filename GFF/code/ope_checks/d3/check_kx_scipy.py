#!/usr/bin/env python3
"""C63d, OPE review 2026-10-16: quick double-precision direct quadrature of the two four-vertex kites at d=1
(roots at 0 and 1, absolute exponents 2u per line, u=(1-eps)/4), with the symmetric kite as control against the
full-line Selberg formula. Usage: python3 check_kx_scipy.py EPS"""
import sys, warnings
warnings.filterwarnings('ignore')
import numpy as np
from scipy.integrate import quad
eps = float(sys.argv[1]); u = (1 - eps) / 4
def kite(e0x, e1x, e0y, e1y, exy):
    # int dx dy |x|^-e0x |1-x|^-e1x |y|^-e0y |1-y|^-e1y |x-y|^-exy
    def inner(x):
        pts = sorted({0.0, 1.0, x})
        segs = [(-np.inf, pts[0] - 1)] + [(pts[0] - 1, pts[0])] + [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)] + [(pts[-1], pts[-1] + 1), (pts[-1] + 1, np.inf)]
        f = lambda y: 0.0 if (y == 0 or y == 1 or y == x) else abs(y)**-e0y * abs(1 - y)**-e1y * abs(x - y)**-exy
        return sum(quad(f, a, b, limit=400, epsabs=0, epsrel=1e-11)[0] for a, b in segs if b > a)
    g = lambda x: 0.0 if (x == 0 or x == 1) else abs(x)**-e0x * abs(1 - x)**-e1x * inner(x)
    cuts = [-np.inf, -10, -1, 0, 0.5, 1, 2, 10, np.inf]
    return sum(quad(g, cuts[i], cuts[i + 1], limit=400, epsabs=0, epsrel=1e-9)[0] for i in range(len(cuts) - 1))
a, b = 2 * u, 4 * u
print('eps', eps)
print('K_par direct (|x|,|1-x|,|y|,|1-y|,|x-y|) = (2u,2u,2u,2u,4u):', kite(a, a, a, a, b))
print('K_x   direct (|x|,|1-x|,|y|,|1-y|,|x-y|) = (2u,4u,4u,2u,2u):', kite(a, b, b, a, a))
