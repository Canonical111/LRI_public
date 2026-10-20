#!/usr/bin/env python3
"""ARCHIVE-FREE validation targets for the independent C6/C7 re-derivation.

Every target here is either stated in the note, derived exactly here from the definitions,
implied by note closed forms through this spec's own definitions, or computed
independently inside this project.  No archive file is read and no archive number is used.
Each target carries a 'provenance' tag:

  note                      stated in note/LRI_perturbation_compendium.tex (line given)
  note-closed-forms         a relation evaluated with the NOTE's closed forms of a, A, p, E
  derived-here-exact        exact derivation from the definitions in this spec (script named)
  note-implied              fixed by a note closed form through this spec's definitions
  independent-numeric       project-internal numerical computation (script named), not exact

Archive-derived predictions (e.g. [l^3] C7, [l^2],[l^3] d_delta C5, the second-tail K4 logs,
archived finite-cutoff values) are NOT here: they are sealed in
../comparison/archive_comparison.json and are used only in the final comparison step.

Output: ../out/validation_targets.json
"""
import json, re
from pathlib import Path
import sympy as s
import mpmath as mp

SPEC = Path(__file__).resolve().parent.parent
OUT = SPEC / 'out'
mp.mp.dps = 60
NOTE = 'note/LRI_perturbation_compendium.tex'

# ----------------------------------------------------------------------------- constants
z2, z3, z4, L2, L3, Li2h, Li4h = s.symbols('z2 z3 z4 L2 L3 Li2h Li4h')
NUM = {z2: mp.zeta(2), z3: mp.zeta(3), z4: mp.zeta(4), L2: mp.log(2), L3: mp.log(3),
       Li2h: mp.polylog(2, -mp.mpf(1) / 2), Li4h: mp.polylog(4, mp.mpf(1) / 2)}
R = s.Rational
def num(ex):
    ex = s.sympify(ex)
    return mp.mpf(s.N(ex.subs({k: s.Float(mp.nstr(v, 70), 70) for k, v in NUM.items()}), 65))
SYMBOLS_LEGEND = {'z2..z6': 'zeta(2)..zeta(6)', 'L2': 'log 2', 'L3': 'log 3', 'Li2h': 'Li2(-1/2)', 'Li4h': 'Li4(1/2)',
                  'P4,R4,S5': 'note eq:periods-low (l.527-533)'}

# note closed forms (eq:oldbetas l.515-522, eq:Eexact l.580-584, eq:periods-low l.527-533, calR l.629-634)
OLD = {
    'a': (-4 * z2, 'eq:oldbetas (l.516)'),
    'c': (s.Integer(-16), 'eq:oldbetas (l.516)'),
    'p': (8 - 2 * z2 - 7 * z3 - 8 * L2, 'eq:oldbetas (l.517); also eq:panswer (l.2267)'),
    'b': (-18 - 6 * z2 + R(28, 3) * z3 + 32 * L2 - 12 * L3 - 4 * L2**2 - 8 * Li2h, 'eq:oldbetas (l.518-519)'),
    'f': (32 - R(136, 3) * z3 - 64 * L2 + 48 * L3 + 16 * L2**2 + 32 * Li2h, 'eq:oldbetas (l.520-521)'),
    'A': (-8 - 4 * z2 - 2 * z3 + 16 * L2, 'Sec. sec:D3 (l.580)'),
    'E': (-16 + 14 * z2 - 22 * z3 + 12 * z4 + 8 * L2 - 8 * L2**2 - 16 * Li4h - 14 * z3 * L2 + 4 * z2 * L2**2
          - R(2, 3) * L2**4, 'eq:Eexact (l.581-584)'),
}
P4 = 4 * z2 + R(8, 3) * z3 - 2 + 3 * L3 + L2**2 + 2 * Li2h
R4 = 24 - 20 * z2 - 30 * z3 - 16 * L2
S5 = 44 * z2 + R(152, 3) * z3 - 3 + 12 * L3 + 4 * L2**2 + 8 * Li2h
assert s.expand(S5 - 4 * P4 - (5 + 28 * z2 + 40 * z3)) == 0          # note l.537
calR = (140 + 64 * z2 - 64 * z3 - 272 * z4 - 64 * L2 + 64 * L2**2 + 112 * z3 * L2 - 32 * z2 * L2**2
        + R(16, 3) * L2**4 + 128 * Li4h)
a_, p_, A_, E_ = (OLD[k][0] for k in ('a', 'p', 'A', 'E'))

targets = []
def add(tid, quantity, series, eps_power, log_power, exact, provenance, source, kind='normalized', note=None):
    ex = s.sympify(exact) if not isinstance(exact, s.Basic) else exact
    rec = {'id': tid, 'quantity': quantity, 'series': series, 'eps_power': eps_power, 'log_power': log_power,
           'kind': kind, 'exact': s.sstr(s.expand(ex)), 'value': mp.nstr(num(ex), 50),
           'provenance': provenance, 'source': source}
    if note:
        rec['remark'] = note
    targets.append(rec)

# ---- 1. note: elementary two-kink responses (l.388)
add('Z2.m1.l0', 'Z2 raw', 'Z2_base', -1, 0, 1, 'note', f'{NOTE} l.388 Z2 = 1/eps + l - 1', 'raw')
add('Z2.0.l1', 'Z2 raw', 'Z2_base', 0, 1, 1, 'note', f'{NOTE} l.388', 'raw')
add('Z2.0.l0', 'Z2 raw', 'Z2_base', 0, 0, -1, 'note', f'{NOTE} l.388', 'raw')
add('Q2.0.l1', 'Q2 raw', 'Q2_base', 0, 1, -1, 'note', f'{NOTE} l.388 Q2 = -l - 1 + eps', 'raw')
add('Q2.0.l0', 'Q2 raw', 'Q2_base', 0, 0, -1, 'note', f'{NOTE} l.388', 'raw')
add('Q2.1.l0', 'Q2 raw', 'Q2_base', 1, 0, 1, 'note', f'{NOTE} l.388', 'raw')

# ---- 2. note: low normalized responses (l.548-557, appendix l.2229-2268)
for k, e in [(2, 2), (1, 5), (0, 3 - 2 * z2)]:
    add(f'C3.l{k}', 'C3 normalized', 'C3[v0d0]', 0, k, e, 'note', f'{NOTE} eq lo:eq:C3 (l.550)')
for k, e in [(3, R(-4, 3)), (2, -6), (1, -8 + 4 * z2), (0, P4 + 4 * z2 - 10)]:
    add(f'K4.l{k}', 'K4 normalized', 'K4[v0d0]', 0, k, e, 'note', f'{NOTE} eq lo:eq:K4 (l.551-552), P4 eq:periods-low')
for k, e in [(4, R(10, 3)), (3, R(62, 3)), (2, R(95, 2) - 24 * z2), (1, 96 - 40 * z2 - S5)]:
    add(f'C5.l{k}', 'C5 normalized', 'C5[v0d0]', 0, k, e, 'note', f'{NOTE} eq lo:eq:C5 (l.553-556), S5 eq:periods-low')
for k, e in [(3, R(-8, 3)), (2, -3), (1, 4 - 4 * z2), (0, 18 - 14 * z2 - 15 * z3 - 8 * L2)]:
    add(f'C3v.l{k}', 'd_v C3 normalized', 'C3[v1d0]', 0, k, e, 'note', f'{NOTE} eq lo:eq:C3v (l.2231-2234)')
for k, e in [(4, -1), (3, -1), (2, -2 * z2), (1, p_ - 4)]:
    add(f'C3d.l{k}', 'd_delta C3 normalized', 'C3[v0d1]', 0, k, e, 'note',
        f'{NOTE} eq lo:eq:C3delta (l.2263-2264); [l^1] = p - 4 with p from eq:panswer (l.2267)')

# ---- 3. endpoint finite parts
add('EQ4.0.l0', 'E Q4 raw (reflected first source derivative)', 'EQ4_base', 0, 0, 6 - 12 * z2 - 54 * z3 - 25 * z4,
    'note', f'{NOTE} eq:ep-exact (l.603); appendix l.2673 (boxed)', 'raw')
add('EA3v.0.l0', 'd_v E A3 raw (reflected first source derivative)', 'EA3_v', 0, 0,
    -108 + 60 * z2 + 22 * z3 - 34 * z4 + 16 * L2, 'note', f'{NOTE} eq:ep-exact (l.602)', 'raw')
add('EQ2.0.l0', 'E Q2 raw', 'EQ2_base', 0, 0, -2 * z2, 'derived-here-exact',
    'EQ2(eps) = int_eps^1 r^-1 [2(1-r)log(1-r) + 2 r log r] dr (inner X1 integral done exactly); '
    '[eps^0] = 2 int_0^1 (1-r)log(1-r)/r dr + 2 int_0^1 log r dr = 2(1 - z2) - 2. Numerical check in this script.', 'raw')
add('EZ2.0.l0', 'E Z2 raw', 'EZ2_base', 0, 0, 2 * z2 - 2, 'derived-here-exact',
    'EZ2(eps) = int_eps^1 r^-2 [2(1-r)log(1-r) + 2 r log r] dr; [eps^0] = -l^2 + 2 l + (2 z2 - 2): '
    'FP int_0^1 [2 log(1-r)/r^2 + 2/r] dr = [-2(1-r)log(1-r)/r]_0^1 = -2 and -2 int_0^1 log(1-r)/r dr = 2 z2. '
    'Numerical check in this script.', 'raw')
add('EZ2.0.l1', 'E Z2 raw', 'EZ2_base', 0, 1, 2, 'derived-here-exact', 'same derivation as EZ2.0.l0', 'raw')
add('EZ2.0.l2', 'E Z2 raw', 'EZ2_base', 0, 2, -1, 'derived-here-exact', 'same derivation as EZ2.0.l0', 'raw')

# EA3_base [eps^0 l^0] is fixed by the note's closed form of b through this spec's definition of b
defs = json.load(open(OUT / 'input_definitions.json'))
norm = json.load(open(OUT / 'normalized_atoms.json'))
two = json.load(open(OUT / 'two_kink_exact.json'))['atoms']
def tk(atom, p, k):
    return R(two[atom].get(str(p), {}).get(str(k), '0'))
assert norm['EC3_0[v0d0]']['leibniz_expansion'] == '(-1)*EZ2_base + (2)*Z2_base + (1)*EA3_base'
assert norm['EK2_0[v0d0]']['leibniz_expansion'] == '(1)*EQ2_base'
assert norm['K2_0[v1d0]']['leibniz_expansion'] == '(1)*Q2_v' and norm['K2_0[v0d0]']['leibniz_expansion'] == '(1)*Q2_base'
EA3_0 = s.Symbol('EA3_0')
note_atoms = {
    'C3_0[v0d0]': 3 - 2 * z2, 'C3_1[v0d0]': s.Integer(5), 'C3_0[v1d0]': 18 - 14 * z2 - 15 * z3 - 8 * L2,
    'C5_1[v0d0]': 96 - 40 * z2 - S5, 'K4_1[v0d0]': -8 + 4 * z2,
    'K2_0[v0d0]': tk('Q2_base', 0, 0), 'K2_0[v1d0]': tk('Q2_v', 0, 0), 'EK2_0[v0d0]': -2 * z2,
    'EC3_0[v0d0]': -(2 * z2 - 2) + 2 * tk('Z2_base', 0, 0) + EA3_0,
}
def subst(expr_str, atoms):
    loc = {}
    for i, at in enumerate(sorted(atoms, key=len, reverse=True)):
        expr_str = expr_str.replace(at, f'XX{i}')
        loc[f'XX{i}'] = atoms[at]
    return s.expand(s.sympify(expr_str, locals=loc))
c_from_def = subst(defs['c']['expansion_in_normalized_atoms'], note_atoms)
assert c_from_def == -16, c_from_def
b_from_def = subst(defs['b']['expansion_in_normalized_atoms'], note_atoms)
EA3_sol = s.solve(s.Eq(b_from_def, OLD['b'][0]), EA3_0)
assert len(EA3_sol) == 1 and s.expand(EA3_sol[0] - (-26 + 10 * z2)) == 0, EA3_sol
add('EA3.0.l0', 'E A3 raw (reflected first source derivative)', 'EA3_base', 0, 0, -26 + 10 * z2, 'note-implied',
    'solving this spec\'s definition of b (out/input_definitions.json) = note eq:oldbetas closed form of b, with the note '
    'atoms C3, d_v C3, C5, K4 and the exact two-kink atoms, for [eps^0 l^0] EA3_base (scripts/validation_targets.py; '
    'cf. review/old_inputs_from_note.py). The same spec definitions give c = -16 exactly.', 'raw')

# ---- 4. second-tail three-kink raw logs: lower-flow relation with the NOTE closed forms of a, A, p, E
for k, e in [(6, R(1, 3)), (5, R(-1, 15)), (4, R(-1, 3) - a_ / 4), (3, R(4, 3) + a_ / 6 + A_ / 3 - p_ / 3), (2, E_ / 2)]:
    add(f'A3dd_half.l{k}', '(A3_dd)/2 raw = Taylor [delta^2] of A3', 'A3_dd/2', 0, k, e, 'note-closed-forms',
        'lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archived check_V_logs.py; no archive '
        'number used); a, A, p, E from the note closed forms; reproduced from scratch by review/three_kink_independent.py', 'raw')

# ---- 5. note: higher-log predictions at 5-8 kinks
for k, e in [(6, R(244, 45)), (5, R(170, 3)), (4, 247 - R(316, 3) * z2)]:
    add(f'C7.l{k}', 'C7 normalized', 'C7[v0d0]', 0, k, e, 'note', f'{NOTE} l.719-723')
for k, e in [(6, R(-142, 45)), (5, R(-71, 5)), (4, R(14, 3) * z2 - R(55, 3))]:
    add(f'C5d.l{k}', 'd_delta C5 normalized', 'C5[v0d1]', 0, k, e, 'note', f'{NOTE} l.726-730')
for k, e in [(8, 0), (7, R(-6416, 315)), (6, R(-1622, 9)), (5, (3848 * z2 - 8824) / 15)]:
    add(f'C7v.l{k}', 'd_v C7 normalized', 'C7[v1d0]', 0, k, e, 'note', f'{NOTE} l.1051-1056')
for k, e in [(7, R(-1088, 315)), (6, R(-664, 15)), (5, 96 * z2 - R(3656, 15))]:
    add(f'K8.l{k}', 'K8 normalized', 'K8[v0d0]', 0, k, e, 'note', f'{NOTE} l.1058-1062')

# ---- 6. note closed forms of beta inputs and invariants
for nm, (e, src) in OLD.items():
    add(f'input.{nm}', f'beta input {nm}', nm, None, None, e, 'note', f'{NOTE} {src}', 'input')
add('input.calR', 'calR = 2G + k + 2q - 2b - f', '2*G + k + 2*q - 2*b - f', None, None, calR, 'note',
    f'{NOTE} l.629-634 ("exact period certificate"); fixes G, q, k only in this combination', 'input_combination')
for nm, e, src in [('D2', R(5, 2) + 2 * z2, 'l.568 (boxed)'), ('T2', 2 - 2 * z2 - 4 * z3, 'l.568 (boxed)'), ('C3', R(39, 16) + 2 * z2, 'l.570 (text)'),
                   ('C4', 4 - 4 * z2 - 8 * z3, 'l.570 (text)'), ('D3', R(21, 4) - 13 * z2 + 11 * z3 + 11 * z4, 'l.638 (boxed)'),
                   ('C5', R(11249, 1024) - R(361, 16) * z2 + 24 * z3 + R(49, 2) * z4, 'l.642-643 (boxed)')]:
    add(f'invariant.{nm}', f'invariant {nm}', nm, None, None, e, 'note', f'{NOTE} {src}', 'invariant',
        note='established before C6; must be reproduced by the old inputs')
for nm, e in [('P4', P4), ('R4', R4), ('S5', S5)]:
    add(f'period.{nm}', f'period {nm}', nm, None, None, e, 'note', f'{NOTE} eq:periods-low (l.527-533)', 'period')

# ---- 7. independent numerics (project-internal, not exact)
tki = json.load(open(SPEC / 'review' / 'three_kink_independent.json'))['inputs']
independent_values = []
for nm in ('V', 'alpha', 'beta', 'gamma'):
    independent_values.append({'id': f'input.{nm}', 'quantity': f'beta input {nm}', 'value': tki[nm]['value'],
                               'abs_accuracy': '1e-26', 'provenance': 'independent-numeric',
                               'source': 'review/three_kink_independent.py (dps 30; from-scratch semi-analytic eps expansion, '
                                         '1D tanh-sinh quadratures; its a, p, A, E agree with the note closed forms to 1e-28)'})

# EQ2, EZ2 at finite cutoff and note integral representations of A and E (independent numerical checks)
mp.mp.dps = 40
I = lambda r: 2 * (1 - r) * mp.log1p(-r) + 2 * r * mp.log(r)
fin = []
for eps in (mp.mpf(1) / 8, mp.mpf(1) / 10):
    fin.append({'moment': 'EQ2_base', 'eps': mp.nstr(eps, 3), 'value': mp.nstr(mp.quad(lambda r: I(r) / r, [eps, 1]), 32),
                'provenance': 'derived-here-exact (1D integral, mpmath 40 digits)', 'source': 'scripts/validation_targets.py'})
    fin.append({'moment': 'EZ2_base', 'eps': mp.nstr(eps, 3), 'value': mp.nstr(mp.quad(lambda r: I(r) / r**2, [eps, 1]), 32),
                'provenance': 'derived-here-exact (1D integral, mpmath 40 digits)', 'source': 'scripts/validation_targets.py'})
EQ2_fp = mp.quad(lambda r: 2 * (1 - r) * mp.log1p(-r) / r + 2 * mp.log(r), [0, 1])
EZ2_fp = mp.quad(lambda r: 2 * mp.log1p(-r) / r**2 + 2 / r, [0, 1]) - 2 * mp.quad(lambda r: mp.log1p(-r) / r, [0, 1])
A_int = -4 * mp.quad(lambda y: mp.log1p(-y)**2 / (y**2 * (1 - y)**2), [0, mp.mpf(1) / 2])
E_int = num(p_) + 4 * mp.quad(lambda y: mp.log1p(-y)**2 * (2 * mp.log(y) - mp.log1p(-y)) / (y**2 * (1 - y)**2), [0, mp.mpf(1) / 2])
checks = {
    'EQ2_base_eps0_numeric_minus_exact': mp.nstr(EQ2_fp - num(-2 * z2), 3),
    'EZ2_base_eps0l0_numeric_minus_exact': mp.nstr(EZ2_fp - num(2 * z2 - 2), 3),
    'A_note_integral_l588_minus_closed_form': mp.nstr(A_int - num(A_), 3),
    'E_note_integral_l592_minus_closed_form': mp.nstr(E_int - num(E_), 3),
    'S5_minus_4P4_equals_5+28z2+40z3': True,
    'c_from_spec_definition_with_note_atoms': str(c_from_def),
    'EA3_0_from_note_b': str(EA3_sol[0]),
}
for k_, v_ in checks.items():
    if k_.endswith(('exact', 'form')):
        assert abs(mp.mpf(v_)) < mp.mpf(10)**-30, (k_, v_)

# finite-cutoff values of the scipy convention check (independent, double precision)
sfc = json.load(open(OUT / 'sanity_finite_cutoff.json'))
for k_, v_ in sfc['values'].items():
    fin.append({'moment': k_, 'eps': '1/8', 'value': repr(v_), 'provenance': 'independent-numeric (scipy cubature, ~1e-10)',
                'source': 'scripts/sanity_finite_cutoff.py'})

FINITE_CUTOFF_CHECKS = {
    'definition': 'full ordered integral over Omega_n(eps) of the differentiated kernel at (v,delta)=(1,0), BEFORE any eps '
                  'expansion (the translation reduction gives the same number). E moments: reflected first source derivative.',
    'independent_values': fin,
    'cross_check_quantities': [
        {'moment': 'A3_d', 'eps': '1/8'}, {'moment': 'Z4_d', 'eps': '1/8'}, {'moment': 'A5_d', 'eps': '1/8'},
        {'moment': 'A7_base', 'eps': '1/8'}, {'moment': 'Q6_v', 'eps': '1/8'}, {'moment': 'EA5_base', 'eps': '1/8'},
        {'moment': 'A7_v', 'eps': '1/10'}, {'moment': 'Q8_base', 'eps': '1/10'}, {'moment': 'Q4_dd', 'eps': '1/10'}],
    'how_to_use': 'Compute each cross-check quantity by two independent routes inside the project (engine: exact/Mellin '
                  'value of the full moment at that eps; direct: Gauss/RQMC cubature) and require agreement within the '
                  'stated errors. Archived values of the same quantities are sealed in comparison/archive_comparison.json '
                  '(archive_finite_cutoff_values) for the final comparison step only. Finite-cutoff cubature validates '
                  'integrand conventions; it cannot isolate the [eps^0 l^1] single logs of the 6-8 kink atoms.',
}

out = {
    'note': 'ARCHIVE-FREE validation targets (scripts/validation_targets.py). No archive file read, no archive number used. '
            'Archive-derived predictions are sealed in comparison/archive_comparison.json.',
    'symbols': SYMBOLS_LEGEND,
    'conventions': {'series': 'C3[v1d0] = d_v C3 at (v,delta)=(1,0) (full normalized eps/log expansion); raw atoms as in '
                              'DEFINITIONS.raw_atoms; A3_dd/2 is the Taylor [delta^2] coefficient of A3',
                    'eps_power/log_power': 'coefficient [eps^p l^k], l = log eps; null for inputs/invariants'},
    'provenance_tags': {
        'note': 'stated in the note (line given)',
        'note-closed-forms': 'a relation evaluated with the note closed forms of the old inputs',
        'derived-here-exact': 'exact derivation from the spec definitions (script named)',
        'note-implied': 'fixed by a note closed form through this spec\'s own definitions',
        'independent-numeric': 'project-internal numerical computation, not exact'},
    'targets': targets,
    'exact_two_kink_raw_atoms': {'source': 'out/two_kink_exact.json (scripts/two_kink_exact.py)', 'provenance': 'derived-here-exact',
                                 'atoms': two},
    'independent_input_values': independent_values,
    'finite_cutoff': FINITE_CUTOFF_CHECKS,
    'internal_checks': checks,
    'archive_derived_targets_sealed': [
        '[l^7], [l^3] of C7[v0d0]', '[l^7], [l^3], [l^2] of C5[v0d1]', '[l^2]..[l^8] of K4[v0d2]/2 (second tail of K4)',
        'archived finite-cutoff values of the cross-check quantities',
        '(location: comparison/archive_comparison.json -> archive_derived_validation_predictions, archive_finite_cutoff_values)'],
}
json.dump(out, open(OUT / 'validation_targets.json', 'w'), indent=1)
print(len(targets), 'targets;', len(independent_values), 'independent values;', len(fin), 'finite-cutoff values')
print('checks', checks)
