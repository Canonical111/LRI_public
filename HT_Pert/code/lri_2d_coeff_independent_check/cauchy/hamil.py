"""Numerical (python-flint, arbitrary precision) evaluation of H0, M, V at complex eps."""
import numpy as np
from flint import acb, arb, acb_mat, ctx


def x_of_eps(eps):
    return acb(1) / 2 - eps / 4


def weights(sp, x):
    """c_m = sqrt(w_m(x)), w_ab = (x)_a (x)_b / (a! b!)  (principal branch; analytic near x=1/2)."""
    cs = []
    for (a, b) in sp.modes:
        w = acb(1)
        for k in range(a):
            w *= (x + k) / (k + 1)
        for k in range(b):
            w *= (x + k) / (k + 1)
        cs.append(w.sqrt())
    return cs


class NumOps:
    """Holds precision-dependent constant coefficients of the exact operator structure."""

    def __init__(self, sp, ops):
        self.sp = sp
        self.terms = {}
        for par in (0, 1):
            for name in ('M', 'V'):
                lst = []
                for (i, j), md in ops[par][name].items():
                    for mono, sd in md.items():
                        coef = arb(0)
                        for S, q in sd.items():
                            coef += arb(q.numerator) / q.denominator * arb(S).sqrt()
                        lst.append((i, j, mono, coef))
                self.terms[(par, name)] = lst
        # double-precision copy of the structure (for the radial continuation stage)
        self.monos = sorted({t[2] for lst in self.terms.values() for t in lst})
        mid = {m: k for k, m in enumerate(self.monos)}
        self.t64 = {}
        for key, lst in self.terms.items():
            I = np.array([t[0] for t in lst], dtype=np.int64)
            J = np.array([t[1] for t in lst], dtype=np.int64)
            C = np.array([float(t[3]) for t in lst])
            Mi = np.array([mid[t[2]] for t in lst], dtype=np.int64)
            self.t64[key] = (I, J, C, Mi)

    def eval64(self, eps):
        sp = self.sp
        x = 0.5 - eps / 4
        cs = []
        for (a, b) in sp.modes:
            w = 1.0 + 0j
            for k in range(a):
                w *= (x + k) / (k + 1)
            for k in range(b):
                w *= (x + k) / (k + 1)
            cs.append(np.sqrt(w))
        mv = np.empty(len(self.monos), dtype=complex)
        for k, mono in enumerate(self.monos):
            v = 1.0 + 0j
            for m, e in mono:
                v *= cs[m] ** e
            mv[k] = v
        out = {'x': x}
        for par in (0, 1):
            n = sp.dim(par)
            sec = sp.sectors[par]
            out[(par, 'H0')] = np.array([sec['level'][i] + sec['P'][i] * x for i in range(n)], dtype=complex)
            for name in ('M', 'V'):
                I, J, C, Mi = self.t64[(par, name)]
                A = np.zeros((n, n), dtype=complex)
                np.add.at(A, (I, J), C * mv[Mi])
                out[(par, name)] = A
        return out

    def eval(self, eps):
        """Return dict with per-sector full-cutoff matrices M, V (acb_mat), H0 diag list, x."""
        sp = self.sp
        x = x_of_eps(acb(eps))
        cs = weights(sp, x)
        monoval = {}
        out = {'x': x}
        for par in (0, 1):
            n = sp.dim(par)
            sec = sp.sectors[par]
            out[(par, 'H0')] = [acb(sec['level'][i]) + sec['P'][i] * x for i in range(n)]
            for name in ('M', 'V'):
                ent = [[acb(0)] * n for _ in range(n)]
                for (i, j, mono, coef) in self.terms[(par, name)]:
                    v = monoval.get(mono)
                    if v is None:
                        v = acb(1)
                        for m, e in mono:
                            v *= cs[m] ** e
                        monoval[mono] = v
                    ent[i][j] += coef * v
                out[(par, name)] = ent
        return out


def submat(ent, n):
    """acb_mat from the leading n x n block of a list-of-lists."""
    return acb_mat([row[:n] for row in ent[:n]])


def diagmat(d):
    n = len(d)
    rows = [[acb(0)] * n for _ in range(n)]
    for i in range(n):
        rows[i][i] = d[i]
    return acb_mat(rows)
