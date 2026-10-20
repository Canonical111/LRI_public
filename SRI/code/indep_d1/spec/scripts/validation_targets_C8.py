#!/usr/bin/env python3
"""ARCHIVE-FREE validation targets for the C8 extension.  Collects (no new physics here):
  note                 the note's leading log of d_delta A7 (l.1355-1358) and the structural statements it implies;
  derived-here-exact   exact two-kink atoms (incl. EZ2/EQ2 MZV constants), closed-form higher logs of every C3 and K4 jet
                       (scripts/rg_logs_C8.py), the vanishing of [l^(top+1)], pole cancellation (scripts/poles_C8.py),
                       the F1-F4 leading raw coefficients (scripts/derive_requirements_C8.py);
  independent-numeric  W and the full eps^0 log polynomial of C3_ddd (review/three_kink_C8.py);
  data-dependent RG    second- and higher-log formulas of the 5-9 kink jets (scripts/rg_logs_C8.py), validated on the
                       phase-2 engine data (review/rg_logs_vs_engine_phase2.json);
  finite-cutoff        cross-check quantities for the new atoms (values to be produced inside the project).
Archive numbers of the C8 era are NOT here: they are sealed in ../comparison_C8/.
Output: ../out/C8/validation_targets_C8.json
"""
import json
from pathlib import Path
import sympy as s
import mpmath as mp

SPEC = Path(__file__).resolve().parent.parent
OUT = SPEC / 'out' / 'C8'
NOTE = 'note/LRI_perturbation_compendium.tex'
mp.mp.dps = 50
J = lambda p: json.load(open(p))
rg = J(OUT / 'rg_logs_C8.json')
tk = J(OUT / 'two_kink_exact_C8.json')
poles = J(OUT / 'poles_C8.json')
chain = J(OUT / 'definition_chain_C8.json')
tk8 = J(SPEC / 'review' / 'three_kink_C8.json')
rgv = J(SPEC / 'review' / 'rg_logs_vs_engine_phase2.json') if (SPEC / 'review' / 'rg_logs_vs_engine_phase2.json').exists() else None

targets = []
def add(tid, quantity, series, p, k, exact, provenance, source, kind='raw', remark=None, value=None):
    rec = {'id': tid, 'quantity': quantity, 'series': series, 'eps_power': p, 'log_power': k, 'kind': kind,
           'exact': exact, 'provenance': provenance, 'source': source}
    if value is not None:
        rec['value'] = value
    if remark:
        rec['remark'] = remark
    targets.append(rec)

# ---- note
add('A7d.0.l8', 'd_delta A7 raw', 'A7_d', 0, 8, '-2362/315', 'note', f'{NOTE} l.1355-1358 ("separately derived leading logarithm")',
    value=mp.nstr(mp.mpf(-2362) / 315, 40), remark='raw moment (not normalized); the engine computes the full log polynomial of '
    'A7_d at eps^0 in the same job as the needed [eps^0 l^1]')
add('A7d.0.l9', 'd_delta A7 raw', 'A7_d', 0, 9, '0', 'note', f'{NOTE} l.1357', value='0')

# ---- derived here: exact two-kink endpoint constants (the Z2/Q2 tables are complete rationals)
for atom, c in tk['constants'].items():
    add(f'{atom}.0.l0', f'{atom} raw [eps^0 l^0] (reflected first source derivative)', atom, 0, 0, c['eps0_l0_exact'],
        'derived-here-exact', 'scripts/two_kink_exact_C8.py (1D integral after the exact X1 integration; PSLQ at 80 digits, '
        f'verified at 100 digits, residual {c["residual_at_100_digits"]})', value=c['eps0_l0_decimal_60'][:52])

# ---- derived here: closed-form higher logs of the C3 and K4 jets
for key, logs in rg['C3_jets_all_logs']['jets'].items():
    tg = key[3:-1]
    for k, r in logs.items():
        add(f'C3[{tg}].l{k}', f'd^{tg} C3 normalized (= A3_{tg} - Z2_{tg}) [eps^0 l^{k}]', f'C3[{tg}]', 0, int(k), r['prediction'],
            'derived-here-exact', 'scripts/rg_logs_C8.py (Callan-Symanzik with the nonautonomous auxiliary flow); closed form in the '
            'b3 Taylor coefficients', kind='normalized', value=r['value'],
            remark='value with the note closed forms of a, p, A, E and the independent three-kink V, alpha, beta, gamma, W; agrees '
                   f'with review/three_kink_independent.json / three_kink_C8.json (max rel. diff {rg["C3_jets_all_logs"]["max_relative_difference"]})')
for key, logs in rg['K4_jets_all_logs']['jets'].items():
    tg = key[3:-1]
    for k, r in logs.items():
        add(f'K4[{tg}].l{k}', f'd^{tg} K4 normalized (= Q4_{tg} - (Q2 Z2)_{tg}) [eps^0 l^{k}]', f'K4[{tg}]', 0, int(k), r['prediction'],
            'derived-here-exact', 'scripts/rg_logs_C8.py; closed form in the b3, h4 Taylor coefficients and zeta values', kind='normalized',
            value=r.get('value_with_note_and_three_kink_inputs'),
            remark='checked on the phase-2 engine data for base, v, d, vv, vd, dd (review/rg_logs_vs_engine_phase2.json)')

# ---- independent numerics
independent = [{'id': 'input.W', 'quantity': 'beta input W = d_delta^3 b3 / 6', 'value': tk8['inputs']['W']['value'],
                'abs_accuracy': '1e-25', 'provenance': 'independent-numeric',
                'source': 'review/three_kink_C8.py (phase-1 reviewer three-kink code, ddd added; dps 30)'}]
for k, v in tk8['C3_eps0_logcoeffs']['ddd'].items():
    independent.append({'id': f'C3[ddd].l{k}', 'quantity': f'd_delta^3 C3 [eps^0 l^{k}]', 'value': v, 'abs_accuracy': '1e-25',
                        'provenance': 'independent-numeric', 'source': 'review/three_kink_C8.py'})
for k, v in tk8['A3_eps0_logcoeffs']['ddd'].items():
    independent.append({'id': f'A3_ddd.0.l{k}', 'quantity': f'raw A3_ddd [eps^0 l^{k}]', 'value': v, 'abs_accuracy': '1e-25',
                        'provenance': 'independent-numeric', 'source': 'review/three_kink_C8.py'})

out = {
    'note': 'ARCHIVE-FREE validation targets for the C8 extension (scripts/validation_targets_C8.py). Archive numbers of the C8 era '
            'are sealed in comparison_C8/.',
    'provenance_tags': {'note': 'stated in the note (line given)',
                        'derived-here-exact': 'exact derivation in this directory (script named)',
                        'independent-numeric': 'project-internal numerical computation, not exact',
                        'data-dependent-RG': 'exact identity among data; evaluate with the project data and compare'},
    'targets': targets,
    'independent_values': independent,
    'exact_two_kink_atoms': {'source': 'out/C8/two_kink_exact_C8.json', 'atoms': sorted(tk['atoms']),
                             'remark': 'Z2_*, Q2_* complete rationals; EZ2_*, EQ2_* exact (MZV constant at eps^0 l^0); may be used '
                                       'directly as raw inputs and are targets for any engine value of them'},
    'structural_zeros': {
        'top_log': 'for a jet d_v^i d_delta^j of a normalized response of order n (C_n, K_n), [eps^0 l^k] = 0 for k > n - 1 + i + 2j; '
                   'checked by the RG formulas (the predicted [l^(top+1)] vanishes identically) and on the phase-2 data',
        'raw_A7_d': '[eps^0 l^9] A7_d = 0 (note)',
        'pole_cancellation': {'source': 'out/C8/poles_C8.json', 'n_jets': poles['n_jets'], 'n_new_jets': poles['n_new_jets'],
                              'statement': 'every [eps^p l^k], p < 0, of every normalized jet vanishes; the raw windows needed for '
                                           'the new jets are poles_C8.json -> raw_needed_for_new_jets (all log powers)'},
        'below_tight_bound': 'the 12 safe-minus-tight scalars below the tight bound (raw_requirements_C8.json -> safe_minus_tight) vanish'},
    'data_dependent_RG': {
        'source': 'out/C8/rg_logs_C8.json -> second_log_formulas, higher_log_formulas',
        'statement': 'for every C/K jet of order n >= 5 used by the C8 inputs (incl. C9, d_delta C7, d_v K8, d_v^2 K6, d_v d_delta K6, '
                     'd_delta^2 C5) the coefficients [eps^0 l^k], k = 2 .. top+1, are predicted from lower-order data (normalized C, K '
                     'and E jets at log powers < k) and the beta inputs',
        'extra_normalized_atoms_for_the_second_log': rg['second_log_formulas']['extra_normalized_atoms_needed'],
        'validation': (None if rgv is None else {'phase2_engine_checks': rgv['n_checks'], 'max_abs_pull': rgv['max_abs_pull'],
                                                  'rms_pull': rgv['rms_pull'], 'source': 'review/rg_logs_vs_engine_phase2.json'}),
        'l0_identity': 'the [l^0] part of the same identity reproduces the recurrence for all 35 inputs (rg_logs_C8.json -> '
                       'l0_identity_equals_recurrence), including lambda6, j7 and b9'},
    'note_structure_checks': chain['note_F1_F4_structure_checks'],
    'finite_cutoff_cross_check_quantities': {
        'definition': 'full ordered integral over Omega_n(eps) of the differentiated kernel at (v,delta) = (1,0), before any eps '
                      'expansion; E moments with the reflected first source derivative',
        'quantities': [{'moment': m, 'eps': e} for m, e in [
            ('A3_ddd', '1/8'), ('Q4_vvv', '1/8'), ('Q4_vvd', '1/8'), ('Q4_vdd', '1/8'), ('EQ4_vd', '1/8'), ('EQ4_vv', '1/8'),
            ('A5_dd', '1/8'), ('EA5_d', '1/8'), ('Z6_d', '1/10'), ('Q6_vv', '1/10'), ('Q6_vd', '1/10'), ('EQ6_v', '1/10'),
            ('EZ6_base', '1/10'), ('A7_d', '1/10'), ('EA7_base', '1/10'), ('Q8_v', '1/10'), ('Z8_base', '1/10'), ('A9_base', '1/10')]],
        'how_to_use': 'two independent project routes (engine series at that eps vs direct cubature); archived values of some of them '
                      '(e.g. Q6_vv(1/10)) are sealed in comparison_C8/ for the final comparison only. Finite-cutoff cubature checks '
                      'conventions; it cannot isolate the single logs of the 6-9 kink atoms.'},
    'archive_derived_targets_sealed': [
        'rational projections pi_0 of the ten inputs, R6, R8, R_tail, R9, C8^(0) = 88 and the raw rational scalars (note l.1176-1227)',
        'singular rational predictions of Q6_vd and Q8_v (note l.1236-1246)',
        'every C8-era decimal of the note Secs. 16-17 and of the archive records (comparison_C8/archive_C8_values.json)'],
}
json.dump(out, open(OUT / 'validation_targets_C8.json', 'w'), indent=1)
print(len(targets), 'targets;', len(independent), 'independent values')
