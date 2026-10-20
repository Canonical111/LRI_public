#!/usr/bin/env python3
"""Exact algebra: gs:C5 at d=2 (A = 4 log2, R = X = 0, U = -14 z3, V = -4 z3, Z = 4 G Q) with L2 = -2 log2 P4, K2 = 32 G^2 - 28 z3 log2
reproduces C62d's 972 C5(2) formula; plus the numeric non-scalar part from this workflow's spectral L2, K2."""
import sympy as sp, json, mpmath as mp
P5, P4, Q, G, z3, l2 = sp.symbols('P5 P4 Q G zeta3 log2')
A, R, U, V, X, Z = 4 * l2, 0, -14 * z3, -4 * z3, 0, 4 * G * Q
L2, K2 = -2 * l2 * P4, 32 * G**2 - 28 * z3 * l2
rhs = (-1536 * (P5 + K2) + 384 * A * P4 - 576 * L2 - 1728 * Q**2 + 720 * A**2 * Q + 1008 * Q * R + 7152 * Z
       - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * X) / 48
c62d = -32 * P5 + 56 * l2 * P4 - 36 * Q**2 + (240 * l2**2 + 596 * G) * Q - 1024 * G**2 + 449 * z3 * l2 - 80 * l2**4
print('46656 C5(2)/48 - C62d formula =', sp.expand(rhs - c62d))
mp.mp.dps = 60
r = json.load(open('run4_combined.json'))
print('non-scalar part -1536(K2 + 3 L2/8)/46656 =', mp.nstr(-1536 * (mp.mpf(r['K2']) + 3 * mp.mpf(r['L2']) / 8) / 46656, 30))
