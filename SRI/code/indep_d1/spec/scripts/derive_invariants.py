#!/usr/bin/env python3
"""ARCHIVE-FREE fixed-point / stability-invariant algebra for C5, C6, C7 (D3, T3, D4).

Written from the note's definitions (eq:TD, eq:invariantseries, eq:conversion, the beta
jets of Secs. 7, 8, 13).  Reads NO archive file and imports no archive code.
  * fixed point, T and D series with generic higher terms (leak test), full-Jacobian form,
    conversion to C3..C7 by direct eigenvalue expansion;
  * equality with the note's printed formulas (D2, T2, D3 assembly, B_old of C6, the
    new-input coefficients of C6 and D4) -- the note formulas are typed in from the TeX;
  * exact check that the note's closed forms of the old inputs (eq:oldbetas, eq:Eexact) and
    of the combination calR = 2G+k+2q-2b-f (note l.632) reproduce the boxed D2, T2, D3;
  * the claimed closed forms (C3..C7, D2..D4, T2, T3) evaluated to 60 digits.
The comparison with the archived algebra records and archived input values lives in
../comparison/scripts/compare_with_archive.py (sealed; production never reads it).
Output: ../out/invariants.json
"""
import json
from pathlib import Path
import sympy as s
import mpmath as mp

OUT = Path(__file__).resolve().parent.parent / 'out'
mp.mp.dps = 80

u, z, dl = s.symbols('u z delta')
names = 'a p A E V alpha beta gamma b G R Phi Psi J Omega c f q L M Q k N P K'.split()
S = {n: s.Symbol(n) for n in names}
a, p, A, E, V, alpha, beta, gamma, b, G, R, Phi, Psi, J, Omega, c, f, q, L, M, Q, k, N, P, K = (S[n] for n in names)

F = (z + u * (1 + a * z + p * dl + A * z**2 + E * dl * z + V * dl**2 + alpha * z**3 + beta * z**2 * dl + gamma * z * dl**2)
     + u**2 * (b + G * z + R * dl + Phi * z**2 + Psi * z * dl) + u**3 * (J + Omega * z))
H = (-dl + 4 * u + u**2 * (c + f * z + q * dl + L * z**2 + M * z * dl + Q * dl**2)
     + u**3 * (k + N * z + P * dl) + K * u**4)

# generic unknown higher terms that must NOT matter at the orders used (power counting check)
X1, X2, X3, X4, X5 = s.symbols('X1:6')
F_ext = F + X1 * u**4 + X2 * u * z**4 + X3 * u**2 * dl**2 + X4 * u**3 * dl
H_ext = H + X5 * u**2 * z**3 + s.Symbol('X6') * u**3 * z**2 + s.Symbol('X7') * u**5 + s.Symbol('X8') * u**2 * dl**3

def tmul(x, y, n):
    out = {}
    for i, a_ in x.items():
        for j, b_ in y.items():
            if i + j <= n:
                out[i + j] = out.get(i + j, 0) + a_ * b_
    return {i: s.expand(v_) for i, v_ in out.items()}

def compose(ex, U, Z, n):
    """ex polynomial in u,z,delta ; U,Z dict series in delta (no constant term) -> dict series to delta^n"""
    P = s.Poly(s.expand(ex), u, z, dl)
    du = max((m[0] for m in P.monoms()), default=0); dz = max((m[1] for m in P.monoms()), default=0)
    Up = [{0: s.Integer(1)}]; Zp = [{0: s.Integer(1)}]
    for _ in range(du):
        Up.append(tmul(Up[-1], U, n))
    for _ in range(dz):
        Zp.append(tmul(Zp[-1], Z, n))
    out = {}
    for (i, j, l), co in P.terms():
        if i + j + l > n:
            continue
        for m, v_ in tmul(Up[i], Zp[j], n - l).items():
            out[m + l] = out.get(m + l, 0) + co * v_
    return {i: s.expand(v_) for i, v_ in out.items()}

def fixed_point(Fx, Hx, nu, nz):
    """solve H=0 for u_n and F=0 for z_n order by order"""
    U = {}; Z = {}
    for n in range(1, max(nu, nz) + 1):
        un, zn = s.Symbol('un'), s.Symbol('zn')
        if n <= nu:
            Ut = dict(U); Ut[n] = un
            hn = compose(Hx, Ut, Z, n).get(n, 0)
            U[n] = s.expand(s.solve(hn, un)[0])
        if n <= nz:
            Zt = dict(Z); Zt[n] = zn
            fn = compose(Fx, U, Zt, n).get(n, 0)
            Z[n] = s.expand(s.solve(fn, zn)[0])
    return U, Z

def invariants(Fx, Hx, nu, nz, order, full=False):
    U, Z = fixed_point(Fx, Hx, nu, nz)
    Fu, Fz, Hu, Hz = (s.diff(Fx, u), s.diff(Fx, z), s.diff(Hx, u), s.diff(Hx, z))
    T = compose(2 * u * Fu + (1 + z) * Hz, U, Z, order)
    D = compose(2 * u * (1 + z) * (Fu * Hz - Fz * Hu), U, Z, order)
    TJ = DJ = None
    if full:
        TJ = compose(s.diff(2 * u * Fx, u) + s.diff((1 + z) * Hx, z), U, Z, order)
        DJ = compose(s.expand(s.diff(2 * u * Fx, u) * s.diff((1 + z) * Hx, z) - s.diff(2 * u * Fx, z) * s.diff((1 + z) * Hx, u)), U, Z, order)
    return U, Z, T, D, TJ, DJ

import time; _t = time.time()
# trace to delta^3 (u to delta^3, z to delta^2); determinant to delta^4 (u to delta^4, z to delta^3)
_, _, Tser, _, _, _ = invariants(F_ext, H_ext, 3, 2, 3)
_, _, _, Dser, _, _ = invariants(F_ext, H_ext, 4, 3, 4)
T2, T3 = Tser.get(2, 0), Tser.get(3, 0)
D2, D3, D4 = Dser.get(2, 0), Dser.get(3, 0), Dser.get(4, 0)
ext = {s.Symbol(f'X{i}') for i in range(1, 9)}
assert Tser.get(1) == s.Rational(1, 2) and Dser.get(1) == -2
assert not (T3.free_symbols | D4.free_symbols) & ext, 'higher terms leak'
print('ext checks', time.time() - _t, flush=True)
UT, ZT, T2ser, _, TJ2, _ = invariants(F, H, 3, 3, 3, full=True)
assert s.expand(TJ2[3] - T2ser[3]) == 0 and s.expand(T2ser[3] - T3) == 0
UD, ZD, _, D2ser, _, DJ2 = invariants(F, H, 4, 3, 4, full=True)
assert s.expand(DJ2[4] - D2ser[4]) == 0 and s.expand(D2ser[4] - D4) == 0
solT2 = {f'u{i}': U_ for i, U_ in UT.items()}; solT2.update({f'z{i}': Z_ for i, Z_ in ZT.items()})
solD2 = {f'u{i}': U_ for i, U_ in UD.items()}; solD2.update({f'z{i}': Z_ for i, Z_ in ZD.items()})
print('full jacobian checks', time.time() - _t, flush=True)

# --- conversion to thermal coefficients by direct eigenvalue expansion
t = s.Symbol('t', positive=True)
T2s, T3s, D2s, D3s, D4s = s.symbols('T2s T3s D2s D3s D4s')
Tr = dl / 2 + T2s * dl**2 + T3s * dl**3
De = -2 * dl + D2s * dl**2 + D3s * dl**3 + D4s * dl**4
disc = s.expand((Tr**2 / 4 - De).subs(dl, 2 * t**2))
root = 2 * t * s.sqrt(s.expand(disc / (4 * t**2)))
Dm = s.expand(s.series(1 + Tr.subs(dl, 2 * t**2) / 2 - root, t, 0, 8).removeO())
Cn = {n: s.expand(Dm.coeff(t, n)) for n in range(1, 8)}
assert Cn[1] == -2 and Cn[2] == s.Rational(1, 2)
C3f = D2s - s.Rational(1, 16)
assert s.expand(Cn[3] - C3f) == 0 and s.expand(Cn[4] - 2 * T2s) == 0
C5f = 2 * D3s - T2s / 2 + (D2s - s.Rational(1, 16))**2 / 4
assert s.expand(Cn[5] - C5f) == 0 and s.expand(Cn[6] - 4 * T3s) == 0
assert s.expand(Cn[7] - (4 * D4s - T3s - T2s**2 + C3f * C5f / 2)) == 0

C6poly = s.expand(4 * T3)
newC6 = {V: 2, R: 1, J: s.Rational(3, 8), L: -s.Rational(1, 8), M: s.Rational(1, 4), N: s.Rational(1, 16)}
B_old = s.expand(C6poly - sum(cf * x for x, cf in newC6.items()))
note_B_old = (A / 8 - E / 2 - G / 4 + (a**2 - a * b) / 8 + a * c / 16 - a * p / 2 - b * c / 8 + c**2 / 64
              - c * f / 32 - c * p / 8 - f / 32 - k / 32 - q / 8)
assert s.expand(B_old - note_B_old) == 0
for x, cf in newC6.items():
    assert s.expand(C6poly).coeff(x) == cf
note_D3 = (16 * A - 32 * E - 8 * G + 8 * b + c**2 + 4 * f - 4 * k + 32 * p - 8 * q) / 64
assert s.expand(D3 - note_D3) == 0
assert s.expand(D2 - (s.Rational(1, 2) - a / 2 - c / 8)) == 0
assert s.expand(T2 - (-a / 8 + b / 4 - c / 32 + f / 16 + p / 2)) == 0
newD4 = {alpha: -s.Rational(3, 32), beta: s.Rational(1, 4), gamma: -s.Rational(1, 2), Phi: s.Rational(1, 16),
         Psi: -s.Rational(1, 8), Omega: -s.Rational(1, 32), Q: -s.Rational(1, 8), P: -s.Rational(1, 16), K: -s.Rational(3, 128)}
for x, cf in newD4.items():
    assert s.expand(D4).coeff(x) == cf, (x, s.expand(D4).coeff(x))
B_old_D4 = s.expand(D4 - sum(cf * x for x, cf in newD4.items()))
assert not B_old_D4.free_symbols & set(newD4)


# --- note closed forms of the old inputs -> boxed D2, T2, D3 (exact, archive-free)
zz2, zz3, zz4, LL2, LL3, Li2h, Li4h, calR = s.symbols('z2 z3 z4 L2 L3 Li2h Li4h calR')
closed_old_sym = {
    a: -4 * zz2, c: s.Integer(-16), p: 8 - 2 * zz2 - 7 * zz3 - 8 * LL2,
    b: -18 - 6 * zz2 + s.Rational(28, 3) * zz3 + 32 * LL2 - 12 * LL3 - 4 * LL2**2 - 8 * Li2h,
    f: 32 - s.Rational(136, 3) * zz3 - 64 * LL2 + 48 * LL3 + 16 * LL2**2 + 32 * Li2h,
    A: -8 - 4 * zz2 - 2 * zz3 + 16 * LL2,
    E: (-16 + 14 * zz2 - 22 * zz3 + 12 * zz4 + 8 * LL2 - 8 * LL2**2 - 16 * Li4h - 14 * zz3 * LL2
        + 4 * zz2 * LL2**2 - s.Rational(2, 3) * LL2**4),
}
calR_closed = (140 + 64 * zz2 - 64 * zz3 - 272 * zz4 - 64 * LL2 + 64 * LL2**2 + 112 * zz3 * LL2
               - 32 * zz2 * LL2**2 + s.Rational(16, 3) * LL2**4 + 128 * Li4h)
# D3 = A/4 - E/2 + c^2/64 + p/2 - calR/16 with calR = 2G + k + 2q - 2b - f (note l.629)
assert s.expand(D3 - (A / 4 - E / 2 + c**2 / 64 + p / 2 - (2 * G + k + 2 * q - 2 * b - f) / 16)) == 0
D2_cf = s.expand(D2.subs(closed_old_sym))
T2_cf = s.expand(T2.subs(closed_old_sym))
D3_cf = s.expand((A / 4 - E / 2 + c**2 / 64 + p / 2 - calR / 16).subs(closed_old_sym).subs(calR, calR_closed))
assert D2_cf == s.Rational(5, 2) + 2 * zz2, D2_cf
assert T2_cf == 2 - 2 * zz2 - 4 * zz3, T2_cf
assert D3_cf == s.Rational(21, 4) - 13 * zz2 + 11 * zz3 + 11 * zz4, D3_cf

# --- claimed closed forms, numerically (no archive input)
z2, z3, z4, z5, z6 = (mp.zeta(i) for i in range(2, 7))
claims = {
    'D2': mp.mpf(5) / 2 + 2 * z2,
    'T2': 2 - 2 * z2 - 4 * z3,
    'D3': mp.mpf(21) / 4 - 13 * z2 + 11 * z3 + 11 * z4,
    'C5': mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z2 + 24 * z3 + mp.mpf(49) / 2 * z4,
    'C6': 26 - 38 * z2 + 104 * z3 - 80 * z4 - 272 * z5 + 112 * z2 * z3,
    'D4': 13 - mp.mpf(179) / 8 * z2 + mp.mpf(47) / 2 * z3 - mp.mpf(493) / 8 * z4 + 289 * z5 - 130 * z2 * z3 + mp.mpf(499) / 4 * z6 - 76 * z3**2,
}
claims['T3'] = claims['C6'] / 4
claims['C3'] = mp.mpf(39) / 16 + 2 * z2
claims['C4'] = 2 * claims['T2']
claims['C7'] = 4 * claims['D4'] - claims['T3'] - claims['T2']**2 + claims['C3'] * claims['C5'] / 2
assert abs(claims['C3'] - (claims['D2'] - mp.mpf(1) / 16)) < mp.mpf(10)**-70
assert abs(claims['C5'] - (2 * claims['D3'] - claims['T2'] / 2 + claims['C3']**2 / 4)) < mp.mpf(10)**-70
claimed_closed = {'D2': '5/2 + 2 z2', 'T2': '2 - 2 z2 - 4 z3', 'C3': '39/16 + 2 z2', 'C4': '4 - 4 z2 - 8 z3',
                  'D3': '21/4 - 13 z2 + 11 z3 + 11 z4', 'C5': '11249/1024 - 361/16 z2 + 24 z3 + 49/2 z4',
                  'C6': '26 - 38 z2 + 104 z3 - 80 z4 - 272 z5 + 112 z2 z3', 'T3': 'C6/4',
                  'D4': '13 - 179/8 z2 + 47/2 z3 - 493/8 z4 + 289 z5 - 130 z2 z3 + 499/4 z6 - 76 z3^2',
                  'C7': '4 D4 - T3 - T2^2 + C3 C5/2 = 1798583/32768 - 90637/1024 z2 + 453/4 z3 - 16835/64 z4 + 1224 z5 - 540 z2 z3 + 4335/8 z6 - 320 z3^2'}

out = {
    'note': 'ARCHIVE-FREE. Generated by scripts/derive_invariants.py from the note definitions only.',
    'beta_jets': {'F': s.sstr(F), 'H': s.sstr(H)},
    'fixed_point_trace_order': {k_: s.sstr(v_) for k_, v_ in solT2.items()},
    'fixed_point_det_order': {k_: s.sstr(v_) for k_, v_ in solD2.items()},
    'D2': s.sstr(D2), 'T2': s.sstr(T2), 'D3': s.sstr(D3), 'T3': s.sstr(T3), 'D4': s.sstr(s.expand(D4)),
    'C6_polynomial': s.sstr(C6poly), 'B_old_C6': s.sstr(B_old), 'B_old_D4': s.sstr(B_old_D4),
    'C6_new_coefficients': {str(x): str(cf) for x, cf in newC6.items()},
    'D4_new_coefficients': {str(x): str(cf) for x, cf in newD4.items()},
    'conversion': {'C3': 'D2-1/16', 'C4': '2*T2', 'C5': '2*D3-T2/2+(D2-1/16)^2/4', 'C6': '4*T3',
                   'C7': '4*D4-T3-T2^2+C3*C5/2', 'checked_by_direct_eigenvalue_expansion': True},
    'checks': {'note_B_old_C6': True, 'note_D3': True, 'note_D2_T2': True, 'note_D4_new_coefficients': True,
               'higher_unknown_terms_do_not_enter_T3_D4': True, 'full_jacobian_equals_fixed_point_form': True,
               'note_old_input_closed_forms_give_boxed_D2_T2': True,
               'note_old_input_closed_forms_and_calR_give_boxed_D3': True},
    'claims_closed_form': claimed_closed,
    'claims_value_60': {k_: mp.nstr(v_, 60) for k_, v_ in claims.items()},
}
json.dump(out, open(OUT / 'invariants.json', 'w'), indent=1)
print('checks', out['checks'])
for k_ in ('C6', 'D4', 'C7'):
    print(k_, out['claims_value_60'][k_])
