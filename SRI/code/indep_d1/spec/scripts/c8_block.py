#!/usr/bin/env python3
"""Build the C8_EXTENSION block of ../spec_definitions.json from the archive-free files in ../out/C8/ and the reviewer
outputs in ../review/ (called by build_spec.py; never reads ../comparison*/ or the compendium)."""
import hashlib, json
from math import comb, factorial
from pathlib import Path
import sympy as s

SPEC = Path(__file__).resolve().parent.parent
OUTC8 = SPEC / 'out' / 'C8'
C8_DATE = '2026-10-03'
NEW = ['W', 'S', 'U', 'J9', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'Kv']
FILES = ['input_definitions_C8.json', 'normalized_atoms_C8.json', 'raw_requirements_C8.json', 'definition_chain_C8.json',
         'two_kink_exact_C8.json', 'invariants_C8.json', 'rg_logs_C8.json', 'poles_C8.json', 'budget_C8.json',
         'validation_targets_C8.json']


def insertion_string(a, b):
    """d_v^a d_delta^b W_n / W_n at (1,0) in terms of S_j = sum_{i<k} q_i q_k log^j(X_k - X_i)"""
    z, d = s.symbols('z d')
    Sj = s.symbols('S1:6')
    X = 2 * z * Sj[0] + 2 * (1 + z) * sum(d**(j - 1) * Sj[j - 1] / s.factorial(j) for j in range(2, b + 2))
    ex = s.expand(sum(X**n / s.factorial(n) for n in range(a + b + 1)))
    c = s.Poly(ex, z, d).coeff_monomial(z**a * d**b) * s.factorial(a) * s.factorial(b)
    return s.sstr(s.expand(c)).replace('**', '^') if c != 1 else '1'


def tag_ab(tag):
    return (0, 0) if tag == 'base' else (tag.count('v'), tag.count('d'))


def integrand(atom):
    base, der = atom.split('_', 1)
    kind = base.rstrip('0123456789'); n = int(base[len(kind):])
    a, b = tag_ab(der)
    dip = f'D_{n} * ' if kind.endswith('Q') else ''
    if not kind.startswith('E'):
        return f'int_{{Omega_{n}(eps)}} d^{n}X  {dip}[{insertion_string(a, b)}] * W_{n}'
    terms = [f'{comb(b, j)}*e{j}*[{insertion_string(a, b - j)}]' for j in range(b + 1)]
    return f'int_{{Omega_{n}(eps)}} d^{n}X  {dip}(' + ' + '.join(terms) + f') * W_{n}'


def pmin_tight(atom):
    base = atom.split('_')[0]
    kind = base.rstrip('0123456789'); m = int(base[len(kind):]) // 2
    if kind in ('A', 'Z', 'EA'):
        return -m
    if kind in ('Q', 'EZ'):
        return -(m - 1)
    return 0 if m == 1 else -(m - 1)


def build():
    J = lambda n: json.load(open(OUTC8 / n))
    defs, norm, req, chain = J('input_definitions_C8.json'), J('normalized_atoms_C8.json'), J('raw_requirements_C8.json'), J('definition_chain_C8.json')
    tk, inv, rg, poles, bud, vt = (J(n) for n in ('two_kink_exact_C8.json', 'invariants_C8.json', 'rg_logs_C8.json', 'poles_C8.json',
                                                  'budget_C8.json', 'validation_targets_C8.json'))
    rev = {n: json.load(open(SPEC / 'review' / f'{n}.json')) for n in ('three_kink_C8', 'crosscheck_framework_C8', 'rg_logs_vs_engine_phase2',
                                                                       'crosscheck_framework_C8_assembly')
           if (SPEC / 'review' / f'{n}.json').exists()}
    used_by = {}
    for nm, d in defs.items():
        for a in d['raw_requirements_tight']:
            used_by.setdefault(a, []).append(nm)
    raw_atoms = {}
    for atom, info in req['total_tight'].items():
        kind = atom.split('_')[0].rstrip('0123456789')
        n = int(atom.split('_')[0][len(kind):])
        raw_atoms[atom] = {
            'kinks': n, 'endpoint_source': kind.startswith('E'), 'derivative': atom.split('_', 1)[1],
            'd_v_order': tag_ab(atom.split('_', 1)[1])[0], 'd_delta_order': tag_ab(atom.split('_', 1)[1])[1],
            'integrand_at_v1_delta0': integrand(atom),
            'endpoint_factor_if_unreflected': (None if not kind.startswith('E') else
                                               ('U^odd: sum_i q_i[f(X_i)+f(1-X_i)]' if n % 2 else 'U^even: sum_i q_i[f(X_i)-f(1-X_i)]')),
            'integration_dimension_after_translation': n - 1 if not kind.startswith('E') else n,
            'tight_leading_eps_power': pmin_tight(atom),
            'needed_log_orders_by_power_tight': info['log_orders_by_power'],
            'needed_log_orders_by_power_safe': req['total_safe'][atom]['log_orders_by_power'],
            'new_atom_for_C8': atom in req['counts']['new_atoms'],
            'exact_expansion_available': atom in tk['atoms'],
            'used_by_inputs': used_by.get(atom, [])}
    block = {
        'meta': {
            'title': 'C8 extension of the definitions-only spec: the ten new inputs of C8 = 8 T4',
            'date': C8_DATE,
            'archive_free': 'Contains NO archive-derived number. Every C8-era archive number (the ten inputs, A9_1, Z8_1, (EA7)_0, '
                            '(EZ6)_0, D9_lower, A7_d_1, D_known, P6, P8, X_vv, X_E, S3, B_old, B_done, C_fixed, C8, rational '
                            'projections) is sealed in comparison_C8/, which production code never reads.',
            'sources': 'note/LRI_perturbation_compendium.tex Secs. 14-18 (l.1100-1460): eq:C8trace, eq:C8F, eq:C8H (l.1106-1116), '
                       'derivative dictionary (l.1120-1137), eq:K8norm, eq:C9norm, h8, eq:b9, j7 (l.1139-1158), eq:C8assembly '
                       '(l.1162-1166), appendix app:C8polynomial (l.2781-2806); Secs. 3-6 for the integrals.',
            'scripts': ['scripts/derive_requirements_C8.py', 'scripts/two_kink_exact_C8.py', 'scripts/derive_invariants_C8.py',
                        'scripts/rg_logs_C8.py', 'scripts/poles_C8.py', 'scripts/budget_C8.py', 'scripts/validation_targets_C8.py',
                        'review/three_kink_C8.py', 'review/rg_logs_vs_engine_phase2.py', 'review/crosscheck_framework_C8.py',
                        'review/crosscheck_framework_C8_assembly.py', 'scripts/assemble_from_raw_C8.py', 'scripts/test_assembler_C8.py'],
            'generated_from': {f'out/C8/{n}': hashlib.sha256((OUTC8 / n).read_bytes()).hexdigest() for n in FILES},
        },
        'CLAIMS_UNDER_TEST': {
            'remark': 'Claims of the note about C8 (expressions only). Their decimal values are archive numbers or would coincide with '
                      'them to ~1e-86; they are sealed in comparison_C8/ and not reproduced here.',
            'C8 = 8 T4': 'note eq:C8trace (l.1104); C8 multiplies x^4 = t^8; no D5 enters (checked here by eigenvalue expansion)',
            'C8_candidate': '88 - 178 z2 + 110 z3 + 113 z4 + 4892 z5 - 2376 z2 z3 - (8630/3) z6 + 1872 z3^2 - 12168 z7 + 6048 z2 z5 '
                            '+ 1536 z3 z4  (note eq:C8-candidate-main l.92-100; UNPROVED in the note)',
            'C8_assembly': 'C8 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta + 1/32 Kv '
                           '(eq:C8assembly; reproduced exactly here, invariants_C8.json)',
            'note_relations_tested_structurally': ['N_delta = -4 P6 + known (eq:NdP6)', 'U = A7_d_1 - Z6_d_1 + 2(EA5_d)_0 - 2(EZ4_d)_0 + D_lower',
                                                   'K_v = -4 P8 + 16 X_vv - 8 X_E + S3', 'J9 = A9_1 - Z8_1 + 2(EA7)_0 - 2(EZ6)_0 + D9_lower',
                                                   'C8 = C_fixed - P6/2 (eq:C8short): dC8/d[eps^0 l^1]Q6_vd = -1/2 (budget_C8.json)'],
        },
        'DEFINITIONS': {
            'new_inputs': {nm: {k: defs[nm][k] for k in ('group', 'definition', 'expansion_in_normalized_atoms', 'n_terms',
                                                           'normalized_atoms', 'constant_part', 'max_kinks', 'depends_on_lambda6')}
                           | {'raw_atoms_tight': {a: r['log_orders_by_power'] for a, r in defs[nm]['raw_requirements_tight'].items()},
                              'raw_atoms_safe': {a: r['log_orders_by_power'] for a, r in defs[nm]['raw_requirements_safe'].items()},
                              'C8_coefficient': inv['C8_new_coefficients'][nm]}
                           for nm in NEW},
            'dictionary': {'W': 'b3_ddd/6', 'S': 'b5_dd/2', 'U': 'b7_d', 'J9': 'b9', 'L3': '-(2/3) h4_vvv', 'M21': '-2 h4_vvd',
                           'M12': '-2 h4_vdd', 'N2': '-2 h6_vv', 'Ndelta': '-4 h6_vd', 'Kv': '-4 h8_v',
                           'rule': 'full derivatives at (v,delta) = (1,0); Taylor factors only as displayed; mixed first derivatives '
                                   'carry no 1/2 (note l.1137)'},
            'all_35_inputs_file': 'out/C8/input_definitions_C8.json (the 25 old ones identical to out/input_definitions.json)',
            'normalized_responses': chain['normalized_responses'],
            'recurrence_9th_order': chain['recurrence_9th_order'],
            'lambda6_dependence': chain['lambda6_dependence'],
            'new_normalized_atoms': {k: {kk: v[kk] for kk in ('meaning', 'leibniz_expansion', 'n_leibniz_terms', 'raw_windows_tight',
                                                               'raw_windows_safe', 'used_by_inputs')}
                                     for k, v in norm.items() if v['new_for_C8']},
            'all_normalized_atoms_file': 'out/C8/normalized_atoms_C8.json',
            'derivative_insertions (multiply W_n at (1,0); new tags)': {t: insertion_string(*tag_ab(t)) for t in
                                                                        ('ddd', 'vvvv', 'vvvd', 'vvdd', 'vvv', 'vvd', 'vdd', 'dd')},
            'E derivative pieces (reflected)': 'e_j = d_delta^j e at delta = 0 = (2/(j+1)) sum_i q_i log^{j+1} X_i: e0 = 2 sum q log X, '
                                               'e1 = sum q log^2 X, e2 = (2/3) sum q log^3 X, e3 = (1/2) sum q log^4 X; '
                                               'd_delta^b (E M) = sum_j binom(b,j) e_j * [insertion of d_v^a d_delta^(b-j)]',
            'raw_atoms': raw_atoms,
            'beta_jets': inv['jets'],
            'assembly': {'C8 = 8 T4': 'B_old + new part', 'new_part': inv['C8_new_part'], 'B_old_C8': inv['B_old_C8'],
                         'B_old_C8_n_terms': inv['B_old_C8_n_terms'], 'T4': inv['T4']},
        },
        'EXTRAPOLATIONS': [{
            'id': 'lambda6',
            'statement': 'lambda6 = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0',
            'status_C8': 'Still not written in the note. It now enters K (old), Kv = -4 h8_v and J9 = b9 (through -2 v j1 h8); the other '
                         'eight new inputs do not depend on it (exact test, definition_chain_C8.json -> lambda6_dependence).',
            'support': ['the [l^0] part of the Callan-Symanzik identity of scripts/rg_logs_C8.py (response model F_H = h + sqrt2 b_h sum '
                        'g^n N^n K_n, essential flow autonomous) gives exactly this lambda6 and the whole recurrence for all 35 inputs',
                        'framework/framework.md Sec. 3 derives lambda_n = -2 K_n0 - 4 v d_v K_n0 + 2 v E K_n0 from J0 beta = R1',
                        'the note F3 decomposition K_v = -4 P8 + 16 X_vv - 8 X_E + S3 (l.1363) has exactly the coefficients this '
                        'lambda6 implies (+16 on [eps^0 l^0] Q6_vv, -8 on [eps^0 l^0] d_v E Q6; definition_chain_C8.json)']}],
        'RAW_MOMENT_REQUIREMENTS': {
            'summary': (f"C8 (all 35 inputs): tight set {req['counts']['scalars_tight_C8']} scalars in {req['counts']['atoms_tight_C8']} raw "
                        f"atoms ({req['counts']['scalars_tight_new']} beyond the C7 set, {len(req['counts']['new_atoms'])} new atoms); safe set "
                        f"{req['counts']['scalars_safe_C8']} ({req['counts']['below_tight_bound_C8']} below the tight bound must vanish, "
                        f"{len(req['safe_minus_tight']['genuine_positive_power_extras'])} genuine positive-power extras). "
                        f"{req['counts']['two_kink_scalars_tight_C8']} tight scalars are Z2_*/Q2_* (exact rationals) and all EZ2_*/EQ2_* "
                        f"scalars are exact too (out/C8/two_kink_exact_C8.json). Only l^0, l^1 of a raw coefficient reach a beta input; "
                        f"the higher-log and pole targets need the same atoms with all log powers (poles_C8.json lists the extra negative powers)."),
            'counts': req['counts'], 'tight_bounds': req['tight_bounds'], 'safe_bounds': req['safe_bounds'],
            'safe_minus_tight': req['safe_minus_tight'],
            'new_tight_scalars_relative_to_C7': req['new_tight_scalars_relative_to_C7'],
            'tight': {a: r['log_orders_by_power'] for a, r in req['total_tight'].items()},
            'safe': {a: r['log_orders_by_power'] for a, r in req['total_safe'].items()},
            'framework_cross_check': (rev['crosscheck_framework_C8']['b_requirements_vs_framework'] if 'crosscheck_framework_C8' in rev else None),
            'precision_budget': {'source': 'out/C8/budget_C8.json',
                                 'statement': 'exact dC8/dx for the 85 non-exact new scalars (51 constant): e.g. A9[eps^0 l^1] +1/4, '
                                              'Z8 -1/4, (EA7)_0 +1/2, (EZ6)_0 -1/2, A7_d[eps^0 l^1] +3/4, Z6_d -3/4, Q8_v[eps^0 l^1] '
                                              '-1/8, Q6_vv[eps^0 l^0] +1/2, (d_v EQ6)_0 -1/4, Q6_vd[eps^0 l^1] -1/2, A3_ddd +2/3, '
                                              'A5_dd +1; a 1e-4 test of C8 needs each of these to ~1e-4/|dC8/dx| absolute',
                                 'largest': bud['largest_constant_sensitivities'][:15]},
            'hardest': ['A9_base [eps^0 l^1] (8-dim, J9)', 'Z8_base [eps^0 l^1] (7-dim, J9)', 'Q8_v [eps^0 l^1] (7-dim, Kv)',
                        'A7_d [eps^0 l^1] (6-dim, U)', 'EA7_base [eps^0 l^0] (7-dim absolute, J9)', 'Q6_vd [eps^0 l^1] (5-dim, Ndelta)',
                        'Q6_vv [eps^0 l^0, l^1] (Kv, N2)', 'EQ6_v, EZ6_base [eps^0 l^0] (6-dim absolute)', 'Z6_d [eps^0 l^1] (U)'],
        },
        'VALIDATION_TARGETS': vt,
        'SPEC_CHECKS_ARCHIVE_FREE': {
            'normalization': chain['normalized_response_checks'],
            'regression_vs_phase1': chain['regression_vs_phase1'],
            'note_F1_F4_structure': chain['note_F1_F4_structure_checks'],
            'trace_algebra': inv['checks'],
            'rg_l0_identity_equals_recurrence_all_35': all(all(v for k, v in r.items() if k.startswith('equal'))
                                                           for r in rg['l0_identity_equals_recurrence'].values()),
            'rg_C3_jets_vs_three_kink_max_rel_diff': rg['C3_jets_all_logs']['max_relative_difference'],
            'rg_note_checks': rg['C3_note_checks'] | rg['K4_jets_all_logs']['note_checks'],
            'rg_vs_phase2_engine': ({k: rev['rg_logs_vs_engine_phase2'][k] for k in ('n_checks', 'max_abs_pull', 'rms_pull')}
                                    if 'rg_logs_vs_engine_phase2' in rev else None),
            'two_kink': tk['checks'],
            'framework_cross_check': ({'expansions_all_35_identical': rev['crosscheck_framework_C8']['a_expansions_vs_framework']['all_identical'],
                                       'endpoint_two_kink_max_abs_difference': rev['crosscheck_framework_C8']['c_endpoint_two_kink_vs_framework']['max_abs_difference']}
                                      if 'crosscheck_framework_C8' in rev else None),
            'W_independent_three_kink': (rev['three_kink_C8']['inputs']['W'] if 'three_kink_C8' in rev else None),
            'framework_assembly_on_synthetic_data_max_rel_diff (35 inputs, C5..C8)': (
                rev['crosscheck_framework_C8_assembly']['max_relative_difference'] if 'crosscheck_framework_C8_assembly' in rev else None),
            'assembler_regression_test': 'scripts/test_assembler_C8.py (synthetic): all six checks pass',
        },
        'ASSEMBLER': {
            'script': 'scripts/assemble_from_raw_C8.py raw.json [--windows both|tight|safe] [--fill-two-kink-exact] [--out result.json]',
            'layout': 'plain {atom: {p: {k: value}}}, full derivatives, E = reflected first source derivative (as phase 1)',
            'outputs': 'all 35 inputs, D2..D4, C3..C7, B_old_C8, B_done_C8 (B_old + the six inherited-record terms), T4, C8 '
                       '(= B_old + linear part, checked against 8 T4)',
            'strictness': 'as phase 1 (missing scalar = error; below-bound scalars must vanish; tight/safe agreement); in addition '
                          'C3_1[v0d0] must equal 5 (the tree normalization b3(1,0) = 1 assumed by the invariant algebra)',
            'compares_with': 'nothing: the C8 claims are sealed in comparison_C8/'},
        'AMBIGUITIES_AND_DISCREPANCIES': [
            {'id': 'lambda6', 'issue': 'lambda6 is used in h8 but not defined in the note; it now affects Kv and J9 as well as K.',
             'resolution': 'see EXTRAPOLATIONS (derived from the response Jacobian / CS identity; the note F3 structure agrees)'},
            {'id': 'raw-vs-normalized-leading-log', 'issue': 'The note leading log -2362/315 refers to the RAW d_delta A7, not to the '
             'normalized d_delta C7; products with Z2 ~ 1/eps mix positive-power raw logs into the normalized one.',
             'resolution': 'target A7d.0.l8 is on the raw atom; the normalized jets have their own RG predictions'},
            {'id': 'inherited-six', 'issue': 'The note says W, S, L3, M21, M12, N2 enter the archive assembly as inherited numerical '
             'records without a reconstructed exact expression (l.1240-1252).',
             'resolution': 'definitions here are the note dictionary only; W is computed independently (three-kink code); the other '
                           'five need the engine. No archive record is used.'},
            {'id': 'E-on-delta-derivatives', 'issue': 'd_delta acts on the endpoint factor as well as on the kernel (note l.421 "Tail '
             'derivatives also act on endpoint factors").', 'resolution': 'raw_atoms integrands: sum_j binom(b,j) e_j * insertion(a,b-j)'},
            {'id': 'reflection', 'issue': 'Only first source derivatives are needed (j7 = -2 d_v C7_0 + (E C7)_0, lambda6 with E K6); '
             'the reflected form is valid for all of them, with any d_v, d_delta.', 'resolution': 'either form'},
            {'id': 'b3-normalization', 'issue': 'The CS identity and the trace algebra use b3(1,0) = 1 (F = z + u + ...), which the '
             'input expansions write as C3_1[v0d0] - 4; they agree because C3_1[v0d0] = 5 (note l.550). Data that violate it give '
             'inputs and invariants on different footings (the framework then differs from the spec assembler).',
             'resolution': 'the C8 assembler rejects data with |C3_1[v0d0] - 5| > agree-tol'},
            {'id': 'structural-zeros', 'issue': 'As in phase 2, some needed scalars are exact zeros (e.g. A3 at eps^-1 l^1, eps^3 l^1, '
             'Z4 eps^-2 l^1; every EZ2/EQ2 eps^-1). They must be supplied explicitly.', 'resolution': 'two_kink_exact_C8.json; A3 closed '
             'form of framework/review_gate_phase2'},
        ],
    }
    return block
