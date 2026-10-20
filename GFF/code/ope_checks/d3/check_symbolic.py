#!/usr/bin/env python3
"""C63d, review of the OPE package (2026-10-16): exact symbolic checks written independently of the package code.

The package formulas are transcribed from note/lri_ope_note.tex; the condensed-note formulas from
GFF/LRI_condensed_note (gs:C0C4, gs:C5, gd:bc3, gs:b4, gs:c4, gs:D5). T = 6 Q throughout.
Checks:
  S1 package C2..C5 == note C2..C5
  S2 package b3, c3, b4, c4 == note; package 3 c5 - b5 == note D5
  S3 Lagrange inversion with the package b_j, c_j gives the note's C2..C5
  S4 package fixed point g_* (eq:fixedpoint) and bare-coupling recursion (eq:bare)
  S5 uncollected h4 (eq:h4uncollected) + W4, W5, W6, b5 == collected h4 (eq:h4); M, N, Jm, Cx cancel
  S6 outer Gamma factor: log-expansion gives f_1..f_4 (eq:external-f)
  S7 log map: l_1..l_4 from h_j and the outer factor == eq:logmap1..4 with the note's C_j; also eq:h2thermal..h4thermal
  S8 eq:C4RG and the uncollected-to-thermal identity
Usage: python3 check_symbolic.py OUT.json
"""
import json
import sys

import sympy as sp

A, R, U, V, X, Q, P4, P5, K, L, Z, M, N, Jm, Cx = sp.symbols('A R U V X Q P4 P5 K L Z M N Jm Cx')
B0, B1, B2, B3 = sp.symbols('B0:4')
e, g = sp.symbols('epsilon g')
F = sp.Rational
T = 6 * Q
results = {}


def trunc(expr, var, n):
    p = sp.Poly(sp.expand(expr), var)
    return sp.Add(*[c * var**k[0] for k, c in p.terms() if k[0] <= n])


def tmul(a, b, var, n):
    return trunc(trunc(a, var, n) * trunc(b, var, n), var, n)


def tpow(a, k, var, n):
    out = sp.Integer(1)
    for _ in range(k):
        out = tmul(out, a, var, n)
    return out


def texp(x, var, n):
    # x has no constant term
    return sp.expand(sum(tpow(x, k, var, n) / sp.factorial(k) for k in range(n + 1)))


def tlog1p(x, var, n):
    return sp.expand(sum((-1)**(k + 1) * tpow(x, k, var, n) / k for k in range(1, n + 1)))


def same(name, lhs, rhs):
    ok = sp.expand(lhs - rhs) == 0
    results[name] = ok
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok:
        print('   difference:', sp.factor(sp.expand(lhs - rhs)))
    return ok


# ---------------- condensed note
C2n = A / 9
C3n = (A**2 + R - 8 * Q) / 108
C4n = (16 * P4 - A**3 - 8 * A * Q - 3 * A * R + F(53, 2) * U - 3 * V) / 648
C5n = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q**2 + 720 * A**2 * Q + 1008 * Q * R + 7152 * Z
       - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * X) / 46656
b3n = 6 * Q + F(87, 4) * A**2 - F(9, 4) * R + M
c3n = F(7, 2) * A**2 - R / 2 + M / 3
b4n = (-F(393, 4) * A**3 - F(11, 2) * A * M - 54 * A * Q + F(117, 4) * A * R - F(3, 2) * M * N - 6 * P4
       - F(165, 8) * U + F(9, 4) * V)
c4n = (-F(127, 8) * A**3 - F(7, 6) * A * M - 3 * A * Q + F(51, 8) * A * R - M * N / 2 - F(57, 16) * U
       + F(3, 8) * V)
D5rem = (-F(16347, 64) * A**4 - F(57, 4) * A**2 * M - F(1179, 4) * A**2 * Q + F(3159, 32) * A**2 * R
         - 3 * A * M * N - F(3657, 32) * A * U + F(189, 16) * A * V - 24 * K - 6 * M * Q + F(3, 4) * M * R
         + F(135, 4) * Q * R - F(225, 64) * R**2 - F(75, 64) * X + F(447, 4) * Z)
D5n = D5rem - 54 * A * P4 - 9 * L - 63 * Q**2 - 24 * P5

# ---------------- OPE package (note/lri_ope_note.tex)
C2p = A / 9
C3p = (A**2 + R) / 108 - T / 81
C4p = (16 * P4 - A**3 - F(4, 3) * A * T - 3 * A * R + F(53, 2) * U - 3 * V) / 648
C5p = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 48 * T**2 + 120 * A**2 * T + 168 * R * T + 7152 * Z
       - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * X) / 46656
b3p = T + F(87, 4) * A**2 - F(9, 4) * R + M
b4p = (-F(393, 4) * A**3 - F(11, 2) * A * M - 9 * A * T + F(117, 4) * A * R - F(3, 2) * M * N - 6 * P4
       - F(165, 8) * U + F(9, 4) * V)
c3p = F(7, 2) * A**2 - R / 2 + M / 3
c4p = (-F(127, 8) * A**3 - F(7, 6) * A * M - A * T / 2 + F(51, 8) * A * R - M * N / 2 - F(57, 16) * U
       + F(3, 8) * V)
b5p = (F(64341, 128) * A**4 + F(2145, 64) * A**2 * M - F(17001, 64) * A**2 * R + F(1053, 16) * A**2 * T
       + F(393, 32) * A * M * N + 63 * A * P4 + F(14907, 64) * A * U - F(603, 32) * A * V + 87 * K
       + F(51, 4) * L + F(3, 4) * M**2 + F(81, 64) * M * N**2 - F(9, 8) * M * R + M * T + F(81, 64) * M * Jm
       + 24 * P5 + F(1839, 128) * R**2 - F(153, 16) * R * T + F(7, 4) * T**2 + F(565, 128) * X
       - F(1311, 8) * Z)
c5p = (F(10549, 128) * A**4 + F(411, 64) * A**2 * M - F(3561, 64) * A**2 * R + F(89, 16) * A**2 * T
       + F(99, 32) * A * M * N + 3 * A * P4 + F(2531, 64) * A * U - F(75, 32) * A * V + 21 * K + F(5, 4) * L
       + F(1, 4) * M**2 + F(27, 64) * M * N**2 - F(1, 8) * M * R + F(27, 64) * M * Jm + F(463, 128) * R**2
       - F(21, 16) * R * T + F(415, 384) * X - F(139, 8) * Z)
W4 = (A**4 / 384 + F(7, 288) * A**2 * M + F(7, 64) * A**2 * R + F(7, 144) * A * M * N + F(11, 192) * A * U
      - F(47, 96) * A * V + Cx / 4 + F(7, 288) * M * N**2 - M * Jm / 288 + F(103, 128) * R**2 + F(85, 96) * X)
W5 = (F(113, 576) * A**4 + F(55, 96) * A**2 * M + F(713, 96) * A**2 * R + F(55, 48) * A * M * N
      + F(619, 288) * A * U - F(2071, 144) * A * V + F(9, 2) * Cx + F(55, 96) * M * N**2 + F(7, 12) * M * R
      + F(7, 96) * M * Jm + F(643, 64) * R**2 + R * T / 4 + F(2179, 192) * X - F(5, 12) * Z)
W6 = (F(1139, 128) * A**4 + F(1697, 192) * A**2 * M + F(9057, 64) * A**2 * R + F(3, 16) * A**2 * T
      + F(1513, 96) * A * M * N + F(2549, 64) * A * U - F(6545, 32) * A * V + F(189, 4) * Cx + 5 * K + L / 4
      + F(11, 108) * M**2 + F(459, 64) * M * N**2 + F(89, 8) * M * R + F(123, 64) * M * Jm
      + F(11345, 128) * R**2 + F(77, 16) * R * T + F(40211, 384) * X - F(89, 8) * Z)
h4unc = (F(4811, 1296) * A**4 + F(23, 162) * A**2 * M - F(839, 216) * A**2 * R + F(253, 486) * A**2 * T
         - F(2, 81) * A * M * N + F(56, 81) * A * P4 + F(521, 324) * A * U + F(2, 3) * A * V - M**2 / 729
         - M * R / 18 + F(2, 243) * M * T - F(161, 144) * R**2 - F(13, 162) * R * T + F(7, 729) * T**2
         - F(35, 24) * X + 10 * W4 - F(4, 3) * W5 + F(2, 27) * W6 - F(2, 243) * b5p)
h1 = F(4, 3) * A
h2 = F(25, 36) * A**2 + R / 6 - F(2, 27) * T
h3 = F(17, 108) * A**3 + A * R / 12 - F(2, 27) * A * T + F(4, 27) * P4 + F(71, 216) * U - V / 36
h4 = (-F(7, 5184) * A**4 - F(7, 288) * A**2 * R - F(7, 972) * A**2 * T + F(14, 81) * A * P4
      + F(301, 864) * A * U - F(7, 144) * A * V - F(28, 81) * K - F(7, 81) * L - F(16, 81) * P5
      - F(103, 5184) * R**2 + F(7, 324) * R * T - F(7, 1458) * T**2 - F(61, 3888) * X + F(175, 162) * Z)
Omega = 13 * Z - L - 12 * K

# S1
same('S1 C2 package == note', C2p, C2n)
same('S1 C3 package == note', C3p, C3n)
same('S1 C4 package == note', C4p, C4n)
same('S1 C5 package == note', C5p, C5n)
# S2
same('S2 b3 package == note gd:bc3', b3p, b3n)
same('S2 c3 package == note gd:bc3', c3p, c3n)
same('S2 b4 package == note gs:b4', b4p, b4n)
same('S2 c4 package == note gs:c4', c4p, c4n)
same('S2 3c5-b5 package == note D5 (gs:D5)', 3 * c5p - b5p, D5n)


# S3 Lagrange inversion, Delta_E = (d-eps)/2 + gamma_r(g_*), eps = g B(g)
def lagrange(bs, cs):
    y = sum(bs[j] * g**(j - 1) for j in range(2, 6)) / 3     # B = 3 (1 + y)
    gam = g + sum(cs[j] * g**j for j in range(2, 6))
    out = {}
    for n in range(2, 6):
        inv = sum(sp.binomial(-n, k) * tpow(y, k, g, n - 1) for k in range(n)) / sp.Integer(3)**n
        ser = tmul(sp.diff(gam, g), inv, g, n - 1)
        out[n] = sp.expand(sp.Poly(ser, g).coeff_monomial(g**(n - 1)) / n)
    return out


Cl = lagrange({2: -6 * A, 3: b3p, 4: b4p, 5: b5p}, {2: -A, 3: c3p, 4: c4p, 5: c5p})
for n, Cn in zip(range(2, 6), (C2n, C3n, C4n, C5n)):
    same(f'S3 Lagrange C{n} (package RG input) == note C{n}', Cl[n], Cn)

# S4 fixed point and bare coupling
bseries = -e * g + 3 * g**2 - 6 * A * g**3 + b3p * g**4 + b4p * g**5 + b5p * g**6
gs_pkg = (e / 3 + 2 * A / 9 * e**2 + (8 * A**2 / 27 - b3p / 81) * e**3
          + (40 * A**3 / 81 - (10 * A * b3p + b4p) / 243) * e**4
          + (672 * A**4 - 84 * A**2 * b3p - 12 * A * b4p + b3p**2 - b5p) / 729 * e**5)
resid = trunc(-e * gs_pkg + sum(cf * tpow(gs_pkg, k, e, 6) for cf, k in ((3, 2), (-6 * A, 3), (b3p, 4), (b4p, 5), (b5p, 6))), e, 6)
same('S4 beta(g_*) = O(eps^7) with eq:fixedpoint', resid, 0)
bl = {1: 3, 2: -6 * A, 3: b3p}
G = {1: sp.Integer(1)}
for n in range(2, 5):
    G[n] = sp.expand(sum(bl[l] * (n - l) * G[n - l] for l in range(1, n)) / ((n - 1) * e))
same('S4 G2 (eq:bare)', G[2], 3 / e)
same('S4 G3 (eq:bare)', G[3], 9 / e**2 - 3 * A / e)
same('S4 G4 (eq:bare)', G[4], 27 / e**3 - 21 * A / e**2 + b3p / (3 * e))

# S5 uncollected -> collected h4
same('S5 h4 uncollected (W4,W5,W6,b5) == boxed h4', h4unc, h4)
results['S5 Cx cancels in 10W4-4/3W5+2/27W6'] = sp.expand(10 * W4 - F(4, 3) * W5 + F(2, 27) * W6).coeff(Cx) == 0
print('PASS' if results['S5 Cx cancels in 10W4-4/3W5+2/27W6'] else 'FAIL', 'S5 Cx cancels')

# S6 outer factor: log[Gamma(-q-e/4)Gamma(q)/(Gamma(q-e/4)Gamma(-q))] = sum_k (-1/4)^k B_{k-1} e^k / k!
Bs = [B0, B1, B2, B3]
logF = sum((-F(1, 4))**k * Bs[k - 1] * e**k / sp.factorial(k) for k in range(1, 5))
fser = texp(logF, e, 4)
f = [sp.Poly(fser, e).coeff_monomial(e**k) for k in range(5)]
same('S6 f1', f[1], -B0 / 4)
same('S6 f2', f[2], (B0**2 + B1) / 32)
same('S6 f3', f[3], -(B0**3 + 3 * B0 * B1 + B2) / 384)
same('S6 f4', f[4], (B0**4 + 6 * B0**2 * B1 + 3 * B1**2 + 4 * B0 * B2 + B3) / 6144)

# S7 log map
hs = 1 + h1 * e + h2 * e**2 + h3 * e**3 + h4 * e**4
lser = sp.expand(logF + tlog1p(hs - 1, e, 4))
l = [sp.Poly(lser, e).coeff_monomial(e**k) for k in range(5)]
same('S7 l1 (eq:logmap1)', l[1], 12 * C2n - B0 / 4)
same('S7 l2 (eq:logmap2)', l[2], 6 * C3n - A**2 / 4 + R / 9 + B1 / 32)
same('S7 l3 (eq:logmap3)', l[3], 6 * C4n - 3 * A * C3n + F(19, 324) * A**3 - A * R / 12 + U / 12 - B2 / 384)
same('S7 l4 (eq:logmap4)', l[4],
     6 * C5n - 3 * A * C4n + (A**2 - F(5, 6) * R) * C3n - 9 * C3n**2 - F(11, 576) * A**4 + F(37, 864) * A**2 * R
     - F(53, 2592) * A * U - F(5, 432) * A * V - F(53, 5184) * R**2 - F(47, 7776) * X + Omega / 81 + B3 / 6144)
same('S7 h2 thermal (eq:h2thermal)', h2, 6 * C3n + F(23, 36) * A**2 + R / 9)
same('S7 h3 thermal (eq:h3thermal)', h3, 6 * C4n + 5 * A * C3n + F(13, 108) * A**3 + F(7, 108) * A * R + U / 12)
same('S7 h4 thermal (eq:h4thermal)', h4,
     6 * C5n + 5 * A * C4n + (5 * A**2 - R) / 6 * C3n + 9 * C3n**2 - A**4 / 5184 + F(7, 2592) * A**2 * R
     + F(235, 2592) * A * U - F(5, 432) * A * V - F(7, 1728) * R**2 - F(47, 7776) * X + Omega / 81)
# exp map (eq:exp-map) is the Taylor series of exp(sum l_j e^j); check a_n/a_2 = convolution of h and f
conv = texp(lser, e, 4)
hf = tmul(texp(logF, e, 4), hs, e, 4)
same('S7 exp(log map) == convolution h*f', conv, hf)
# Omega_d is the only master combination left: l4 - (its C, A, R, U, V, X, B3 terms) depends on K, L, Z only via Omega
# S8 eq:C4RG
same('S8 243 C4 = 60A^3 - 8A b3 + 18A c3 + 3c4 - b4', 243 * C4n, 60 * A**3 - 8 * A * b3p + 18 * A * c3p + 3 * c4p - b4p)

ok = all(results.values())
print('ALL PASS' if ok else 'SOME FAIL', f'({sum(results.values())}/{len(results)})')
json.dump({'checks': results, 'all_pass': ok}, open(sys.argv[1], 'w'), indent=1)
sys.exit(0 if ok else 1)
