#!/usr/bin/env python3
"""
Test of the raw -> normalized layer of lri_framework.py against a direct, independent
sympy computation:
  * random raw Laurent-log series for A3,A5,A7,Z4,Z6,Q4,Q6,Q8 (all needed (z,delta,eta)
    Taylor coefficients, eps^pmin..eps^3, l^0..l^3) given in DERIVATIVE convention;
  * Z2, Q2, A1 from the exact internal sector (also used on the sympy side);
  * sympy: build each raw moment as a polynomial in (z, delta, eta) whose coefficients are
    explicit expressions in eps, l; form odd/even generating-function ratios, differentiate,
    multiply out and extract [eps^0 l^k];
  * compare a selection of normalized coefficients (k=0,1) with the module (kmax=1) and the
    module with kmax=3 for [l^2], [l^3] (higher-log hook).
"""
import math
import os
import random
import sys

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import lri_framework as L  # noqa: E402

mp.mp.dps = 30
random.seed(3)
eps, l, z, d, e, g = sp.symbols("eps l z delta eta g")

DEG = 2          # test (z,delta) total degree <= 2 to keep sympy fast
PMAX = 3
KMAX = 3


def rnd():
    return sp.Rational(random.randint(-40, 40), random.randint(1, 7))


def main():
    """reference: note eq:normalization (explicit products, A1 kept for EE) with plain-dict
    multivariate series in (z,delta,eta) x (eps,l); no truncation of log powers."""
    DEG = 2
    raw = {}
    ref = {}
    for M, n in (("A", 3), ("A", 5), ("A", 7), ("Z", 4), ("Z", 6), ("Q", 4), ("Q", 6), ("Q", 8)):
        pmin = L.struct_pmin(M, n)
        jet = {}
        for i in range(DEG + 1):
            for j in range(DEG + 1 - i):
                for ee in (0, 1):
                    ser = {}
                    for p in range(pmin, PMAX + 1):
                        for k in range(KMAX + 1):
                            c = mp.mpf(random.randint(-40, 40)) / random.randint(1, 7)
                            ds = L.deriv_str(i, j, ee)
                            raw[f"{M}{n}{'_' + ds if ds else ''}[eps^{p} l^{k}]"] = c
                            ser[(p, k)] = c / (math.factorial(i) * math.factorial(j))
                    jet[(i, j, ee)] = ser
        ref[(M, n)] = jet
    for M, kind in (("Z", "Z"), ("Q", "Q")):
        ref[(M, 2)] = {(i, j, ee): dict(L.two_kink(kind, i, j, ee, 8, None, 30))
                       for i in range(DEG + 1) for j in range(DEG + 1 - i) for ee in (0, 1)}
    ref[("A", 1)] = {(0, j, ee): ({(0, 0): L.A1_taylor(j, ee)}) for j in range(DEG + 1) for ee in (0, 1)}
    mon = [(i, j, ee) for i in range(DEG + 1) for j in range(DEG + 1 - i) for ee in (0, 1)]

    def smul(a, b):
        r = {}
        for (p1, k1), x in a.items():
            for (p2, k2), y in b.items():
                r[(p1 + p2, k1 + k2)] = r.get((p1 + p2, k1 + k2), 0) + x * y
        return r

    def sadd(a, b, s=1):
        r = dict(a)
        for kk, y in b.items():
            r[kk] = r.get(kk, 0) + s * y
        return r

    def jmul(A, B):
        out = {}
        for m in mon:
            acc = {}
            for m1 in mon:
                m2 = (m[0] - m1[0], m[1] - m1[1], m[2] - m1[2])
                if min(m2) < 0 or m1 not in A or m2 not in B:
                    continue
                acc = sadd(acc, smul(A[m1], B[m2]))
            out[m] = acc
        return out

    def jadd(*terms):
        out = {}
        for s, J in terms:
            for m, ser in J.items():
                out[m] = sadd(out.get(m, {}), ser, s)
        return out
    A1, A3, A5, A7 = (ref[("A", n)] for n in (1, 3, 5, 7))
    Z2, Z4, Z6 = (ref[("Z", n)] for n in (2, 4, 6))
    Q2, Q4, Q6, Q8 = (ref[("Q", n)] for n in (2, 4, 6, 8))
    Z22 = jmul(Z2, Z2)
    Z222 = jmul(Z22, Z2)
    Z24 = jmul(Z2, Z4)
    # eq:normalization (A1 kept: "source derivatives differentiate every factor, including A1")
    C3 = jadd((1, A3), (-1, jmul(A1, Z2)))
    C5 = jadd((1, A5), (-1, jmul(A3, Z2)), (1, jmul(A1, jadd((1, Z22), (-1, Z4)))))
    C7 = jadd((1, A7), (-1, jmul(A5, Z2)), (1, jmul(A3, jadd((1, Z22), (-1, Z4)))),
              (1, jmul(A1, jadd((-1, Z222), (2, Z24), (-1, Z6)))))
    K4 = jadd((1, Q4), (-1, jmul(Q2, Z2)))
    K6 = jadd((1, Q6), (-1, jmul(Q4, Z2)), (1, jmul(Q2, jadd((1, Z22), (-1, Z4)))))
    K8 = jadd((1, Q8), (-1, jmul(Q6, Z2)), (1, jmul(Q4, jadd((1, Z22), (-1, Z4)))),
              (1, jmul(Q2, jadd((-1, Z222), (2, Z24), (-1, Z6)))))
    norm = {("C", 3): C3, ("C", 5): C5, ("C", 7): C7, ("K", 4): K4, ("K", 6): K6, ("K", 8): K8}
    tests = [("C", 5, (1, 0, 0)), ("C", 5, (0, 1, 1)), ("C", 7, (1, 0, 0)), ("C", 7, (0, 0, 1)),
             ("C", 3, (2, 0, 0)), ("K", 6, (1, 0, 1)), ("K", 8, (0, 0, 0)), ("K", 8, (1, 0, 0)),
             ("K", 4, (0, 2, 0)), ("C", 5, (1, 1, 0)), ("C", 7, (0, 1, 0)), ("K", 6, (0, 1, 1))]
    # only (z,delta)-degree <= 2 atoms are supplied: the degree-3 ones that the full outputs need are
    # absent, so strict mode would (rightly) refuse; this test only reads the normalized layer
    fw1 = L.Framework("D4", dps=30, kmax=1)
    r1 = fw1.from_raw(raw, strict=False)
    fw3 = L.Framework("D4", dps=30, kmax=3)
    r3 = fw3.from_raw(raw, track=False, strict=False)
    worst = 0
    ok = True
    for X_, n, (i, j, ee) in tests:
        ser = norm[(X_, n)][(i, j, ee)]
        for k in range(0, 4):
            refv = ser.get((0, k), 0) * math.factorial(i) * math.factorial(j)
            ds = L.deriv_str(i, j, ee)
            nm = f"{X_}{n}{'_' + ds if ds else ''}[l^{k}]"
            res = r1 if k <= 1 else r3
            got = res.normalized.get(nm)
            if got is None or got.is_missing:
                print("  MISSING", nm, None if got is None else sorted(got.miss)[:3])
                ok = False
                continue
            diff = abs(got.v - refv) / (1 + abs(refv))
            worst = max(worst, diff)
            print(f"  {nm:18s} module {mp.nstr(got.v, 18):>26s}  reference {mp.nstr(refv, 18):>26s}  rel.diff {mp.nstr(diff, 3)}")
    print("worst rel. diff:", mp.nstr(worst, 3))
    ok &= worst < mp.mpf(10) ** -20
    print("NORMALIZATION TEST", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
