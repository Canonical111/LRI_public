#!/usr/bin/env python3
"""Can the r = 4 residue functional be written with two nodes, one of them the pole node t = 0?
Mode vector of the functional: w = (c(3+2c^2), 1+4c^2, 5c), c = cos(pi b/2).  Node t=0 evaluates
e_T = (1, c, 2c^2-1); a node tau evaluates e(tau) = (1, cos 2pi tau, cos 4pi tau).  Solve w = alpha e_T + beta e(tau)."""
import sympy as sp
c, al, be, z = sp.symbols('c alpha beta z')   # z = cos(2 pi tau2)
w = sp.Matrix([c * (3 + 2 * c ** 2), 1 + 4 * c ** 2, 5 * c])
eT = sp.Matrix([1, c, 2 * c ** 2 - 1])
e2 = sp.Matrix([1, z, 2 * z ** 2 - 1])
sol = sp.solve(list(w - al * eT - be * e2), [al, be, z], dict=True)
for s_ in sol:
    print({k: sp.factor(v) for k, v in s_.items()})
