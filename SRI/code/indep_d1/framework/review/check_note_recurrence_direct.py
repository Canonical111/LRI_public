#!/usr/bin/env python3
"""
Reviewer check: module vs a direct, separately written transcription of the NOTE's formulas
(not the agent's derived sympy formulas):
  * eq:subtraction (l.437-444) + h8 (l.1149-1150), j_n, lambda_n (l.427-432), v = 1+z kept explicit;
  * dictionary (l.1124-1130) by explicit sympy differentiation at z=delta=0;
  * eq:D3assembly (l.625), eq:C6assembly with B_old (l.694-700), D4 linear part (l.1033-1036),
  * own fixed-point / T / D solve (eq:TD) for C3..C7 via eq:conversion.
Random rational normalized responses, polynomials in (z, delta) of total degree 4.
"""
import os
import random
import sys
from fractions import Fraction

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import lri_framework as L  # noqa: E402

random.seed(2026)
mp.mp.dps = 40
z, d, u = sp.symbols("z delta u")
DEG = 4


def rpoly():
    return sum(sp.Rational(random.randint(-30, 30), random.randint(1, 9)) * z ** i * d ** j
               for i in range(DEG + 1) for j in range(DEG + 1 - i))


def trunc(e, n=DEG):
    P = sp.Poly(sp.expand(e), z, d)
    return sum(c * z ** a * d ** b for (a, b), c in P.terms() if a + b <= n)


# normalized responses: C_{n,k}(z,delta), EE C_{n,0}; K_{n,k}, EE K_{n,0}
C0 = {n: rpoly() for n in (3, 5, 7)}
C1 = {n: rpoly() for n in (3, 5, 7)}
CE = {n: rpoly() for n in (3, 5, 7)}
K0 = {n: rpoly() for n in (2, 4, 6, 8)}
K1 = {n: rpoly() for n in (4, 6, 8)}
KE = {n: rpoly() for n in (2, 4, 6, 8)}
v = 1 + z
j = {1: trunc(sp.series(-2 / (1 + d), d, 0, DEG + 1).removeO())}
for n in (3, 5):
    j[n] = -2 * sp.diff(C0[n], z) + CE[n]
lam = {n: trunc(-2 * K0[n] - 4 * v * sp.diff(K0[n], z) + 2 * v * KE[n]) for n in (2, 4, 6)}
Q20 = K0[2]
b3 = trunc(C1[3] + 2 * v * j[1])
h4 = trunc(K1[4] - 2 * Q20 * b3 + lam[2])
b5 = trunc(C1[5] - 3 * C0[3] * b3 - 2 * v * j[1] * h4 + 2 * v * j[3])
h6 = trunc(K1[6] - 2 * Q20 * b5 - 4 * K0[4] * b3 - lam[2] * h4 + lam[4])
b7 = trunc(C1[7] - 3 * C0[3] * b5 - 5 * C0[5] * b3 - 2 * v * j[1] * h6 - 2 * v * j[3] * h4 + 2 * v * j[5])
h8 = trunc(K1[8] - 2 * Q20 * b7 - 4 * K0[4] * b5 - 6 * K0[6] * b3 - lam[2] * h6 - lam[4] * h4 + lam[6])


def D(e, nv, nd):
    return sp.diff(e, z, nv, d, nd).subs({z: 0, d: 0}) if (nv or nd) else e.subs({z: 0, d: 0})


note = {
    "a": D(b3, 1, 0), "p": D(b3, 0, 1), "A": D(b3, 2, 0) / 2, "E": D(b3, 1, 1), "V": D(b3, 0, 2) / 2,
    "alpha": D(b3, 3, 0) / 6, "beta": D(b3, 2, 1) / 2, "gamma": D(b3, 1, 2) / 2,
    "b": D(b5, 0, 0), "G": D(b5, 1, 0), "R": D(b5, 0, 1), "Phi": D(b5, 2, 0) / 2, "Psi": D(b5, 1, 1),
    "J": D(b7, 0, 0), "Omega": D(b7, 1, 0),
    "c": -4 * D(h4, 0, 0), "f": -4 * D(h4, 1, 0), "q": -4 * D(h4, 0, 1), "L": -2 * D(h4, 2, 0),
    "M": -4 * D(h4, 1, 1), "Q": -2 * D(h4, 0, 2), "k": -4 * D(h6, 0, 0), "N": -4 * D(h6, 1, 0),
    "P": -4 * D(h6, 0, 1), "K": -4 * D(h8, 0, 0),
}

# feed the module the same normalized data (derivative convention), K2[l^1] = -1 exactly (h2=-1)
norm = {}


def put(lab, n, k, poly, E=False):
    P = sp.Poly(sp.expand(poly), z, d)
    for i in range(DEG + 1):
        for jj in range(DEG + 1 - i):
            c = P.coeff_monomial(z ** i * d ** jj)
            val = c * sp.factorial(i) * sp.factorial(jj)
            ds = L.deriv_str(i, jj, 1 if E else 0)
            norm[f"{lab}{n}{'_' + ds if ds else ''}[l^{k}]"] = mp.mpf(sp.Rational(val).p) / sp.Rational(val).q


for n in (3, 5, 7):
    put("C", n, 0, C0[n]); put("C", n, 1, C1[n]); put("C", n, 0, CE[n], E=True)
for n in (2, 4, 6, 8):
    put("K", n, 0, K0[n]); put("K", n, 0, KE[n], E=True)
for n in (4, 6, 8):
    put("K", n, 1, K1[n])
put("K", 2, 1, sp.Integer(-1))
fw = L.Framework("D4", dps=40)
res = fw.from_normalized(norm)
worst = 0
for nm, x in note.items():
    ref = mp.mpf(sp.Rational(x).p) / sp.Rational(x).q
    got = res.beta[nm]
    assert not got.is_missing, nm
    worst = max(worst, abs(got.v - ref) / (1 + abs(ref)))
print("[1] 25 beta inputs: module vs direct transcription of note recurrence+dictionary: worst rel diff",
      mp.nstr(worst, 3))
ok = worst < mp.mpf(10) ** -30

# ---- own fixed point and invariants from the note's F, H (l.1023-1029) at random rational betas
names = list(note.keys())
B = {nm: sp.Rational(random.randint(-50, 50), random.randint(1, 7)) for nm in names}
s = {nm: sp.Symbol(nm) for nm in names}
F = (z + u * (1 + s["a"] * z + s["p"] * d + s["A"] * z ** 2 + s["E"] * d * z + s["V"] * d ** 2 + s["alpha"] * z ** 3
              + s["beta"] * z ** 2 * d + s["gamma"] * z * d ** 2)
     + u ** 2 * (s["b"] + s["G"] * z + s["R"] * d + s["Phi"] * z ** 2 + s["Psi"] * z * d) + u ** 3 * (s["J"] + s["Omega"] * z))
H = (-d + 4 * u + u ** 2 * (s["c"] + s["f"] * z + s["q"] * d + s["L"] * z ** 2 + s["M"] * z * d + s["Q"] * d ** 2)
     + u ** 3 * (s["k"] + s["N"] * z + s["P"] * d) + s["K"] * u ** 4)
Fn, Hn = F.subs({s[k]: B[k] for k in names}), H.subs({s[k]: B[k] for k in names})
eps_ = sp.Symbol("x")
us = sum(sp.Symbol(f"u{k}") * eps_ ** k for k in range(1, 5))
zs = sum(sp.Symbol(f"z{k}") * eps_ ** k for k in range(1, 5))
sol = {}
for m in range(1, 5):
    Fm = sp.expand(sp.series(Fn.subs({u: us, z: zs, d: eps_}).subs(sol), eps_, 0, m + 1).removeO()).coeff(eps_, m)
    Hm = sp.expand(sp.series(Hn.subs({u: us, z: zs, d: eps_}).subs(sol), eps_, 0, m + 1).removeO()).coeff(eps_, m)
    sol.update(sp.solve([Fm, Hm], [sp.Symbol(f"u{m}"), sp.Symbol(f"z{m}")], dict=True)[0])
Tx = (2 * u * sp.diff(Fn, u) + (1 + z) * sp.diff(Hn, z))
Dx = 2 * u * (1 + z) * (sp.diff(Fn, u) * sp.diff(Hn, z) - sp.diff(Fn, z) * sp.diff(Hn, u))
Ts = sp.expand(sp.series(Tx.subs({u: us, z: zs, d: eps_}).subs(sol), eps_, 0, 5).removeO())
Ds = sp.expand(sp.series(Dx.subs({u: us, z: zs, d: eps_}).subs(sol), eps_, 0, 5).removeO())
T2, T3 = Ts.coeff(eps_, 2), Ts.coeff(eps_, 3)
D2, D3, D4 = Ds.coeff(eps_, 2), Ds.coeff(eps_, 3), Ds.coeff(eps_, 4)
assert Ts.coeff(eps_, 1) == sp.Rational(1, 2) and Ds.coeff(eps_, 1) == -2
C3 = D2 - sp.Rational(1, 16)
C5 = 2 * D3 - T2 / 2 + C3 ** 2 / 4
C7 = 4 * D4 - T3 - T2 ** 2 + C3 * C5 / 2
rb = L.Framework("D4", dps=40).from_beta({k: mp.mpf(B[k].p) / B[k].q for k in names})
w2 = 0
for lab, ex, got in (("D2", D2, rb.inv["D2"]), ("T2", T2, rb.inv["T2"]), ("D3", D3, rb.inv["D3"]),
                     ("T3", T3, rb.inv["T3"]), ("D4", D4, rb.inv["D4"]), ("C5", C5, rb.C[5]),
                     ("C6", 4 * T3, rb.C[6]), ("C7", C7, rb.C[7])):
    ref = mp.mpf(sp.Rational(ex).p) / sp.Rational(ex).q
    w2 = max(w2, abs(got.v - ref) / (1 + abs(ref)))
print("[2] D2..D4, T2, T3, C5..C7: module vs own sympy fixed point (eq:TD, eq:conversion): worst rel diff",
      mp.nstr(w2, 3))
ok &= w2 < mp.mpf(10) ** -30
# ---- note's explicit assembly formulas
b_ = B
D2n = sp.Rational(1, 2) - b_["a"] / 2 - b_["c"] / 8
T2n = -b_["a"] / 8 + b_["b"] / 4 - b_["c"] / 32 + b_["f"] / 16 + b_["p"] / 2
D3n = (16 * b_["A"] - 32 * b_["E"] - 8 * b_["G"] + 8 * b_["b"] + b_["c"] ** 2 + 4 * b_["f"] - 4 * b_["k"]
       + 32 * b_["p"] - 8 * b_["q"]) / 64
Bold = (b_["A"] / 8 - b_["E"] / 2 - b_["G"] / 4 + (b_["a"] ** 2 - b_["a"] * b_["b"]) / 8 + b_["a"] * b_["c"] / 16
        - b_["a"] * b_["p"] / 2 - b_["b"] * b_["c"] / 8 + b_["c"] ** 2 / 64 - b_["c"] * b_["f"] / 32
        - b_["c"] * b_["p"] / 8 - b_["f"] / 32 - b_["k"] / 32 - b_["q"] / 8)
C6n = Bold + 2 * b_["V"] + b_["R"] + sp.Rational(3, 8) * b_["J"] - b_["L"] / 8 + b_["M"] / 4 + b_["N"] / 16
print("[3] note eq D2,T2 (l.563-564):", sp.simplify(D2n - D2) == 0, sp.simplify(T2n - T2) == 0,
      "| eq:D3assembly:", sp.simplify(D3n - D3) == 0, "| eq:C6assembly (with B_old):", sp.simplify(C6n - 4 * T3) == 0)
ok &= sp.simplify(D2n - D2) == 0 and sp.simplify(T2n - T2) == 0 and sp.simplify(D3n - D3) == 0 and sp.simplify(C6n - 4 * T3) == 0
lin = {"alpha": Fraction(-3, 32), "beta": Fraction(1, 4), "gamma": Fraction(-1, 2), "Phi": Fraction(1, 16),
       "Psi": Fraction(-1, 8), "Omega": Fraction(-1, 32), "Q": Fraction(-1, 8), "P": Fraction(-1, 16), "K": Fraction(-3, 128)}
w3 = max(abs(rb.inv["D4"].g[k] - mp.mpf(x.numerator) / x.denominator) for k, x in lin.items())
print("[4] D4 linear part (l.1033-1036): max |module gradient - note coefficient| =", mp.nstr(w3, 3))
ok &= w3 < mp.mpf(10) ** -30
print("NOTE-DIRECT CHECK", "PASSED" if ok else "FAILED")
