#!/usr/bin/env python3
"""Write ../spec.md (human-readable, ARCHIVE-FREE) from ../spec_definitions.json."""
import json
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent
s = json.load(open(SPEC / 'spec_definitions.json'))
D = s['DEFINITIONS']; R = s['RAW_MOMENT_REQUIREMENTS']; V = s['VALIDATION_TARGETS']; C = s['CLAIMS_UNDER_TEST']
L = []
w = L.append

w('# Specification (definitions only): independent re-derivation of the C6/C7 inputs (d=1 LRI, short-range end)\n')
w(f"Generated {s['meta']['created']} by `scripts/make_spec_md.py` from `spec_definitions.json` (version {s['meta']['version']}). "
  'The compendium `<PROJECT>/LRI_SRI_research_compendium` was only read.\n')
w('**This file contains no archive-derived number.** Every value below is a note statement, an exact derivation, a value '
  'implied by a note closed form, or a project-internal computation; each validation target carries a provenance tag. '
  'Archive numbers are sealed in `comparison/archive_comparison.json`, which production code never reads and which is '
  'consulted only in the final comparison step. `spec.json` is a deprecated copy in the old key layout.\n')
w('## 0. Claims under test\n')
for k in ('C6', 'T3', 'D4', 'C7'):
    w(f"* **{k}** = {C[k]['closed_form']} = {C[k]['value'][:34]}...")
w('\nEstablished lower orders (must be reproduced by the old inputs): ' +
  '; '.join(f"{k} = {v['closed_form']}" for k, v in C['established_lower_order'].items()) + '.\n')

w('## 1. Conventions\n')
for k, v in s['CONVENTIONS'].items():
    w(f'* **{k}**: {v}')
w('')
w('## 2. Integrals (raw moments)\n')
for k in ('f_delta', 'charges', 'domain', 'kernel', 'dipole'):
    w(f'* **{k}**: `{D[k]}`')
rm = D['raw_moments']
w('')
for k in ('A_{2m+1}', 'Z_{2m}', 'Q_{2m}', 'A_1', 'E M_n', 'E derivative pieces (reflected)', 'S_j', 'derivative_naming', 'eps_expansion',
          'coordinate_reductions (optional, value-preserving)'):
    w(f'* **{k}**: {rm[k]}')
w('\nDerivative insertions (full derivatives, multiply W_n at (v,delta)=(1,0)):\n')
w('| atom suffix | d_v^a d_delta^b | insertion |\n|---|---|---|')
DV = {'base': '(0,0)', 'v': '(1,0)', 'vv': '(2,0)', 'vvv': '(3,0)', 'd': '(0,1)', 'vd': '(1,1)', 'vvd': '(2,1)', 'dd': '(0,2)', 'vdd': '(1,2)'}
for k, v in rm['derivative_insertions (multiply W_n at (1,0))'].items():
    w(f'| `{k}` | {DV[k]} | `{v}` |')
w('\nFor an endpoint-source atom `EM_<der>` with (a,b): integrand = sum_j binom(b,j) e_j * [insertion (a,b-j)] * W_n '
  '(times D_n for EQ). Example: `EQ2_dd` = int D_2 (e0 [S2^2+(2/3)S3] + 2 e1 S2 + e2) W_2. The two-kink insertions are '
  're-derived from the exponent in `scripts/two_kink_exact.py` and agree with this table.\n')

w('## 3. Normalized responses, coefficient extraction, recurrence\n')
for k, v in D['normalized_responses'].items():
    w(f'* `{k} = {v}`' if k != 'origin' else f'* origin: {v}')
w(f"\n**Extraction.** {D['coefficient_extraction']}\n")
w(f"**Derivatives.** {D['derivative_of_coefficients']}\n")
w('**Finite-response recurrence** (note eq:subtraction l.427-444 and l.1150-1151):\n')
w('```')
for k, v in D['recurrence'].items():
    if k not in ('notes', 'sources'):
        w(f'{k:8s} = {v}')
w('```')
w(D['recurrence']['sources'] + ' ' + D['recurrence']['notes'] + '\n')
w(f"**Beta jets.** F = `{D['beta_jets']['F']}`\n\nH = `{D['beta_jets']['H']}`\n\n{D['beta_jets']['meaning']}\n")

w('## 4. Extrapolations beyond the note\n')
for e in s['EXTRAPOLATIONS']:
    w(f"* **{e['id']}**: `{e['statement']}`  \n  *Status:* {e['status']}")
    for k in ('jacobian_extension', 'affects', 'how_to_test'):
        if k in e:
            w(f"  *{k.replace('_', ' ').capitalize()}:* {e[k]}")
w('')

w('## 5. The 25 inputs (definition chains)\n')
w('Atom notation: `C3_1[v1d0]` = [eps^0 l^1] d_v C3 at (1,0); `K2` = Q2, `EK2` = EQ2. The full expansions (up to 101 terms, Omega) '
  'and each normalized atom\'s Leibniz expansion and windows are in `spec_definitions.json` (`DEFINITIONS.inputs`, '
  '`DEFINITIONS.normalized_atoms`).\n')
w('| input | group | definition | #terms | max kinks | expansion (if short) |\n|---|---|---|---|---|---|')
for k, v in D['inputs'].items():
    ex = v['expansion_in_normalized_atoms']
    flag = ' (uses lambda6)' if v.get('uses_lambda6_extrapolation') else ''
    w(f"| {k} | {v['group']} | {v['definition'].split('  at')[0]}{flag} | {v['n_terms']} | {v['max_kinks']} | "
      f"{('`' + ex + '`') if len(ex) < 160 else '(see spec_definitions.json)'} |")
w('\n**Matching and canonical terms.**\n')
for k, v in D['matching_and_canonical_terms'].items():
    w(f'* **{k}**: {v}')
w('\n**Assemblies** (independently derived in `scripts/derive_invariants.py`; equal to the note\'s printed formulas):\n')
w('```')
for k, v in D['assemblies'].items():
    if k not in ('fixed_point', 'conversion'):
        w(f'{k} = {v}')
w('conversion: ' + ', '.join(f'{a} = {b}' for a, b in D['assemblies']['conversion'].items() if a.startswith('C')))
w('fixed point: ' + ', '.join(f'{a}={b}' for a, b in D['assemblies']['fixed_point'].items()))
w('```\n')

w('## 6. Raw-moment requirements (tight and safe windows)\n')
w(R['summary'] + '\n')
w(f"* **tight bounds:** {R['tight_bounds']}\n* **argument:** {R['tight_bounds_argument']}\n* **safe bounds:** {R['safe_bounds']}\n"
  f"* **safe extras that must vanish:** {', '.join(R['safe_minus_tight']['below_tight_bound_must_vanish'])}\n"
  f"* **genuine positive-power safe extras:** {', '.join(R['safe_minus_tight']['genuine_positive_power_extras'])}\n"
  f"* **policy:** {R['policy']}\n")
w('Each entry `p:[k..]` means the coefficient [eps^p l^k] is needed. dim = integration dimension after the translation reduction. '
  '`exact` = known exactly in `out/two_kink_exact.json`.\n')
w('| raw atom | kinks | E? | dim | tight pmin | needed (tight) [eps^p : l^k] | safe additions | used by |\n|---|---|---|---|---|---|---|---|')
for a, r in D['raw_atoms'].items():
    win = '; '.join(f"{p}:{','.join(map(str, ks))}" for p, ks in r['needed_log_orders_by_power_minimal'].items())
    add = '; '.join(f"{p}:{','.join(map(str, ks))}" for p, ks in r['needed_log_orders_by_power_safe'].items()
                    if p not in r['needed_log_orders_by_power_minimal'] or ks != r['needed_log_orders_by_power_minimal'][p])
    w(f"| `{a}` | {r['kinks']} | {'E' if r['endpoint_source'] else ''} | {r['integration_dimension_after_translation']} | "
      f"{r['tight_leading_eps_power']} | {win} | {add} | {','.join(r['used_by_inputs'])}{' (exact)' if r['exact_expansion_available'] else ''} |")
w('\nIntegrand of every atom: `spec_definitions.json` -> `DEFINITIONS.raw_atoms.<atom>.integrand_at_v1_delta0`.\n')
w('Hardest pieces: ' + '; '.join(R['hardest']) + '.\n')

w('## 7. Validation targets (archive-free)\n')
w('Provenance tags: ' + '; '.join(f'**{k}** = {v}' for k, v in V['provenance_tags'].items()) + '.\n')
w('Symbols: ' + ', '.join(f'{k} = {v}' for k, v in V['symbols'].items()) + '.\n')
w('| id | series | eps^p | l^k | exact | value | provenance | source |\n|---|---|---|---|---|---|---|---|')
for t in V['targets']:
    w(f"| {t['id']} | `{t['series']}` | {'' if t['eps_power'] is None else t['eps_power']} | {'' if t['log_power'] is None else t['log_power']} "
      f"| `{t['exact'][:70]}` | {t['value'][:24]} | {t['provenance']} | {t['source'][:80]} |")
w('\n**Exact two-kink raw atoms** (`out/two_kink_exact.json`, derived-here-exact): every Z2_* and Q2_* atom, full eps/log expansion, '
  'exact rationals. They may be used directly as inputs (`assemble_from_raw.py --fill-two-kink-exact`).\n')
w('**Independent input values** (project-internal, not exact):\n')
for r in V['independent_input_values']:
    w(f"* {r['quantity']} = {r['value']} (abs. accuracy {r['abs_accuracy']}; {r['source']})")
w('\n**Finite-cutoff cross-checks.** ' + V['finite_cutoff']['definition'] + ' ' + V['finite_cutoff']['how_to_use'] + '\n')
w('| moment | eps | value | provenance |\n|---|---|---|---|')
for f in V['finite_cutoff']['independent_values']:
    w(f"| `{f['moment']}` | {f['eps']} | {f['value']} | {f['provenance']} |")
w('\nCross-check quantities (no archive-free value yet; compute by two independent routes): ' +
  ', '.join(f"`{q['moment']}`({q['eps']})" for q in V['finite_cutoff']['cross_check_quantities']) + '.\n')
w('Archive-derived predictions (sealed, comparison step only): ' + '; '.join(V['archive_derived_targets_sealed']) + '.\n')

w('## 8. Archive-free checks performed on this spec\n')
c = s['SPEC_CHECKS_ARCHIVE_FREE']
w(f"* {c['normalization_from_generating_functions']}")
w(f"* algebra: {c['algebra']}")
w(f"* closed-form consistency: {c['closed_form_consistency']}")
w(f"* two-kink exact table: {c['two_kink_exact']}")
w(f"* validation internals: {c['validation_internal']}")
for k, v in c['reviewer_archive_free_checks'].items():
    w(f'* reviewer, {k}: {v}')
w('\nThe archive comparisons (definitions reproduce the 25 archived inputs; the assembler on archived raw coefficients; targets '
  'vs archived series; tight-bound evidence) are in `comparison/archive_comparison.json` and `comparison/comparison_report.json`.\n')

w('## 9. Ambiguities and discrepancies\n')
for a in s['AMBIGUITIES_AND_DISCREPANCIES']:
    w(f"* **{a['id']}**: {a['issue']} *Resolution:* {a['resolution']}.")
w('')
if 'C8_EXTENSION' in s:
    X = s['C8_EXTENSION']
    XD = X['DEFINITIONS']; XR = X['RAW_MOMENT_REQUIREMENTS']; XV = X['VALIDATION_TARGETS']; XC = X['SPEC_CHECKS_ARCHIVE_FREE']
    w(f"## 10. C8 extension ({X['meta']['date']}): the ten new inputs of C8 = 8 T4\n")
    w(X['meta']['archive_free'] + '\n')
    w('Sources: ' + X['meta']['sources'] + '\n')
    w('### 10.1 Claims and assembly\n')
    for k, v in X['CLAIMS_UNDER_TEST'].items():
        if k != 'remark':
            w(f'* **{k}**: {v}')
    w('\n' + X['CLAIMS_UNDER_TEST']['remark'] + '\n')
    w('```')
    w('C8 = 8 T4 = B_old + ' + XD['assembly']['new_part'])
    w(f"B_old ({XD['assembly']['B_old_C8_n_terms']} terms, equal to the note appendix) = " + XD['assembly']['B_old_C8'])
    w('```\n')
    w('### 10.2 Definitions\n')
    w('| input | definition | C8 coefficient | terms | max kinks | uses lambda6 | normalized atoms |\n|---|---|---|---|---|---|---|')
    for nm, d in XD['new_inputs'].items():
        w(f"| {nm} | {d['definition']} | {d['C8_coefficient']} | {d['n_terms']} | {d['max_kinks']} | {d['depends_on_lambda6']} | "
          f"{len(d['normalized_atoms'])} |")
    w('\nW = ' + XD['new_inputs']['W']['expansion_in_normalized_atoms'] + ' ; full expansions of all 35 inputs: ' + XD['all_35_inputs_file'] + '.\n')
    w('Recurrence through ninth order:\n')
    w('```')
    for k, v in XD['recurrence_9th_order'].items():
        w(f'{k:8s} = {v}')
    w('```\n')
    w('Normalized responses (E differentiates every factor, EA1 = -2/(1+delta)):\n')
    w('```')
    for k, v in XD['normalized_responses'].items():
        w(f'{k:4s} = {v}')
    w('```\n')
    w('New derivative insertions (full derivatives; S_j = sum_{i<k} q_i q_k log^j(X_k - X_i)): ' +
      '; '.join(f'**{k}**: `{v}`' for k, v in XD['derivative_insertions (multiply W_n at (1,0); new tags)'].items()) + '.\n')
    w('E pieces: ' + XD['E derivative pieces (reflected)'] + '\n')
    w('### 10.3 Raw requirements\n')
    w(XR['summary'] + '\n')
    w('New raw atoms: ' + ', '.join(XR['counts']['new_atoms']) + '.\n')
    w('| raw atom | kinks | E? | tight pmin | needed (tight) [eps^p : l^k] | safe additions | new | used by |\n|---|---|---|---|---|---|---|---|')
    for a, r in XD['raw_atoms'].items():
        tt = r['needed_log_orders_by_power_tight']; ss = r['needed_log_orders_by_power_safe']
        add_ = {p: [k for k in ks if k not in tt.get(p, [])] for p, ks in ss.items()}
        add_ = {p: ks for p, ks in add_.items() if ks}
        fm = lambda dd: ' '.join(f'{p}:{ks}' for p, ks in dd.items())
        w(f"| {a} | {r['kinks']} | {'E' if r['endpoint_source'] else ''} | {r['tight_leading_eps_power']} | {fm(tt)} | {fm(add_)} | "
          f"{'NEW' if r['new_atom_for_C8'] else ''} | {', '.join(x for x in r['used_by_inputs'] if x in XD['new_inputs'])} |")
    w('\nBelow the tight bound (must vanish): ' + ', '.join(XR['safe_minus_tight']['below_tight_bound_must_vanish']) +
      '. Genuine positive-power extras: ' + ', '.join(XR['safe_minus_tight']['genuine_positive_power_extras']) + '.\n')
    w('Precision budget: ' + XR['precision_budget']['statement'] + ' (`' + XR['precision_budget']['source'] + '`).\n')
    w('Hardest: ' + '; '.join(XR['hardest']) + '.\n')
    w('### 10.4 Validation targets (archive-free)\n')
    w('| id | series | eps^p | l^k | exact | value | provenance |\n|---|---|---|---|---|---|---|')
    for t_ in XV['targets']:
        w(f"| {t_['id']} | {t_['series']} | {t_['eps_power']} | {t_['log_power']} | `{t_['exact']}` | {str(t_.get('value'))[:24]} | "
          f"{t_['provenance']} |")
    w('\nIndependent values: ' + '; '.join(f"{x['id']} = {x['value'][:28]}" for x in XV['independent_values'][:1]) +
      ' (and the full eps^0 log polynomials of C3_ddd, A3_ddd in out/C8/validation_targets_C8.json).\n')
    for k in ('structural_zeros', 'data_dependent_RG'):
        w(f'* **{k}**: `' + json.dumps(XV[k])[:900] + '`')
    w('* **finite-cutoff cross-check quantities**: ' + ', '.join(f"{q['moment']}({q['eps']})" for q in XV['finite_cutoff_cross_check_quantities']['quantities']))
    w('* **sealed (comparison step only)**: ' + '; '.join(XV['archive_derived_targets_sealed']) + '\n')
    w('### 10.5 Checks performed (archive-free)\n')
    for k, v in XC.items():
        w(f'* **{k}**: `' + json.dumps(v)[:700] + '`')
    if 'ASSEMBLER' in X:
        w('\n### 10.6 Reference assembler\n')
        for k, v in X['ASSEMBLER'].items():
            w(f'* **{k}**: {v}')
    w('\n### 10.7 Extrapolations, ambiguities\n')
    for e in X['EXTRAPOLATIONS']:
        w(f"* **{e['id']}**: {e['statement']}. {e['status_C8']} Support: " + ' / '.join(e['support']) + '.')
    for a in X['AMBIGUITIES_AND_DISCREPANCIES']:
        w(f"* **{a['id']}**: {a['issue']} *Resolution:* {a['resolution']}.")
    w('')
(SPEC / 'spec.md').write_text('\n'.join(L) + '\n')
print('spec.md', len(L), 'lines')
