#!/usr/bin/env python3
"""C63d, review of the OPE package (2026-10-16): numerical checks written independently of the package code.

Inputs are this project's own values (GFF/LRI_condensed_note, LRI_C5_d3/masters_d3.json), never the package JSON.
  N1  d=2: the M-dependent parts of the package b5, c5 against the note's MS power sums b_5^p, c_5^p (done:powerSums)
  N2  a^(2..6)(d) at d=1,2,3 from our masters through the package's closed formula (H_j and the outer Gamma factor)
  N3  the same coefficients from the note's status-table C_2..C_5 through the log map, with 13Z-L-12K from our masters
  N4  J_d(a,b) closed form against direct quadrature (d=1); bubble H(eps) jet
  N5  amplitude re-assembly through a^(5): F_2..F_5 of the package with g_*; poles cancel, finite parts = formula
  N6  four-vertex kernel S_4 through eps^0 from exact chains and kites; the symmetric kite from the note's Pattern A
      pole formula (gs:Apole); five-vertex finite table sums to the finite part of S_5
Usage: python3 check_numeric.py OUT.json
"""
import json
import sys

import mpmath as mp
import sympy as sp

mp.mp.dps = 60
out = {}


def rec(name, value, ref, tol):
    diff = abs(value - ref) / max(abs(ref), mp.mpf(1))
    ok = bool(diff < tol)
    out[name] = {'value': mp.nstr(value, 25), 'reference': mp.nstr(ref, 25), 'rel_diff': mp.nstr(diff, 3),
                 'tol': str(tol), 'pass': ok}
    print(('PASS ' if ok else 'FAIL ') + f'{name}: {mp.nstr(value, 20)} vs {mp.nstr(ref, 20)} (rel {mp.nstr(diff, 3)})',
          flush=True)
    return ok


def basis(d):
    q = mp.mpf(d) / 4
    b = {'q': q,
         'A': mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q),
         'R': mp.psi(1, 2 * q) - mp.psi(1, 1),
         'U': mp.psi(2, q),
         'V': mp.psi(2, 1) + mp.psi(2, 2 * q),
         'X': mp.psi(3, 2 * q) - mp.psi(3, 1),
         'M': mp.gamma(-q) * mp.gamma(2 * q)**2 / mp.gamma(3 * q),
         'N': mp.psi(0, -q) + mp.psi(0, 3 * q) - mp.psi(0, 1) - mp.psi(0, 2 * q),
         'Jm': mp.psi(1, -q) - mp.psi(1, 3 * q)}
    b['e'] = [mp.psi(j, -q) - mp.psi(j, q) for j in range(4)]   # the package's B_j
    return b


# ---------------- our masters
G = mp.catalan
F_m = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
F_p = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
B_m = mp.gamma(0.25)**4 * F_m
B_p = 64 * mp.pi**4 / mp.gamma(0.25)**4 * F_p


def Y(r):
    r = mp.mpf(r)
    return r / 8 * (mp.gamma((r + 2) / 8) / mp.gamma((r + 6) / 8))**7 * mp.hyper(
        [1, 1 + r / 8] + [(r + 2) / 8] * 7, [r / 8] + [(r + 6) / 8] * 7, -1)


c8, s8 = mp.cos(mp.pi / 8), mp.sin(mp.pi / 8)
X0, Xp, Xm = Y(2), c8**7 * Y(3) - s8**7 * Y(5), c8**7 * Y(1) + s8**7 * Y(7)
b1 = basis(1)
Q1 = mp.gamma(0.25)**4 / mp.pi
P4_1 = 13 * B_m - 3 * B_p
P5_1 = 16 * mp.pi**1.5 * (-35 * X0 + (22 * mp.sqrt(2) - 13) * Xp + (22 * mp.sqrt(2) + 13) * Xm)
psi1q, psi1qb = mp.psi(1, 0.25), mp.psi(1, 0.75)
masters = {
    1: dict(Q=Q1, P4=P4_1, P5=P5_1,
            K=(psi1q * (3 * psi1q - psi1qb) + b1['A'] * mp.psi(2, 0.25)) / 2,
            L=-(3 * b1['A'] - mp.pi) / 6 * P4_1 - 2 * mp.pi / 3 * B_m,
            Z=Q1 * (2 * mp.pi**2 / 3 + 8 * G)),
    2: dict(Q=mp.gamma(0.25)**8 / (24 * mp.pi**4), P4=(B_m**2 - B_p**2) / (4 * mp.pi**3),
            P5=8 / mp.pi * (25 * X0**2 - 28 * mp.sqrt(2) * X0 * (Xp + Xm) + 18 * (Xp**2 + Xm**2) + 28 * Xp * Xm),
            K=32 * G**2 - 28 * mp.zeta(3) * mp.log(2)),
    3: dict(Q=mp.mpf('5.01710256455385536959085484569018'), P4=mp.mpf('62.0583279434066724664633885840967'),
            P5=mp.mpf('240.340317759083549816366546388004'))}
masters[2]['L'] = -2 * mp.log(2) * masters[2]['P4']
masters[2]['Z'] = 4 * G * masters[2]['Q']
m3 = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
if m3:
    masters[3].update(K=mp.mpf(m3['K3']), L=mp.mpf(m3['L3']), Z=mp.mpf(m3['Z3']))
# note status table (Sec 1), as displayed
table = {1: ['0.657131263981', '-3.719856322902', '45.42488010356', '-731.13947662454'],
         2: ['0.308065413582', '-0.874850012653', '5.048868431', '-38.833645896'],
         3: ['0.181221785406', '-0.353581520433', '1.228063545', '-5.850351421']}
table_digits = {1: mp.mpf('1e-12'), 2: mp.mpf('1e-9'), 3: mp.mpf('1e-9')}


def thermal(b, m):
    A, R, U, V, X = b['A'], b['R'], b['U'], b['V'], b['X']
    Q, P4, P5, K, L, Z = m['Q'], m['P4'], m['P5'], m['K'], m['L'], m['Z']
    C2 = A / 9
    C3 = (A**2 + R - 8 * Q) / 108
    C4 = (16 * P4 - A**3 - 8 * A * Q - 3 * A * R + mp.mpf(53) / 2 * U - 3 * V) / 648
    C5 = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q**2 + 720 * A**2 * Q + 1008 * Q * R + 7152 * Z
          - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * X) / 46656
    return [C2, C3, C4, C5]


def hpoly(b, m):
    A, R, U, V, X = b['A'], b['R'], b['U'], b['V'], b['X']
    T, P4, P5, K, L, Z = 6 * m['Q'], m['P4'], m['P5'], m['K'], m['L'], m['Z']
    F = mp.mpf
    h1 = F(4) / 3 * A
    h2 = F(25) / 36 * A**2 + R / 6 - F(2) / 27 * T
    h3 = F(17) / 108 * A**3 + A * R / 12 - F(2) / 27 * A * T + F(4) / 27 * P4 + F(71) / 216 * U - V / 36
    h4 = (-F(7) / 5184 * A**4 - F(7) / 288 * A**2 * R - F(7) / 972 * A**2 * T + F(14) / 81 * A * P4
          + F(301) / 864 * A * U - F(7) / 144 * A * V - F(28) / 81 * K - F(7) / 81 * L - F(16) / 81 * P5
          - F(103) / 5184 * R**2 + F(7) / 324 * R * T - F(7) / 1458 * T**2 - F(61) / 3888 * X + F(175) / 162 * Z)
    return [mp.mpf(1), h1, h2, h3, h4]


def series_exp(c, n):
    # exp(sum_{j>=1} c[j] z^j) through z^n
    r = [mp.mpf(1)] + [mp.mpf(0)] * n
    for k in range(1, n + 1):
        r[k] = sum(j * c[j] * r[k - j] for j in range(1, k + 1)) / k
    return r


def outer(b):
    # log[Gamma(-q-e/4)Gamma(q)/(Gamma(q-e/4)Gamma(-q))] = sum_k (-1/4)^k B_{k-1} e^k / k!
    c = [0] + [(-mp.mpf(1) / 4)**k * b['e'][k - 1] / mp.factorial(k) for k in range(1, 5)]
    return series_exp(c, 4)


def a2(d):
    q = mp.mpf(d) / 4
    return -mp.gamma(1 - q) * mp.gamma(2 * q)**3 / (54 * mp.gamma(1 + q) * mp.gamma(4 * q))


def coeffs_masters(d):
    b, m = basis(d), masters[d]
    h, f = hpoly(b, m), outer(b)
    return [a2(d) * sum(h[j] * f[n - j] for j in range(n + 1)) for n in range(5)]


def coeffs_logmap(d, C, omega):
    b = basis(d)
    A, R, U, V, X, e = b['A'], b['R'], b['U'], b['V'], b['X'], b['e']
    C2, C3, C4, C5 = C
    F = mp.mpf
    l1 = 12 * C2 - e[0] / 4
    l2 = 6 * C3 - A**2 / 4 + R / 9 + e[1] / 32
    l3 = 6 * C4 - 3 * A * C3 + F(19) / 324 * A**3 - A * R / 12 + U / 12 - e[2] / 384
    l4 = (6 * C5 - 3 * A * C4 + (A**2 - F(5) / 6 * R) * C3 - 9 * C3**2 - F(11) / 576 * A**4 + F(37) / 864 * A**2 * R
          - F(53) / 2592 * A * U - F(5) / 432 * A * V - F(53) / 5184 * R**2 - F(47) / 7776 * X + omega / 81
          + e[3] / 6144)
    r = series_exp([0, l1, l2, l3, l4], 4)
    return [a2(d) * x for x in r]


# ---------------- N1: d=2 power sums
b = basis(2)
A, R, M, N, Jm, T = b['A'], b['R'], b['M'], b['N'], b['Jm'], 6 * masters[2]['Q']
F = mp.mpf
b5M = (F(2145) / 64 * A**2 * M + F(393) / 32 * A * M * N + F(3) / 4 * M**2 + F(81) / 64 * M * N**2 - F(9) / 8 * M * R
       + M * T + F(81) / 64 * M * Jm)
c5M = (F(411) / 64 * A**2 * M + F(99) / 32 * A * M * N + F(1) / 4 * M**2 + F(27) / 64 * M * N**2 - F(1) / 8 * M * R
       + F(27) / 64 * M * Jm)
rec('N1 d=2 b5 power part vs note b_5^p', b5M, mp.mpf('-1540.38932947914290838'), mp.mpf('1e-19'))
rec('N1 d=2 c5 power part vs note c_5^p', c5M, mp.mpf('-251.621917341000466476'), mp.mpf('1e-19'))
rec('N1 d=2 b3 power part M vs note b_3^p=-4', M, mp.mpf(-4), mp.mpf('1e-50'))
rec('N1 d=2 b4 power part vs note 16A+24', -F(11) / 2 * A * M - F(3) / 2 * M * N, 16 * A + 24, mp.mpf('1e-50'))

# ---------------- N2, N3
values = {}
for d in (1, 2, 3):
    if 'K' not in masters[d]:
        continue
    th = thermal(basis(d), masters[d])
    for j, (cv, tv) in enumerate(zip(th, table[d])):
        rec(f'N2 d={d} C{j + 2} from our masters vs status table', cv, mp.mpf(tv), table_digits[d] * 10)
    am = coeffs_masters(d)
    m = masters[d]
    omega = 13 * m['Z'] - m['L'] - 12 * m['K']
    al = coeffs_logmap(d, [mp.mpf(t) for t in table[d]], omega)
    alx = coeffs_logmap(d, th, omega)
    values[d] = {'a': [mp.nstr(x, 30) for x in am], 'omega': mp.nstr(omega, 30)}
    for n in range(5):
        rec(f'N3 d={d} a^({n + 2}) log map with exact C_j == master route', alx[n], am[n], mp.mpf('1e-45'))
        rec(f'N3 d={d} a^({n + 2}) log map with status-table C_j vs master route', al[n], am[n],
            table_digits[d] * 1e3)
out['values'] = values

# ---------------- N4: J_d(a,b) and the bubble
d, a_, b_ = 1, mp.mpf('0.8'), mp.mpf('0.3')
Jgamma = (mp.pi**d * mp.gamma(mp.mpf(d) / 2 - b_) * mp.gamma(2 * a_ + b_ - d) * mp.gamma(a_ + b_ - mp.mpf(d) / 2)**2
          / (mp.gamma(a_)**2 * mp.gamma(mp.mpf(d) / 2) * mp.gamma(2 * a_ + 2 * b_ - d)))
mp.mp.dps = 20
# J_1(a,b) = int dx dy (1+x^2)^-a (1+y^2)^-a |x-y|^-2b ; s = x - y removes the singular line
inner = lambda s: mp.quad(lambda y: (1 + (y + s)**2)**(-a_) * (1 + y**2)**(-a_), [-mp.inf, -s, -s / 2, 0, mp.inf])
Jnum = 2 * mp.quad(lambda s: s**(-2 * b_) * inner(s), [0, mp.mpf(1) / 2, 2, 10, mp.inf])
mp.mp.dps = 60
rec('N4 J_1(0.8,0.3) Gamma formula vs quadrature', Jnum, Jgamma, mp.mpf('1e-10'))


def taylor_quad(fun, n, radius=mp.mpf('0.05'), npts=96):
    # Laurent/Taylor coefficients c_0..c_n of an analytic fun by the trapezoidal rule on a circle
    pts = [radius * mp.expj(2 * mp.pi * k / npts) for k in range(npts)]
    vals = [fun(z) for z in pts]
    return [mp.re(sum(v * z**(-j) for v, z in zip(vals, pts)) / npts) for j in range(n + 1)]


def bubble_times_eps(d):
    return lambda z: z * mp.gamma(mp.mpf(d) / 2) * mp.gamma(z / 2)**2 * mp.gamma(mp.mpf(d) / 2 - z) / (
        mp.gamma((d - z) / 2)**2 * mp.gamma(z))


for d in (mp.mpf(3), mp.mpf('2.6')):
    b = basis(d)
    c = taylor_quad(bubble_times_eps(d), 4)
    for k, ref in enumerate([4, 0, b['R'], -b['V'] / 2, b['R']**2 / 8 + 7 * b['X'] / 48]):
        rec(f'N4 d={mp.nstr(d, 3)} eps*H(eps) coefficient eps^{k}', c[k], mp.mpf(ref), mp.mpf('1e-40'))


# ---------------- N5: amplitude re-assembly through a^(5)
class Laurent:
    def __init__(self, c):           # dict power -> coefficient
        self.c = {k: v for k, v in c.items()}

    def __add__(self, o):
        o = o if isinstance(o, Laurent) else Laurent({0: o})
        r = dict(self.c)
        for k, v in o.c.items():
            r[k] = r.get(k, 0) + v
        return Laurent(r)

    __radd__ = __add__

    def __mul__(self, o):
        o = o if isinstance(o, Laurent) else Laurent({0: o})
        r = {}
        for k1, v1 in self.c.items():
            for k2, v2 in o.c.items():
                if k1 + k2 <= TOP:
                    r[k1 + k2] = r.get(k1 + k2, 0) + v1 * v2
        return Laurent(r)

    __rmul__ = __mul__


TOP = 5
E = Laurent({1: 1})
Einv = Laurent({-1: 1})


def Lser(d, n, order=8):
    q = mp.mpf(d) / 4

    def L(z):
        return (mp.gamma(2 * q) * mp.gamma(-q + (2 * n - 1) * z / 4) * mp.gamma(q - (2 * n + 1) * z / 4)
                * mp.gamma(2 * q - n * z / 2)**2 / (mp.gamma(q - z / 4)**2 * mp.gamma(4 * q - n * z)))
    return Laurent(dict(enumerate(taylor_quad(L, order))))


for d in (mp.mpf(3), mp.mpf('2.6')):
    b = basis(d)
    A, R, U, V, X, M, N = b['A'], b['R'], b['U'], b['V'], b['X'], b['M'], b['N']
    if d == 3:
        m = masters[3]
    else:   # generic d: the coefficient formula is polynomial in T, P4 (no master value is needed for a consistency test)
        m = dict(Q=mp.mpf('7.3'), P4=mp.mpf('91.7'))
    T, P4 = 6 * m['Q'], m['P4']
    b3 = T + F(87) / 4 * A**2 - F(9) / 4 * R + M
    b4 = (-F(393) / 4 * A**3 - F(11) / 2 * A * M - 9 * A * T + F(117) / 4 * A * R - F(3) / 2 * M * N - 6 * P4
          - F(165) / 8 * U + F(9) / 4 * V)
    H = Laurent({k - 1: v for k, v in enumerate(taylor_quad(bubble_times_eps(d), 8))})
    L2, L3, L4, L5 = (Lser(d, n) for n in (2, 3, 4, 5))
    S4 = Laurent({-2: F(9) / 2, -1: A, 0: A**2 / 8 + 3 * R + M / 9,
                  1: M * (A + N) / 18 + A * R + U / 8 - F(9) / 4 * V})
    S5 = Laurent({-3: 18, -2: 11 * A, -1: b3 / 9 + F(3) / 2 * A**2 + F(45) / 2 * R + F(4) / 3 * M,
                  0: F(7) / 8 * A**3 + M * (A + N) + F(145) / 8 * A * R + F(43) / 16 * U - F(181) / 8 * V})
    F2 = Laurent({0: F(1) / 6}) * L2
    F3 = Einv * L2 + Laurent({0: -F(1) / 4}) * H * L3
    F4 = Laurent({-2: F(9) / 2, -1: -A}) * L2 + Laurent({-1: -F(9) / 4}) * H * L3 + S4 * L4
    F5 = (Laurent({-3: 18, -2: -10 * A, -1: b3 / 9}) * L2 + Laurent({-2: -F(27) / 2, -1: F(9) / 4 * A}) * H * L3
          + Laurent({-1: 12}) * S4 * L4 + Laurent({0: -1}) * S5 * L5)
    gstar = Laurent({1: F(1) / 3, 2: 2 * A / 9, 3: 8 * A**2 / 27 - b3 / 81, 4: 40 * A**3 / 81 - (10 * A * b3 + b4) / 243})
    g2 = gstar * gstar
    g3 = g2 * gstar
    g4 = g3 * gstar
    g5 = g4 * gstar
    total = g2 * F2 + g3 * F3 + g4 * F4 + g5 * F5
    # reference: closed formula through a^(5) with these T, P4 (K, L, Z, P5 do not enter)
    mm = dict(m, P5=0, K=0, L=0, Z=0)
    h, f = hpoly(b, mm), outer(b)
    q = d / 4
    a2d = -mp.gamma(1 - q) * mp.gamma(2 * q)**3 / (54 * mp.gamma(1 + q) * mp.gamma(4 * q))
    ref = [a2d * sum(h[j] * f[n - j] for j in range(n + 1)) for n in range(4)]
    for k in range(-2, 2):
        rec(f'N5 d={mp.nstr(d, 3)} re-assembled a(eps): coefficient eps^{k} vanishes', total.c.get(k, 0), mp.mpf(0),
            mp.mpf('1e-25'))
    for k in range(2, 6):
        rec(f'N5 d={mp.nstr(d, 3)} re-assembled a^({k}) == closed formula', total.c.get(k, 0), ref[k - 2],
            mp.mpf('1e-25'))
    # F_n individually finite (renormalized amplitudes)
    for name, Fn in (('F3', F3), ('F4', F4), ('F5', F5)):
        worst = max([abs(v) for k, v in Fn.c.items() if k < 0] + [mp.mpf(0)])
        rec(f'N5 d={mp.nstr(d, 3)} {name} has no poles', worst, mp.mpf(0), mp.mpf('1e-25'))


# ---------------- N6: S_4 from chains and kites; symmetric kite from Pattern A; S_5 finite table
def Bd(d, a, b):   # gs:convolution (absolute exponents)
    return (mp.gamma(d / 2) * mp.gamma((d - a) / 2) * mp.gamma((d - b) / 2) * mp.gamma((a + b - d) / 2)
            / (mp.gamma(a / 2) * mp.gamma(b / 2) * mp.gamma((2 * d - a - b) / 2)))


def chain(d, v1, v2, v3):   # squared-distance exponents, normalized measure
    return (mp.gamma(d / 2)**2 * mp.gamma(d / 2 - v1) * mp.gamma(d / 2 - v2) * mp.gamma(d / 2 - v3)
            / (mp.gamma(v1) * mp.gamma(v2) * mp.gamma(v3)) * mp.gamma(v1 + v2 + v3 - d)
            / mp.gamma(3 * d / 2 - v1 - v2 - v3))


def laurent_of(fun, lowest, order=6):
    # fun has a pole of order <= -lowest at 0
    c = taylor_quad(lambda z: fun(z) * z**(-lowest), order)
    return {k + lowest: v for k, v in enumerate(c)}


for d in (mp.mpf(3), mp.mpf('2.6'), mp.mpf(1)):
    b = basis(d)
    A, R, U, M = b['A'], b['R'], b['U'], b['M']
    q = d / 4
    u = lambda z: q - z / 4

    def PA(z):   # symmetric kite (a,b,c,f,e) = (2u,2u,2u,2u,4u): t = z, p0 = p1 = 2z, u0 = v0 = 0
        t, p0 = z, 2 * z
        return 2 * (2 / p0) * Bd(d, (d + t) / 2, d - t) + (2 / t) * Bd(d, d - p0, d - p0) - (4 / t) * (2 / p0)
    kp = laurent_of(PA, -2)
    rec(f'N6 d={mp.nstr(d, 3)} symmetric kite eps^-2 (Pattern A)', kp[-2], mp.mpf(4), mp.mpf('1e-40'))
    rec(f'N6 d={mp.nstr(d, 3)} symmetric kite eps^-1 (Pattern A)', kp[-1], 2 * A, mp.mpf('1e-40'))
    rec(f'N6 d={mp.nstr(d, 3)} symmetric kite eps^0 (Pattern A)', kp[0], A**2 / 2 + F(7) / 2 * R, mp.mpf('1e-40'))
    ch1 = laurent_of(lambda z: chain(d, 3 * u(z), u(z), 3 * u(z)), 0)
    ch2 = laurent_of(lambda z: chain(d, 2 * u(z), 2 * u(z), 2 * u(z)), -2)
    ch3 = laurent_of(lambda z: chain(d, u(z), 3 * u(z), u(z)), 0)
    Kx = {-2: mp.mpf(8), -1: 2 * A, 0: 4 * R}              # package expansion (not independently evaluated)
    S4 = {k: F(1) / 36 * ch1.get(k, 0) + F(1) / 4 * Kx.get(k, 0) + F(1) / 8 * ch2.get(k, 0)
          + F(1) / 4 * kp.get(k, 0) + F(1) / 12 * ch3.get(k, 0) for k in (-2, -1, 0)}
    for k, ref in ((-2, F(9) / 2), (-1, A), (0, A**2 / 8 + 3 * R + M / 9)):
        rec(f'N6 d={mp.nstr(d, 3)} S_4 eps^{k} from the four-vertex table', S4[k], ref, mp.mpf('1e-40'))

As, Rs, Us, Vs, Ms, Ns = sp.symbols('A R U V M N')
MA = Ms * (As + Ns)
rows = [(sp.Rational(1, 36), 0), (sp.Rational(1, 12), -MA), (sp.Rational(1, 24), 3 * MA),
        (sp.Rational(1, 2), As**3 * sp.Rational(5, 18) + sp.Rational(65, 6) * As * Rs + sp.Rational(43, 36) * Us - sp.Rational(163, 18) * Vs),
        (sp.Rational(1, 4), -sp.Rational(7, 18) * As**3 + sp.Rational(77, 6) * As * Rs + sp.Rational(7, 36) * Us - sp.Rational(247, 18) * Vs),
        (sp.Rational(1, 4), -As**3 / 3 + 11 * As * Rs + sp.Rational(11, 6) * Us - sp.Rational(13, 3) * Vs),
        (sp.Rational(1, 6), 0), (sp.Rational(1, 6), 2 * MA), (sp.Rational(1, 16), -40 * Vs),
        (sp.Rational(1, 4), sp.Rational(2, 9) * As**3 + sp.Rational(26, 3) * As * Rs + sp.Rational(11, 9) * Us - sp.Rational(166, 9) * Vs),
        (sp.Rational(1, 8), sp.Rational(8, 9) * As**3 + sp.Rational(32, 3) * As * Rs + sp.Rational(23, 9) * Us - sp.Rational(160, 9) * Vs),
        (sp.Rational(1, 2), sp.Rational(3, 2) * As**3 + sp.Rational(13, 2) * As * Rs + sp.Rational(23, 12) * Us - sp.Rational(17, 2) * Vs),
        (sp.Rational(1, 24), 0), (sp.Rational(1, 8), 5 * MA)]
s5fin = sp.expand(sum(w * c for w, c in rows))
target = sp.expand(sp.Rational(7, 8) * As**3 + MA + sp.Rational(145, 8) * As * Rs + sp.Rational(43, 16) * Us
                   - sp.Rational(181, 8) * Vs)
ok = sp.expand(s5fin - target) == 0
out['N6 five-vertex finite table sums to S_5 finite part'] = {'pass': ok, 'difference': str(sp.expand(s5fin - target))}
print(('PASS ' if ok else 'FAIL ') + 'N6 five-vertex finite table sums to S_5 finite part', sp.expand(s5fin - target))

npass = sum(1 for v in out.values() if isinstance(v, dict) and v.get('pass') is True)
nfail = sum(1 for v in out.values() if isinstance(v, dict) and v.get('pass') is False)
print(f'{npass} PASS, {nfail} FAIL')
json.dump(out, open(sys.argv[1], 'w'), indent=1)
sys.exit(1 if nfail else 0)
