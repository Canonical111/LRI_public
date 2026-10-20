#!/usr/bin/env python3
"""ARCHIVE-FREE trace algebra for C8 = 8 T4 (note eq:C8trace, eq:C8F, eq:C8H, eq:C8assembly, appendix app:C8polynomial).

  * fixed point of F = H = 0 with the note's C8 jets (eq:C8F/eq:C8H, l.1106-1116) PLUS generic unknown
    higher monomials (leak test: none may enter T4);
  * T(delta) = 2 u F_u + (1+z) H_z through delta^4, also from the literal full Jacobian trace;
  * C8 = 8 T4 by direct eigenvalue expansion of Delta_- (no D5 dependence);
  * the coefficients of the ten new inputs against eq:C8assembly (l.1162-1166), and
    B_old = 8 T4 - (new part) against the appendix polynomial (l.2783-2804), typed in from the TeX;
  * pi_0 B_old = 1153/6 (appendix l.2783) is NOT checked here: it needs the archive's rational projections of
    the 25 old inputs (sealed comparison file).
Reads no archive file; the note's polynomial is a definition-level statement (no archive number).
Output: ../out/C8/invariants_C8.json
"""
import json, time
from pathlib import Path
import sympy as s

OUT = Path(__file__).resolve().parent.parent / 'out' / 'C8'
u, z, dl = s.symbols('u z delta')
old_names = 'a p A E V alpha beta gamma b G R Phi Psi J Omega c f q L M Q k N P K'.split()
new_names = 'W S U J9 L3 M21 M12 N2 Ndelta Kv'.split()
S = {n: s.Symbol(n) for n in old_names + new_names}
(a, p, A, E, V, alpha, beta, gamma, b, G, R, Phi, Psi, J, Omega, c, f, q, L, M, Q, k, N, P, K,
 W, S_, U, J9, L3, M21, M12, N2, Nd, Kv) = (S[n] for n in old_names + new_names)

# note eq:C8F, eq:C8H (l.1106-1116)
F = (z + u * (1 + a * z + p * dl + A * z**2 + E * dl * z + V * dl**2 + alpha * z**3 + beta * dl * z**2 + gamma * dl**2 * z + W * dl**3)
     + u**2 * (b + G * z + R * dl + Phi * z**2 + Psi * dl * z + S_ * dl**2)
     + u**3 * (J + Omega * z + U * dl) + J9 * u**4)
H = (-dl + 4 * u + u**2 * (c + f * z + q * dl + L * z**2 + M * dl * z + Q * dl**2 + L3 * z**3 + M21 * dl * z**2 + M12 * dl**2 * z)
     + u**3 * (k + N * z + P * dl + N2 * z**2 + Nd * dl * z) + u**4 * (K + Kv * z))

# generic higher monomials that must NOT enter T4 (power counting after differentiation)
X = s.symbols('X1:23')
F_ext = F + (X[0] * u**5 + X[1] * u * z**4 + X[2] * u * z**3 * dl + X[3] * u * dl**4 + X[4] * u**2 * z**3 + X[5] * u**2 * dl**3
             + X[6] * u**3 * z**2 + X[7] * u**3 * dl**2 + X[8] * u**4 * z + X[9] * u**4 * dl + X[10] * u**2 * z**2 * dl
             + X[11] * u * z**2 * dl**2)
H_ext = H + (X[12] * u**5 + X[13] * u**2 * z**4 + X[14] * u**3 * z**3 + X[15] * u**4 * z**2 + X[16] * u**5 * z + X[17] * u**4 * dl
             + X[18] * u**2 * dl**3 + X[19] * u**3 * dl**2 + X[20] * u**2 * z**3 * dl + X[21] * u**3 * z**2 * dl)


def tmul(x, y, n):
    out = {}
    for i, a_ in x.items():
        for j, b_ in y.items():
            if i + j <= n:
                out[i + j] = out.get(i + j, 0) + a_ * b_
    return {i: s.expand(v_) for i, v_ in out.items()}


def compose(ex, Us, Zs, n):
    Pl = s.Poly(s.expand(ex), u, z, dl)
    du = max((m[0] for m in Pl.monoms()), default=0)
    dz = max((m[1] for m in Pl.monoms()), default=0)
    Up, Zp = [{0: s.Integer(1)}], [{0: s.Integer(1)}]
    for _ in range(du):
        Up.append(tmul(Up[-1], Us, n))
    for _ in range(dz):
        Zp.append(tmul(Zp[-1], Zs, n))
    out = {}
    for (i, j, l), co in Pl.terms():
        if i + j + l > n:
            continue
        for m, v_ in tmul(Up[i], Zp[j], n - l).items():
            out[m + l] = out.get(m + l, 0) + co * v_
    return {i: s.expand(v_) for i, v_ in out.items()}


def fixed_point(Fx, Hx, nu, nz):
    Us, Zs = {}, {}
    for n in range(1, max(nu, nz) + 1):
        un, zn = s.Symbol('un'), s.Symbol('zn')
        if n <= nu:
            Ut = dict(Us); Ut[n] = un
            Us[n] = s.expand(s.solve(compose(Hx, Ut, Zs, n).get(n, 0), un)[0])
        if n <= nz:
            Zt = dict(Zs); Zt[n] = zn
            Zs[n] = s.expand(s.solve(compose(Fx, Us, Zt, n).get(n, 0), zn)[0])
    return Us, Zs


t0 = time.time()
Us, Zs = fixed_point(F_ext, H_ext, 4, 4)
Fu, Hz = s.diff(F_ext, u), s.diff(H_ext, z)
Tser = compose(2 * u * Fu + (1 + z) * Hz, Us, Zs, 4)
T4_ext = Tser[4]
ext = set(X)
assert Tser[1] == s.Rational(1, 2), Tser[1]
leak = T4_ext.free_symbols & ext
assert not leak, f'higher terms leak into T4: {leak}'
print('leak test passed', round(time.time() - t0, 1), 's', flush=True)

# literal full-Jacobian trace (no extra terms): tr d(beta_u, beta_z)/d(u,z) = d(2uF)/du + d((1+z)H)/dz
Us0, Zs0 = fixed_point(F, H, 4, 4)
TJ = compose(s.diff(2 * u * F, u) + s.diff((1 + z) * H, z), Us0, Zs0, 4)
T4 = s.expand(T4_ext)
assert s.expand(TJ[4] - T4) == 0
# T2, T3 must reproduce the phase-1 trace (out/invariants.json)
inv1 = json.load(open(OUT.parent / 'invariants.json'))
assert s.expand(Tser[2] - s.sympify(inv1['T2'], locals=S)) == 0 and s.expand(Tser[3] - s.sympify(inv1['T3'], locals=S)) == 0
print('full-Jacobian trace and T2, T3 regression OK', round(time.time() - t0, 1), 's', flush=True)

# conversion: C8 = 8 T4 by direct eigenvalue expansion (T to delta^4, D to delta^5 with a symbolic D5)
t = s.Symbol('t', positive=True)
T2s, T3s, T4s, D2s, D3s, D4s, D5s = s.symbols('T2s T3s T4s D2s D3s D4s D5s')
Tr = dl / 2 + T2s * dl**2 + T3s * dl**3 + T4s * dl**4
De = -2 * dl + D2s * dl**2 + D3s * dl**3 + D4s * dl**4 + D5s * dl**5
disc = s.expand((Tr**2 / 4 - De).subs(dl, 2 * t**2))
root = 2 * t * s.sqrt(s.expand(disc / (4 * t**2)))
Dm = s.expand(s.series(1 + Tr.subs(dl, 2 * t**2) / 2 - root, t, 0, 10).removeO())
C8_conv = s.expand(Dm.coeff(t, 8))
assert s.expand(C8_conv - 8 * T4s) == 0, C8_conv
C9_conv = s.expand(Dm.coeff(t, 9))
assert D5s in C9_conv.free_symbols        # D5 first enters C9
print('C8 = 8 T4 exactly (no D5); D5 first enters C9', flush=True)

C8poly = s.expand(8 * T4)
note_new = {W: 4, S_: 2, U: s.Rational(3, 4), J9: s.Rational(1, 4), L3: s.Rational(3, 32), M21: -s.Rational(1, 4),
            M12: s.Rational(1, 2), N2: -s.Rational(1, 16), Nd: s.Rational(1, 8), Kv: s.Rational(1, 32)}
new_coeffs = {str(x): str(C8poly.coeff(x)) for x in note_new}
for x, cf in note_new.items():
    assert C8poly.coeff(x) == cf, (x, C8poly.coeff(x), cf)
B_old = s.expand(C8poly - sum(cf * x for x, cf in note_new.items()))
assert not B_old.free_symbols & set(note_new), 'new inputs appear nonlinearly'

# appendix polynomial (note l.2785-2804), typed in from the TeX source
R_ = s.Rational
note_B_old = (- gamma - R_(5, 1024) * c**3 - R_(3, 16) * Omega
              - Psi / 2 - Q / 4 - M / 16
              - P / 16 - alpha / 16 - a**3 / 16
              - K / 64 - N / 64 + beta / 4
              + Phi / 8 + f**2 / 64 + R_(3, 64) * L
              + A * p / 2 + E * a / 2 - E * p
              - V * a - R_(9, 64) * J * c - R_(5, 256) * a * c**2
              - R_(3, 16) * A * a - R_(3, 64) * A * c - R_(3, 64) * a**2 * c
              - R_(3, 128) * N * c - G * p / 2 - E * b / 4
              - L * p / 4 - R * a / 4 - R * c / 4
              - V * c / 4 - b * q / 4 - p * q / 4
              - G * b / 8 - J * a / 16 - L * b / 16
              - M * c / 16 - b * k / 16 - f * q / 16
              - k * p / 16 - a * f / 64 - f * k / 64
              + a**2 * p / 4 + A * b / 8 + E * c / 8
              + a * q / 8 + L * a / 16 + a**2 * b / 16
              + c * q / 16 + a * k / 32 + c**2 * p / 32
              + c * f / 256 + R_(3, 16) * G * a + R_(3, 32) * G * c
              + R_(3, 64) * L * c + R_(3, 64) * b * f + R_(5, 128) * b * c**2
              + R_(5, 256) * c * k + R_(5, 512) * c**2 * f + a * c * p / 8
              + R_(3, 64) * a * b * c)
diff_B = s.expand(B_old - note_B_old)
assert diff_B == 0, diff_B
print('eq:C8assembly coefficients and the appendix B_old polynomial reproduced exactly', round(time.time() - t0, 1), 's')

# term count and the linear part of B_old (sanity numbers for readers)
n_terms = len(s.Add.make_args(B_old))
res = {
    'note': 'ARCHIVE-FREE (scripts/derive_invariants_C8.py). Jets typed in from note eq:C8F/eq:C8H; B_old compared with the '
            'appendix polynomial typed in from the TeX.',
    'jets': {'F': s.sstr(F), 'H': s.sstr(H)},
    'fixed_point': {f'u{i}': s.sstr(v_) for i, v_ in Us0.items() if i <= 2} | {f'z{i}': s.sstr(v_) for i, v_ in Zs0.items() if i <= 2},
    'T4': s.sstr(T4),
    'C8 = 8 T4': s.sstr(C8poly),
    'C8_new_part': ' + '.join(f'({s.sstr(cf)})*{x}' for x, cf in note_new.items()),
    'C8_new_coefficients': new_coeffs,
    'B_old_C8': s.sstr(B_old),
    'B_old_C8_n_terms': n_terms,
    'checks': {
        'higher_terms_do_not_enter_T4 (22 generic monomials)': True,
        'full_jacobian_trace_equals_2uFu_plus_(1+z)Hz': True,
        'T2_T3_equal_phase1': True,
        'C8 = 8 T4 by eigenvalue expansion (no D5)': True,
        'note_eq:C8assembly_new_coefficients': True,
        'note_appendix_B_old_polynomial (61 terms)': True,
        'new_inputs_enter_linearly': True,
    },
    'not_checked_here': 'pi_0 B_old = 1153/6 (appendix l.2783) and the numerical B_old = -861.66... (l.1167): both need archive '
                        'numbers (sealed in comparison_C8/).',
}
json.dump(res, open(OUT / 'invariants_C8.json', 'w'), indent=1)
print('B_old terms', n_terms, 'done', round(time.time() - t0, 1), 's')
