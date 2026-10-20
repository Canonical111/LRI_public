#!/usr/bin/env python3
"""C71d, 2026-10-16: independent d = 1 check of the OPE package (lri_ope_reproducibility).

Nothing from the package is imported or executed.  The masters come from our condensed
note's d = 1 closed forms (Sec. 1.1, eq:KprovedFinal, gdr:L1, gs:d1Dictionary); the
one-point formulas are retyped from the OPE note (eqs. a2, Bj, h1-h4, external-f,
convolution-result, h2thermal-h4thermal, logmap1-4, exp-map, b3, b4, b5, c5, clower,
W4-W6, h4uncollected, r12, Rcheck, Jgamma).  The package's printed numbers appear only as
reference strings to compare against.

Usage: python3 -I check_d1.py [--dps 80] [--json out.json]
"""
import argparse
import json
import sys

import mpmath as mp

ap = argparse.ArgumentParser()
ap.add_argument("--dps", type=int, default=80)
ap.add_argument("--json", default=None)
ap.add_argument("--skip-quad", action="store_true", help="skip the J_d(a,b) quadrature")
args = ap.parse_args()
mp.mp.dps = args.dps

rows = []


def check(name, got, ref, tol, note=""):
    got = mp.mpf(got)
    ref = mp.mpf(ref)
    diff = got - ref
    rel = abs(diff) / abs(ref) if ref != 0 else abs(diff)
    ok = rel <= tol
    rows.append(dict(name=name, got=mp.nstr(got, 25), ref=mp.nstr(ref, 25),
                     rel=mp.nstr(rel, 3), tol=str(tol), ok=bool(ok), note=note))
    print(f"{'PASS' if ok else 'FAIL'}  {name:58s} rel {mp.nstr(rel, 3):>10s}  (tol {tol})")
    return ok


# ---------------------------------------------------------------- masters at d = 1
q = mp.mpf(1) / 4
pi, l2, G, z3 = mp.pi, mp.log(2), mp.catalan, mp.zeta(3)
psi = mp.psi
A = psi(0, 2 * q) - 2 * psi(0, q) + psi(0, 1)
R = psi(1, 2 * q) - psi(1, 1)
U = psi(2, q)
V = psi(2, 1) + psi(2, 2 * q)
X = psi(3, 2 * q) - psi(3, 1)
Q = mp.gamma(q) ** 4 / pi                       # Q_1
T = 6 * Q                                        # OPE note: T = 6 Q_d
Fm = mp.hyper([q, q, 0.5, 0.5], [0.75, 0.75, 1], 1)
Fp = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
Bm = mp.gamma(q) ** 4 * Fm
Bp = 64 * pi ** 4 / mp.gamma(q) ** 4 * Fp
P4 = 13 * Bm - 3 * Bp


def Y(r):
    r = mp.mpf(r)
    up = [1, 1 + r / 8] + [(r + 2) / 8] * 7
    lo = [r / 8] + [(r + 6) / 8] * 7
    return r / 8 * (mp.gamma((r + 2) / 8) / mp.gamma((r + 6) / 8)) ** 7 * mp.hyper(up, lo, -1)


c8, s8 = mp.cos(pi / 8), mp.sin(pi / 8)
X0 = Y(2)
Xp = c8 ** 7 * Y(3) - s8 ** 7 * Y(5)
Xm = c8 ** 7 * Y(1) + s8 ** 7 * Y(7)
P5 = 16 * pi ** 1.5 * (-35 * X0 + (22 * mp.sqrt(2) - 13) * Xp + (22 * mp.sqrt(2) + 13) * Xm)
# our eq:KprovedFinal, both forms
K = 128 * G ** 2 + 24 * pi ** 2 * G - 4 * pi ** 3 * l2 - 28 * (pi + 4 * l2) * z3
K_psi = 2 * psi(1, q) ** 2 - pi ** 2 * psi(1, q) + A / 2 * psi(2, q)
# our gdr:L1 (= eq:KLpsiReflected)
L = -(3 * A - pi) / 6 * P4 - 2 * pi / 3 * Bm
# our gs:d1Dictionary: Z_1 = Q H
H = 2 * pi ** 2 / 3 + 8 * G
Z = Q * H
Omega = 13 * Z - L - 12 * K

print("== masters (our closed forms) vs the d = 1 dictionary and the package's d1 values")
check("A = pi + 4 log 2", A, pi + 4 * l2, mp.mpf(10) ** (5 - args.dps))
check("R = pi^2/3", R, pi ** 2 / 3, mp.mpf(10) ** (5 - args.dps))
check("U = -2 pi^3 - 56 zeta3", U, -2 * pi ** 3 - 56 * z3, mp.mpf(10) ** (5 - args.dps))
check("V = -16 zeta3", V, -16 * z3, mp.mpf(10) ** (5 - args.dps))
check("X = 14 pi^4/15", X, 14 * pi ** 4 / 15, mp.mpf(10) ** (5 - args.dps))
check("K: Catalan form = polygamma form", K, K_psi, mp.mpf(10) ** (5 - args.dps))
# OPE note eq:d1masters, retyped
K_ope = (psi(1, q) * (3 * psi(1, q) - psi(1, 0.75)) + A * psi(2, q)) / 2
check("K: OPE eq.(d1masters) = ours", K_ope, K, mp.mpf(10) ** (5 - args.dps))
pkg = {  # results/coefficients.json, dimensions/1/masters (reference strings only)
    "T": "330.00891926497789571952459743090674549924110968731972302117541879",
    "P4": "2229.5220610709419642945251997485173235868240835449334583863521174",
    "P5": "28599.293176562103536646477021422057490321246031264169213569279351",
    "K": "39.331569128259039057503187151597861523043938020422251570986617965",
    "L": "-5805.301629548802380141179877001377744963796217474775210161354003",
    "Z": "764.93103019958857704016177876948839729230618512868406661255163724",
}
for k, v in dict(T=T, P4=P4, P5=P5, K=K, L=L, Z=Z).items():
    check(f"master {k}: ours vs package (60 digits)", v, pkg[k], mp.mpf("1e-58"))

# ---------------------------------------------------------------- thermal C_n(1), our note
print("== thermal coefficients from our note (general and d = 1 boxed forms)")
C2 = A / 9
C3 = (A ** 2 + R - 8 * Q) / 108
C4 = (16 * P4 - A ** 3 - 8 * A * Q - 3 * A * R + mp.mpf(53) / 2 * U - 3 * V) / 648
C5 = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q ** 2 + 720 * A ** 2 * Q
      + 1008 * Q * R + 7152 * Z - 15 * A ** 4 - 90 * A ** 2 * R + 414 * A * U
      - 108 * A * V - 117 * R ** 2 - 75 * X) / 46656
pT, pTb, pU, pUb = psi(1, q), psi(1, 0.75), psi(2, q), psi(2, 0.75)
C3b = (A ** 2 + (pT + pTb) / 6 - 8 * Q) / 108
C4b = (16 * P4 - A ** 3 - A / 2 * (pT + pTb) - 8 * A * Q + (365 * pU - 6 * pUb) / 14) / 648
C5b = (-1536 * P5 + 96 * (7 * A - pi) * P4 + 384 * pi * Bm - 1728 * Q ** 2
       + 16 * Q * (45 * A ** 2 + 383 * pT - 64 * pTb) - 768 * pT * (3 * pT - pTb)
       - 15 * A ** 4 - 15 * A ** 2 * (pT + pTb) - 6 * A / 7 * (431 * pU + 18 * pUb)
       - mp.mpf(83) / 4 * (pT + pTb) ** 2) / 46656
tiny = mp.mpf(10) ** (8 - args.dps)
check("C3: general form = d=1 boxed form", C3, C3b, tiny)
check("C4: general form = d=1 boxed form", C4, C4b, tiny)
check("C5: general form = d=1 boxed form", C5, C5b, tiny)
table = dict(C2="0.657131263981", C3="-3.719856322902", C4="45.42488010356", C5="-731.13947662454")
for k, v in dict(C2=C2, C3=C3, C4=C4, C5=C5).items():
    check(f"{k}(1) vs our status table (as printed)", v, table[k], mp.mpf("1e-12"))
# OPE note's own thermal formulas eq.(C23)-(C5) with T = 6Q
C3o = (A ** 2 + R) / 108 - T / 81
C4o = (16 * P4 - A ** 3 - mp.mpf(4) / 3 * A * T - 3 * A * R + mp.mpf(53) / 2 * U - 3 * V) / 648
C5o = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 48 * T ** 2 + 120 * A ** 2 * T + 168 * R * T
       + 7152 * Z - 15 * A ** 4 - 90 * A ** 2 * R + 414 * A * U - 108 * A * V - 117 * R ** 2
       - 75 * X) / 46656
check("C3: OPE eq.(C23) = ours", C3o, C3, tiny)
check("C4: OPE eq.(C4) = ours", C4o, C4, tiny)
check("C5: OPE eq.(C5) = ours", C5o, C5, tiny)

# ---------------------------------------------------------------- one-point coefficients
print("== one-point coefficients a_2..a_6 at d = 1 (OPE formulas, our masters)")
kd = mp.gamma(1 - q) * mp.gamma(2 * q) ** 3 / (54 * mp.gamma(1 + q) * mp.gamma(4 * q))
a2 = -kd
check("a2 = -2 pi^(3/2) Gamma(3/4) / (27 Gamma(1/4))", a2,
      -2 * pi ** 1.5 * mp.gamma(0.75) / (27 * mp.gamma(0.25)), tiny)
B = [psi(j, -q) - psi(j, q) for j in range(4)]
B_alt = [psi(j, 1 - q) - psi(j, q) + mp.factorial(j) / q ** (j + 1) for j in range(4)]
for j in range(4):
    check(f"B_{j}: direct = reflected form", B[j], B_alt[j], tiny)
check("B_0 = pi cot(pi q) + 1/q", B[0], pi * mp.cot(pi * q) + 1 / q, tiny)
f = [mp.mpf(1), -B[0] / 4, (B[0] ** 2 + B[1]) / 32,
     -(B[0] ** 3 + 3 * B[0] * B[1] + B[2]) / 384,
     (B[0] ** 4 + 6 * B[0] ** 2 * B[1] + 3 * B[1] ** 2 + 4 * B[0] * B[2] + B[3]) / 6144]
# independent: Taylor coefficients of Gamma(-q-e/4)/Gamma(q-e/4), normalized at e = 0
tay = mp.taylor(lambda e: mp.gamma(-q - e / 4) / mp.gamma(q - e / 4), 0, 4)
for j in range(5):
    check(f"f_{j}: Bell form = Taylor of the Gamma ratio", f[j], tay[j] / tay[0],
          mp.mpf(10) ** (20 - args.dps))
h = [mp.mpf(1),
     mp.mpf(4) / 3 * A,
     mp.mpf(25) / 36 * A ** 2 + R / 6 - mp.mpf(2) / 27 * T,
     mp.mpf(17) / 108 * A ** 3 + A * R / 12 - mp.mpf(2) / 27 * A * T + mp.mpf(4) / 27 * P4
     + mp.mpf(71) / 216 * U - V / 36,
     -7 * A ** 4 / 5184 - 7 * A ** 2 * R / 288 - 7 * A ** 2 * T / 972 + 14 * A * P4 / 81
     + 301 * A * U / 864 - 7 * A * V / 144 - 28 * K / 81 - 7 * L / 81 - 16 * P5 / 81
     - 103 * R ** 2 / 5184 + 7 * R * T / 324 - 7 * T ** 2 / 1458 - 61 * X / 3888
     + mp.mpf(175) * Z / 162]
a = {n: a2 * mp.fsum(h[j] * f[n - 2 - j] for j in range(n - 1)) for n in range(2, 7)}
# independent: Taylor coefficients of the factorized form eq.(factorized)
pref = lambda e: mp.gamma(2 * q) ** 3 * mp.gamma(-q - e / 4) / (54 * mp.gamma(4 * q) * mp.gamma(q - e / 4))
tay2 = mp.taylor(lambda e: pref(e) * mp.polyval(h[::-1], e), 0, 4)
for n in range(2, 7):
    check(f"a_{n}: convolution = Taylor of the factorized form", a[n], tay2[n - 2],
          mp.mpf(10) ** (18 - args.dps))
check("a3/a2 = 13 pi/12 + 16/3 log 2 - 1 (eq.low-special)", a[3] / a2,
      13 * pi / 12 + mp.mpf(16) / 3 * l2 - 1, tiny)
check("a3/a2 = 4A/3 - pi/4 cot(pi q) - 1/d (eq.a3derive)", a[3] / a2,
      mp.mpf(4) / 3 * A - pi / 4 * mp.cot(pi * q) - 1, tiny)
# package table (12 significant digits) and its 60-digit d1 values
tab12 = {2: "-0.139409946645", 3: "-0.850425350705", 4: "1.679873884171",
         5: "-26.272012715691", 6: "450.850442331799"}
pkg_a = {2: "-0.13940994664502544021016329979082394185666056637847813996047708336",
         3: "-0.85042535070517415611976826468724420224069673187519453080950344413",
         4: "1.6798738841713949220502361428235522810399320624563086932380001167",
         5: "-26.272012715691309487402765115511802559264821974726508144400007696",
         6: "450.85044233179925117144460655709351317642200493467737815582410255"}
for n in range(2, 7):
    check(f"a_{n}(1) vs the OPE note's Table 1 (as printed)", a[n], tab12[n], mp.mpf("1e-12"))
    check(f"a_{n}(1) vs the package's 60-digit value", a[n], pkg_a[n], mp.mpf("1e-58"))

# ---------------------------------------------------------------- thermal forms and the log map
print("== thermal forms of h_2..h_4, the log map and Omega_1")
check("h2 = 6C3 + 23A^2/36 + R/9 (eq.h2thermal)", h[2],
      6 * C3 + mp.mpf(23) / 36 * A ** 2 + R / 9, tiny)
check("h3 = 6C4 + 5AC3 + ... (eq.h3thermal)", h[3],
      6 * C4 + 5 * A * C3 + 13 * A ** 3 / 108 + 7 * A * R / 108 + U / 12, tiny)
h4t = (6 * C5 + 5 * A * C4 + (5 * A ** 2 - R) / 6 * C3 + 9 * C3 ** 2 - A ** 4 / 5184
       + 7 * A ** 2 * R / 2592 + 235 * A * U / 2592 - 5 * A * V / 432 - 7 * R ** 2 / 1728
       - 47 * X / 7776 + Omega / 81)
check("h4 = 6C5 + ... + Omega/81 (eq.h4thermal)", h[4], h4t, tiny)
ell = [None,
       12 * C2 - B[0] / 4,
       6 * C3 - A ** 2 / 4 + R / 9 + B[1] / 32,
       6 * C4 - 3 * A * C3 + 19 * A ** 3 / 324 - A * R / 12 + U / 12 - B[2] / 384,
       6 * C5 - 3 * A * C4 + (A ** 2 - mp.mpf(5) / 6 * R) * C3 - 9 * C3 ** 2 - 11 * A ** 4 / 576
       + 37 * A ** 2 * R / 864 - 53 * A * U / 2592 - 5 * A * V / 432 - 53 * R ** 2 / 5184
       - 47 * X / 7776 + Omega / 81 + B[3] / 6144]
# independent: log of the a-series
lt = mp.taylor(lambda e: mp.log(mp.polyval([a[n] for n in range(6, 1, -1)], e) / a2), 0, 4)
for j in range(1, 5):
    check(f"ell_{j}: log map = Taylor of log(a/(a2 eps^2))", ell[j], lt[j], mp.mpf(10) ** (15 - args.dps))
r = [mp.mpf(1)]
for n in range(1, 5):
    r.append(mp.fsum(j * ell[j] * r[n - j] for j in range(1, n + 1)) / n)
for n in range(3, 7):
    check(f"a_{n}: exp of the log map (eq.exp-recursion)", a2 * r[n - 2], a[n], tiny)
pkg_ell = {1: "6.1001770043753176585597683129964031542829342325777259946998166923",
           2: "-30.655965167307909337628934425939106913516539705705438457870318897",
           3: "337.6248477743568667972038326713280684474362140104482163717149487",
           4: "-5250.7662955585037390202074160233866134469677072145623480216488514"}
for j in range(1, 5):
    check(f"ell_{j}(1) vs the package", ell[j], pkg_ell[j], mp.mpf("1e-58"))
# d = 1: A = 9 C2, so the map from our printed C2..C5 needs only Omega_1 in addition
Cp = {k: mp.mpf(v) for k, v in table.items()}
ell_p = [None, 12 * Cp["C2"] - B[0] / 4,
         6 * Cp["C3"] - A ** 2 / 4 + R / 9 + B[1] / 32,
         6 * Cp["C4"] - 3 * A * Cp["C3"] + 19 * A ** 3 / 324 - A * R / 12 + U / 12 - B[2] / 384,
         6 * Cp["C5"] - 3 * A * Cp["C4"] + (A ** 2 - mp.mpf(5) / 6 * R) * Cp["C3"]
         - 9 * Cp["C3"] ** 2 - 11 * A ** 4 / 576 + 37 * A ** 2 * R / 864 - 53 * A * U / 2592
         - 5 * A * V / 432 - 53 * R ** 2 / 5184 - 47 * X / 7776 + Omega / 81 + B[3] / 6144]
rp = [mp.mpf(1)]
for n in range(1, 5):
    rp.append(mp.fsum(j * ell_p[j] * rp[n - j] for j in range(1, n + 1)) / n)
for n in range(3, 7):
    check(f"a_{n}: map from our printed table C2..C5 + Omega_1", a2 * rp[n - 2], a[n], mp.mpf("1e-9"),
          "table digits only")
print(f"   Omega_1 = 13 Z_1 - L_1 - 12 K_1 = {mp.nstr(Omega, 30)}")

# ---------------------------------------------------------------- RG input
print("== RG input at d = 1: OPE formulas vs our note and our five-loop numerics")
M = mp.gamma(-q) * mp.gamma(2 * q) ** 2 / mp.gamma(3 * q)
N = psi(0, -q) + psi(0, 3 * q) - psi(0, 1) - psi(0, 2 * q)
Jm = psi(1, -q) - psi(1, 3 * q)
b = {1: mp.mpf(3), 2: -6 * A,
     3: T + mp.mpf(87) / 4 * A ** 2 - mp.mpf(9) / 4 * R + M,
     4: -mp.mpf(393) / 4 * A ** 3 - mp.mpf(11) / 2 * A * M - 9 * A * T + mp.mpf(117) / 4 * A * R
        - mp.mpf(3) / 2 * M * N - 6 * P4 - mp.mpf(165) / 8 * U + mp.mpf(9) / 4 * V}
b[5] = (mp.mpf(64341) / 128 * A ** 4 + mp.mpf(2145) / 64 * A ** 2 * M - mp.mpf(17001) / 64 * A ** 2 * R
        + mp.mpf(1053) / 16 * A ** 2 * T + mp.mpf(393) / 32 * A * M * N + 63 * A * P4
        + mp.mpf(14907) / 64 * A * U - mp.mpf(603) / 32 * A * V + 87 * K + mp.mpf(51) / 4 * L
        + mp.mpf(3) / 4 * M ** 2 + mp.mpf(81) / 64 * M * N ** 2 - mp.mpf(9) / 8 * M * R + M * T
        + mp.mpf(81) / 64 * M * Jm + 24 * P5 + mp.mpf(1839) / 128 * R ** 2
        - mp.mpf(153) / 16 * R * T + mp.mpf(7) / 4 * T ** 2 + mp.mpf(565) / 128 * X
        - mp.mpf(1311) / 8 * Z)
c = {1: mp.mpf(1), 2: -A, 3: mp.mpf(7) / 2 * A ** 2 - R / 2 + M / 3,
     4: -mp.mpf(127) / 8 * A ** 3 - mp.mpf(7) / 6 * A * M - A * T / 2 + mp.mpf(51) / 8 * A * R
        - M * N / 2 - mp.mpf(57) / 16 * U + mp.mpf(3) / 8 * V}
c[5] = (mp.mpf(10549) / 128 * A ** 4 + mp.mpf(411) / 64 * A ** 2 * M - mp.mpf(3561) / 64 * A ** 2 * R
        + mp.mpf(89) / 16 * A ** 2 * T + mp.mpf(99) / 32 * A * M * N + 3 * A * P4
        + mp.mpf(2531) / 64 * A * U - mp.mpf(75) / 32 * A * V + 21 * K + mp.mpf(5) / 4 * L
        + M ** 2 / 4 + mp.mpf(27) / 64 * M * N ** 2 - M * R / 8 + mp.mpf(27) / 64 * M * Jm
        + mp.mpf(463) / 128 * R ** 2 - mp.mpf(21) / 16 * R * T + mp.mpf(415) / 384 * X
        - mp.mpf(139) / 8 * Z)
# our note: gd:bc3, gs:b4, gs:c4, gs:D5 (with Q)
b3o = 6 * Q + mp.mpf(87) / 4 * A ** 2 - mp.mpf(9) / 4 * R + M
c3o = mp.mpf(7) / 2 * A ** 2 - R / 2 + M / 3
b4o = (-mp.mpf(393) / 4 * A ** 3 - mp.mpf(11) / 2 * A * M - 54 * A * Q + mp.mpf(117) / 4 * A * R
       - mp.mpf(3) / 2 * M * N - 6 * P4 - mp.mpf(165) / 8 * U + mp.mpf(9) / 4 * V)
c4o = (-mp.mpf(127) / 8 * A ** 3 - mp.mpf(7) / 6 * A * M - 3 * A * Q + mp.mpf(51) / 8 * A * R
       - M * N / 2 - mp.mpf(57) / 16 * U + mp.mpf(3) / 8 * V)
D5rem = (-mp.mpf(16347) / 64 * A ** 4 - mp.mpf(57) / 4 * A ** 2 * M - mp.mpf(1179) / 4 * A ** 2 * Q
         + mp.mpf(3159) / 32 * A ** 2 * R - 3 * A * M * N - mp.mpf(3657) / 32 * A * U
         + mp.mpf(189) / 16 * A * V - 24 * K - 6 * M * Q + mp.mpf(3) / 4 * M * R
         + mp.mpf(135) / 4 * Q * R - mp.mpf(225) / 64 * R ** 2 - mp.mpf(75) / 64 * X
         + mp.mpf(447) / 4 * Z)
D5o = D5rem - 54 * A * P4 - 9 * L - 63 * Q ** 2 - 24 * P5
check("b3: OPE = ours (gd:bc3)", b[3], b3o, tiny)
check("c3: OPE = ours (gd:bc3)", c[3], c3o, tiny)
check("b4: OPE = ours (gs:b4)", b[4], b4o, tiny)
check("c4: OPE = ours (gs:c4)", c[4], c4o, tiny)
check("3c5 - b5: OPE (eqs.b5, c5) = our D5 (gs:D5)", 3 * c[5] - b[5], D5o, tiny)
# package's numeric task report (results/verification/a6_numeric) and our 2026-09 five-loop numerics
pkg_b = {3: "1070.80186962985612025246988235021214480318611066103358233431",
         4: "-47582.7301057819079763235800164651599259760377196070992075641",
         5: "2646702.31225018121307481895467733737453249630835039678538109"}
pkg_c = {3: "116.587670440098277180208476113494262214507414391270396765745",
         4: "-3568.11172840717368300667356906010665227832564569736098836947",
         5: "143230.801298955513414232425317342816065615379615620174724212"}
for n in (3, 4, 5):
    check(f"b{n}(1): formula vs package numeric report", b[n], pkg_b[n], mp.mpf("1e-55"))
    check(f"c{n}(1): formula vs package numeric report", c[n], pkg_c[n], mp.mpf("1e-55"))
ours_num = {"b": {3: "1070.8018696298561", 4: "-47582.73010578191", 5: "2646702.236439145"},
            "c": {3: "116.58767044009828", 4: "-3568.111728407175", 5: "143230.79505148454"}}
for n in (3, 4):
    check(f"b{n}(1) vs our 2026-09 five-loop numerics", b[n], ours_num["b"][n], mp.mpf("1e-13"))
    check(f"c{n}(1) vs our 2026-09 five-loop numerics", c[n], ours_num["c"][n], mp.mpf("1e-13"))
check("b5(1) vs our 2026-09 five-loop numerics", b[5], ours_num["b"][5], mp.mpf("1e-7"),
      "numerical graph integration; its C5 is 1.1e-7 off the exact value")
check("c5(1) vs our 2026-09 five-loop numerics", c[5], ours_num["c"][5], mp.mpf("1e-7"),
      "numerical graph integration")
# Two-channel five-loop graph sums at quadrature degree 18 (lri_numerical_resolution records
# amplitude5_{maxgap,span}_18.json), MS-assembled with degree-28 lower loops for the C6(1) production in
# LRI_C6_1D_HPC/reference/assembly_lower6.json (keys maxgap_28, span_28; beta[4], gamma[4]).
deg28 = {"maxgap": ("2646702.31224394467901580418548154371067369", "143230.8012979120184009172948656202742237704"),
         "span": ("2646702.31224874171285698698955874811768955", "143230.80129870486627788288811165261517435575")}
for cut, (bb5, cc5) in deg28.items():
    check(f"b5(1) vs five-loop graph sums, degree 18 ({cut})", b[5], bb5, mp.mpf("1e-10"),
          "LRI_C6_1D_HPC/reference/assembly_lower6.json")
    check(f"c5(1) vs five-loop graph sums, degree 18 ({cut})", c[5], cc5, mp.mpf("1e-10"),
          "LRI_C6_1D_HPC/reference/assembly_lower6.json")
# The research bundle's analytic certificate split (2634163.41, 139051.17; eps5_derivation/RESULTS5.md) omits the
# 28 zero-weight classes; it has the same 3c5 - b5 but would move a6(1) through -2/243 b5 in eq.(h4uncollected).
b5_cert = mp.mpf("2634163.41")
print(f"   a6(1) shift if b5 had the certificate value: {mp.nstr(a2 * (-mp.mpf(2) / 243) * (b5_cert - b[5]), 6)}")


# C_n from the RG functions by Lagrange inversion (OPE eq.Lagrange; our sec:RG)
def series_mul(x, y, n):
    return [mp.fsum(x[i] * y[k - i] for i in range(k + 1)) for k in range(n)]


def series_pow(x, p, n):
    out = [mp.mpf(1)] + [mp.mpf(0)] * (n - 1)
    for _ in range(p):
        out = series_mul(out, x, n)
    return out


def series_inv(x, n):
    out = [1 / x[0]]
    for k in range(1, n):
        out.append(-mp.fsum(x[i] * out[k - i] for i in range(1, k + 1)) / x[0])
    return out


Bser = [b[1], b[2], b[3], b[4], b[5]]
gp = [c[1], 2 * c[2], 3 * c[3], 4 * c[4], 5 * c[5]]
CL = {}
for n in range(2, 6):
    s = series_mul(gp, series_pow(series_inv(Bser, 5), n, 5), 5)
    CL[n] = s[n - 1] / n
for n, ref in ((2, C2), (3, C3), (4, C4), (5, C5)):
    check(f"C{n}(1) by Lagrange inversion of the OPE RG input", CL[n], ref, tiny)
# the fixed point eq.(fixedpoint): solve beta(g) = 0 at small eps and compare with the series
for e in (mp.mpf("1e-3"), mp.mpf("1e-4")):
    beta = lambda g: -e * g + g * mp.fsum(Bser[i] * g ** (i + 1) for i in range(5))
    gs = mp.findroot(lambda g: beta(g) / g, e / 3)
    ser = (e / 3 + 2 * A / 9 * e ** 2 + (8 * A ** 2 / 27 - b[3] / 81) * e ** 3
           + (40 * A ** 3 / 81 - (10 * A * b[3] + b[4]) / 243) * e ** 4
           + (672 * A ** 4 - 84 * A ** 2 * b[3] - 12 * A * b[4] + b[3] ** 2 - b[5]) / 729 * e ** 5)
    print(f"   g* series check at eps={mp.nstr(e, 2)}: |root-series|/eps^6 = {mp.nstr(abs(gs - ser) / e ** 6, 6)}")
    rows.append(dict(name=f"g* series residual / eps^6 at eps={mp.nstr(e, 2)}",
                     got=mp.nstr(abs(gs - ser) / e ** 6, 10), ok=True, info=True, note="should be O(1), similar at both eps"))

# ---------------------------------------------------------------- uncollected h4: C_x and M cancel
print("== eq.(h4uncollected): W4, W5, W6 and b5 reproduce h4 for any C_x")
for Cx in (mp.mpf(0), mp.mpf(17), mp.mpf(-3) / 7):
    W4 = (A ** 4 / 384 + 7 * A ** 2 * M / 288 + 7 * A ** 2 * R / 64 + 7 * A * M * N / 144
          + 11 * A * U / 192 - 47 * A * V / 96 + Cx / 4 + 7 * M * N ** 2 / 288 - M * Jm / 288
          + 103 * R ** 2 / 128 + 85 * X / 96)
    W5 = (113 * A ** 4 / 576 + 55 * A ** 2 * M / 96 + 713 * A ** 2 * R / 96 + 55 * A * M * N / 48
          + 619 * A * U / 288 - 2071 * A * V / 144 + mp.mpf(9) / 2 * Cx + 55 * M * N ** 2 / 96
          + 7 * M * R / 12 + 7 * M * Jm / 96 + 643 * R ** 2 / 64 + R * T / 4 + 2179 * X / 192
          - 5 * Z / 12)
    W6 = (1139 * A ** 4 / 128 + 1697 * A ** 2 * M / 192 + 9057 * A ** 2 * R / 64
          + 3 * A ** 2 * T / 16 + 1513 * A * M * N / 96 + 2549 * A * U / 64 - 6545 * A * V / 32
          + mp.mpf(189) / 4 * Cx + 5 * K + L / 4 + 11 * M ** 2 / 108 + 459 * M * N ** 2 / 64
          + 89 * M * R / 8 + 123 * M * Jm / 64 + 11345 * R ** 2 / 128 + 77 * R * T / 16
          + 40211 * X / 384 - 89 * Z / 8)
    h4u = (4811 * A ** 4 / 1296 + 23 * A ** 2 * M / 162 - 839 * A ** 2 * R / 216
           + 253 * A ** 2 * T / 486 - 2 * A * M * N / 81 + 56 * A * P4 / 81 + 521 * A * U / 324
           + mp.mpf(2) / 3 * A * V - M ** 2 / 729 - M * R / 18 + 2 * M * T / 243
           - 161 * R ** 2 / 144 - 13 * R * T / 162 + 7 * T ** 2 / 729 - 35 * X / 24
           + 10 * W4 - mp.mpf(4) / 3 * W5 + mp.mpf(2) / 27 * W6 - mp.mpf(2) / 243 * b[5])
    check(f"h4 uncollected (C_x={mp.nstr(Cx, 4)}) = h4 collected", h4u, h[4], mp.mpf(10) ** (10 - args.dps))

# ---------------------------------------------------------------- low-order OPE-ratio route
print("== low-order OPE-ratio route (eqs. r12, Rcheck) and the bulk-leg integral (eq. Jgamma)")
r1 = mp.gamma(1 - q) * mp.gamma(2 * q) / (3 * mp.sqrt(6) * mp.gamma(1 + q))
r2 = -r1 / 12 * (13 * psi(0, q) + 3 * psi(0, -q) - 8 * psi(0, 2 * q) - 8 * psi(0, 1))
F0 = mp.gamma(2 * q) * mp.gamma(q) / (mp.gamma(4 * q) * mp.gamma(-q))
check("a2 = F0 r1^2", F0 * r1 ** 2, a2, tiny)
check("a3 = F0 (2 r1 r2 + B0 r1^2/4)", F0 * (2 * r1 * r2 + B[0] / 4 * r1 ** 2), a[3], tiny)


def Jgamma(d, aa, bb):
    return (pi ** d * mp.gamma(d / 2 - bb) * mp.gamma(2 * aa + bb - d) * mp.gamma(aa + bb - d / 2) ** 2
            / (mp.gamma(aa) ** 2 * mp.gamma(d / 2) * mp.gamma(2 * aa + 2 * bb - d)))


# a2 = J_d(q, 3q) / (54 kappa_d^2), kappa_1 = 1
check("a2 = J_1(1/4, 3/4)/54 (eq.a2derive, continued)", Jgamma(1, q, 3 * q) / 54, a2, tiny)
# Published low-order formulas of Behan, Lauria, Nocchi, van Vliet, arXiv:2311.02742v6, at p = d = 1:
# Eq. (3.34) R^(1), R^(2); Eq. (3.35) the Ising quadratic coefficient; Eq. (3.47) the long-range O(N) cubic at N = 1.
pp = mp.mpf(1)
g_ = mp.gamma
R1b = g_(1 - pp / 4) * g_(pp / 2) / (3 * mp.sqrt(6) * g_(pp / 4 + 1))
R2b = -g_(1 - pp / 4) * g_(pp / 2) / (36 * mp.sqrt(6) * g_(pp / 4 + 1)) * (
    13 * psi(0, pp / 4) + 3 * psi(0, -pp / 4) - 8 * psi(0, pp / 2) - 8 * psi(0, 1))
check("BLNV (3.34) R^(1) = r1 at d=1", R1b, r1, tiny)
check("BLNV (3.34) R^(2) = r2 at d=1", R2b, r2, tiny)
a2_335 = -g_(pp / 2) ** 2 / (3 * mp.sqrt(6) * g_(pp)) * R1b
check("BLNV (3.35) quadratic coefficient (Ising) = a2(1)", a2_335, a2, tiny)
NN = 1
a3_347 = -(NN + 2) * g_(1 - pp / 4) * g_(pp / 2) ** 3 / (8 * (NN + 8) ** 4 * g_(pp / 4 + 1) * g_(pp)) * (
    (NN ** 2 - 144 * NN - 640) * psi(0, pp / 4) - (NN + 8) ** 2 * psi(0, -pp / 4)
    + 16 * (5 * NN + 22) * psi(0, pp / 2) + 16 * (5 * NN + 22) * psi(0, 1))
check("BLNV (3.47) O(N) cubic coefficient at N=1 = a3(1)", a3_347, a[3], tiny)
a2_347 = (NN + 2) * g_(1 - pp / 4) * g_(pp / 2) ** 3 / (2 * (NN + 8) ** 2 * g_(pp / 4 + 1) * g_(pp))
check("BLNV (3.47) O(N) quadratic at N=1 = -a2(1) (printed sign opposite)", a2_347, -a2, tiny,
      "documents the sign inconsistency of the printed (3.47) quadratic term")
a3_335 = -(g_(pp / 2) ** 3 * g_(1 - pp / 2) * g_(1 - pp / 4)) / (216 * g_(pp / 4 + 1) * g_(pp + 1)) * (
    4 - g_(pp / 4) ** 2 * g_(1 - pp / 4) ** 2 / (g_(pp / 2) * g_(-pp / 2))
    - 96 * mp.sqrt(6) * g_(pp / 4 + 1) / (g_(-pp / 4) * g_(pp / 2)) * R2b)
rows.append(dict(name="BLNV (3.35) cubic coefficient read literally at d=1 (disagrees)", got=mp.nstr(a3_335, 15),
                 ref=mp.nstr(a[3], 15), ok=True, info=True, note="printed-formula inconsistency, recorded not checked"))
print(f"INFO  BLNV (3.35) cubic read literally: {mp.nstr(a3_335, 12)} against a3(1) = {mp.nstr(a[3], 12)}")
if not args.skip_quad:
    with mp.workdps(20):
        pts = [0, mp.mpf(1) / 4, 1, 4, 16, 64, 256, 1024, mp.inf]
        for aa, bb in ((mp.mpf(1), mp.mpf("0.3")), (mp.mpf("1.5"), mp.mpf("0.25"))):
            # y = x + t: J = 2 int_0^inf t^(-2b) F(t) dt, F(t) = int dx (1+x^2)^(-a) (1+(x+t)^2)^(-a)
            F = lambda t: mp.quad(lambda x: ((1 + x ** 2) * (1 + (x + t) ** 2)) ** (-aa),
                                  [-mp.inf, -t - 4, -t, -t / 2, 0, 4, mp.inf])
            I = 2 * mp.quad(lambda t: t ** (-2 * bb) * F(t), pts)
            check(f"J_1({mp.nstr(aa, 2)},{mp.nstr(bb, 2)}): Gamma formula vs direct quadrature", I,
                  Jgamma(1, aa, bb), mp.mpf("1e-8"), "convergent region, 20-digit quadrature")

# ---------------------------------------------------------------- 1d functional cross-check
print("== one-dimensional functional cross-check (Ghosh, Paulos, Suchel, Zheng, arXiv:2603.22395v1)")
check("gamma_0^(1) = C1 + 1/2 = 1/3 (their eq. for gamma_0^(1))", mp.mpf(-1) / 6 + mp.mpf(1) / 2,
      mp.mpf(1) / 3, tiny)
check("gamma_0^(2) = (pi + log 16)/9 = C2(1)", (pi + mp.log(16)) / 9, C2, tiny)
check("their C3 quote: (-alpha_I4 + pi^2 + (pi+log4) log64)/81 with alpha_I4 = 6Q",
      (-6 * Q + pi ** 2 + (pi + mp.log(4)) * mp.log(64)) / 81, C3, tiny,
      "their perturbative-data section, citing Benedetti et al.; alpha_I4 ~ 330")
check("alpha_I4 = 6 Q_1 = T_1 ~ 330", T, 330, mp.mpf("1e-4"))

# rows marked info=True are recorded diagnostics, not checks, and are tallied separately
npass = sum(1 for x in rows if x["ok"] and not x.get("info"))
nfail = sum(1 for x in rows if not x["ok"])
ninfo = sum(1 for x in rows if x.get("info"))
print(f"\nSUMMARY: {npass} PASS, {nfail} FAIL, {ninfo} INFO (recorded, not checked)")
print(f"   a_2..a_6(1) = " + ", ".join(mp.nstr(a[n], 15) for n in range(2, 7)))
print(f"   b5(1) = {mp.nstr(b[5], 20)}, c5(1) = {mp.nstr(c[5], 20)}, Omega_1 = {mp.nstr(Omega, 20)}")
if args.json:
    out = dict(dps=args.dps, mpmath=mp.__version__, python=sys.version.split()[0], rows=rows,
               values={**{f"a{n}": mp.nstr(a[n], 50) for n in range(2, 7)},
                       **{f"ell{j}": mp.nstr(ell[j], 50) for j in range(1, 5)},
                       "Omega1": mp.nstr(Omega, 50), "b5": mp.nstr(b[5], 50), "c5": mp.nstr(c[5], 50),
                       **{f"C{n}": mp.nstr(v, 50) for n, v in ((2, C2), (3, C3), (4, C4), (5, C5))}},
               summary=dict(passed=npass, failed=nfail, info=ninfo))
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1)
sys.exit(1 if nfail else 0)
