#!/usr/bin/env python3
"""ARCHIVE-FREE sanity check of the spec's integrand conventions (signs, q_i, S2, translation
factor, reflected endpoint insertion) at finite cutoff eps = 1/8 by plain scipy cubature.
Writes OUR values only (double precision, ~1e-10); the comparison with archived finite-cutoff
values is done in ../comparison/scripts/compare_with_archive.py.  Runs in seconds."""
import json
from pathlib import Path
import numpy as np
from scipy import integrate

OUT = Path(__file__).resolve().parent.parent / 'out'
e = 1 / 8
L = np.log


def A3_d(r, s):          # gaps r, s; W3 = (r+s)^2/(r^2 s^2); S2 = sum q_i q_j log^2 r_ij
    W = (r + s)**2 / (r * r * s * s)
    S2 = -L(r)**2 - L(s)**2 + L(r + s)**2
    return (1 - r - s) * W * S2


def Z4_d(w, s, r):
    W = (r + s)**2 * (s + w)**2 / (r * r * s * s * w * w * (r + s + w)**2)
    S2 = -L(r)**2 - L(s)**2 - L(w)**2 + L(r + s)**2 + L(s + w)**2 - L(r + s + w)**2
    return (1 - r - s - w) * W * S2


def EQ2(x2, x1):         # reflected endpoint insertion 2 sum q_i log X_i, absolute coordinates, D2 = x2 - x1
    r = x2 - x1
    return r * 2 * (L(x1) - L(x2)) / (r * r) if x1 > 0 else 0.0


o = {}
o['A3_d'] = integrate.dblquad(A3_d, e, 1 - e, lambda r: e, lambda r: 1 - r, epsabs=1e-11, epsrel=1e-11)[0]
o['Z4_d'] = integrate.tplquad(Z4_d, e, 1 - 2 * e, lambda r: e, lambda r: 1 - r - e, lambda r, s: e, lambda r, s: 1 - r - s,
                              epsabs=1e-9, epsrel=1e-9)[0]
o['EQ2_base'] = integrate.dblquad(EQ2, 0, 1 - e, lambda x1: x1 + e, lambda x1: 1.0, epsabs=1e-12, epsrel=1e-12)[0]
for k, v in o.items():
    print(k, repr(v))
json.dump({'note': 'ARCHIVE-FREE scipy cubature at eps = 1/8 (double precision, ~1e-10). Archive comparison: '
                   'comparison/scripts/compare_with_archive.py.', 'eps': '1/8', 'values': o},
          open(OUT / 'sanity_finite_cutoff.json', 'w'), indent=1)
