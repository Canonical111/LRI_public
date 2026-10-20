#!/usr/bin/env python3
"""SEALED COMPARISON STEP.  Everything that touches archive numbers, in one place.

Run AFTER the archive-free pipeline (../../scripts/*) and after archive_values.py.  Production
code never imports this script or reads its outputs.  It
  1. compares our symbolic algebra (out/invariants.json) with the archived algebra records
     (trace_symbolic.json, D4_algebra.json) and evaluates C5, C6, D4, C7 from the archived
     25 input values (100 digits) through OUR polynomials;
  2. compares every archive-free validation target (out/validation_targets.json), the exact
     two-kink table (out/two_kink_exact.json), the note closed forms of the old inputs and the
     independent three-kink values with the archived series / archived inputs;
  3. evaluates the ARCHIVE-DERIVED predictions (C7 [l^7],[l^3]; d_delta C5 [l^7],[l^3],[l^2];
     second-tail K4 logs) and checks them against the archived normalized series;
  4. collects the archived finite-cutoff values and compares our scipy/mpmath values;
  5. runs the production assembler (scripts/assemble_from_raw.py) on the archive-derived raw
     coefficients in tight, safe and strict 'both' modes;
  6. checks the tight leading-power bounds against the archived series files;
  7. writes ../archive_comparison.json (the single sealed comparison file) and
     ../comparison_report.json (pass/fail summary).
"""
import json, sys, time
from pathlib import Path
import sympy as s
import mpmath as mp

HERE = Path(__file__).resolve().parent
CMP = HERE.parent                       # spec/comparison
SPEC = CMP.parent                       # spec
OUT = SPEC / 'out'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPEC / 'scripts'))
import archive_values as av             # noqa: E402  (comparison-only evaluator of archived series)
from archive_layout import load_archive_raw   # noqa: E402
import assemble_from_raw as asm         # noqa: E402  (the production assembler, fed archive data here)

COMP = av.COMP
mp.mp.dps = 110
t0 = time.time()
av.load_periods()
print('periods', len(av.PERIODS), 'conflicts', len(av.CONFLICTS), round(time.time() - t0, 1), flush=True)

z2s, z3s, z4s, L2s, L3s, Li2hs, Li4hs = s.symbols('z2 z3 z4 L2 L3 Li2h Li4h')
CONST = {z2s: mp.zeta(2), z3s: mp.zeta(3), z4s: mp.zeta(4), L2s: mp.log(2), L3s: mp.log(3),
         Li2hs: mp.polylog(2, -mp.mpf(1) / 2), Li4hs: mp.polylog(4, mp.mpf(1) / 2)}


def ev_exact(txt):
    ex = s.sympify(txt, locals={str(k): k for k in CONST})
    syms = sorted(ex.free_symbols, key=str)
    if not syms:
        r = s.Rational(ex)
        return mp.mpf(r.p) / r.q
    return s.lambdify(syms, ex, 'mpmath')(*[CONST[x] for x in syms])


def arch_series(stem, kmax=12):
    sp = av.series_path(stem)
    if sp is None:
        return None, None
    vals, bad = av.eval_poly(open(av.LAYOUT[sp]).read(), kmax)
    return vals, str(av.LAYOUT[sp].relative_to(COMP))


def pred_file(name):
    for st in ('C7_completion/engine/', 'LRI_1d_complete/stages/C6_integrals/reproducibility/'):
        if st + name in av.LAYOUT:
            txt = open(av.LAYOUT[st + name]).read().strip()
            v, bad = av.eval_poly(txt, 0)
            return txt, v[0], st + name
    return None, None, None


def nstr(x, n=5):
    return None if x is None else mp.nstr(x, n)


report = {}
ain = json.load(open(CMP / 'archive_inputs.json'))
AIN = {k: mp.mpf(v['value']) for k, v in ain['inputs'].items()}
ADER = {k: mp.mpf(v['value']) for k, v in ain['derived'].items()}
inv = json.load(open(OUT / 'invariants.json'))
names = 'a p A E V alpha beta gamma b G R Phi Psi J Omega c f q L M Q k N P K'.split()
S = {n: s.Symbol(n) for n in names}

# ------------------------------------------------------------------ 1. algebra and invariants vs archive
arch_trace = json.load(open(COMP / 'data/archived/C6_closed_form/proof/trace_symbolic.json'))
arch_D4 = json.load(open(COMP / 'outputs/archived/C7_closed_form_proof/verification/algebra/D4_algebra.json'))
alg = {
    'archive_trace_symbolic_C6_identical': s.expand(s.sympify(arch_trace['C6'], locals=S) - s.sympify(inv['C6_polynomial'], locals=S)) == 0,
    'archive_D4_algebra_D4_identical': s.expand(s.sympify(arch_D4['D4'], locals=S) - s.sympify(inv['D4'], locals=S)) == 0,
    'archive_D4_algebra_old_D4_identical': s.expand(s.sympify(arch_D4['old_D4'], locals=S) - s.sympify(inv['B_old_D4'], locals=S)) == 0,
}


def ev_poly(key):
    ex = s.sympify(inv[key], locals=S)
    syms = sorted(ex.free_symbols, key=str)
    return s.lambdify(syms, ex, 'mpmath')(*[AIN[str(x)] for x in syms])


num = {k: ev_poly(k) for k in ('D2', 'T2', 'D3', 'T3', 'D4', 'B_old_C6', 'B_old_D4')}
num['C3'] = num['D2'] - mp.mpf(1) / 16
num['C5'] = 2 * num['D3'] - num['T2'] / 2 + num['C3']**2 / 4
num['C6'] = 4 * num['T3']
num['C7'] = 4 * num['D4'] - num['T3'] - num['T2']**2 + num['C3'] * num['C5'] / 2
num['C4'] = 2 * num['T2']
claims = asm.claims()                    # closed forms evaluated at the current 110 digits
claims.update({'T3': claims['C6'] / 4, 'D2': claims['C3'] + mp.mpf(1) / 16, 'T2': claims['C4'] / 2})
inv_num = {}
for k, v in num.items():
    r = {'from_archive_inputs': mp.nstr(v, 50)}
    if k in claims:
        r['minus_claim'] = nstr(v - claims[k])
    if k in ADER:
        r['archive_value'] = mp.nstr(ADER[k], 50)
        r['minus_archive_value'] = nstr(v - ADER[k])
    inv_num[k] = r
newC6 = inv['C6_new_coefficients']; newD4 = inv['D4_new_coefficients']
frac = lambda t: mp.mpf(s.Rational(t).p) / s.Rational(t).q
C6_terms = {'B_old': mp.nstr(num['B_old_C6'], 40)}
C6_terms.update({f'{cf}*{x}': mp.nstr(frac(cf) * AIN[x], 40) for x, cf in newC6.items()})
D4_terms = {'B_old_D4': mp.nstr(num['B_old_D4'], 40)}
D4_terms.update({f'{cf}*{x}': mp.nstr(frac(cf) * AIN[x], 40) for x, cf in newD4.items()})
report['algebra_vs_archive_records'] = all(alg.values())
report['archive_inputs_reproduce_claims'] = all(abs(mp.mpf(inv_num[k]['minus_claim'])) < mp.mpf(10)**-80
                                                  for k in ('C3', 'D3', 'C5', 'C6', 'D4', 'C7'))
print('algebra', alg, 'C6-claim', inv_num['C6']['minus_claim'], 'D4-claim', inv_num['D4']['minus_claim'], flush=True)

# ------------------------------------------------------------------ 2. archive-free targets vs archive
vt = json.load(open(OUT / 'validation_targets.json'))
SERIES = {'C3[v0d0]': 'norm_C3_0_0', 'K4[v0d0]': 'norm_K4_0_0', 'C5[v0d0]': 'norm_C5_0_0', 'C3[v1d0]': 'norm_C3_1_0',
          'C3[v0d1]': 'norm_C3_0_1', 'C7[v0d0]': 'norm_C7_0_0', 'C5[v0d1]': 'norm_C5_0_1', 'C7[v1d0]': 'norm_C7_1_0',
          'K8[v0d0]': 'norm_K8_0_0'}
tcmp = []
cache = {}
for t in vt['targets']:
    target = ev_exact(t['exact'])
    rec = {'id': t['id'], 'provenance': t['provenance']}
    if t['kind'] in ('raw', 'normalized'):
        if t['series'] == 'A3_dd/2':
            stem, fac = 'A3_dd_p0', mp.mpf(1) / 2
        elif t['kind'] == 'raw':
            stem, fac = f"{t['series']}_p{t['eps_power']}", 1
        else:
            stem, fac = SERIES[t['series']], 1
        if stem not in cache:
            cache[stem] = arch_series(stem)
        vals, f = cache[stem]
        if vals is None or vals[t['log_power']] is None:
            rec['archive'] = None
        else:
            rec['archive_file'] = f
            rec['archive_minus_target'] = nstr(vals[t['log_power']] * fac - target)
    elif t['kind'] == 'input':
        rec['archive_minus_target'] = nstr(AIN[t['series']] - target)
    elif t['kind'] == 'input_combination':
        rec['archive_minus_target'] = nstr(2 * AIN['G'] + AIN['k'] + 2 * AIN['q'] - 2 * AIN['b'] - AIN['f'] - target)
    elif t['kind'] == 'invariant':
        rec['archive_inputs_minus_target'] = nstr(num[t['series']] - target)
    else:
        rec['archive'] = 'n/a'
    tcmp.append(rec)
def diffs(rec):
    return [abs(mp.mpf(rec[k])) for k in ('archive_minus_target', 'archive_inputs_minus_target') if rec.get(k) is not None]
bad_t = [r for r in tcmp if any(d > mp.mpf(10)**-40 for d in diffs(r))]
report['archive_free_targets_vs_archive'] = {'n': len(tcmp), 'n_compared': sum(1 for r in tcmp if diffs(r)),
                                             'mismatches_above_1e-40': [r['id'] for r in bad_t]}
print('targets vs archive', report['archive_free_targets_vs_archive'], flush=True)

two = json.load(open(OUT / 'two_kink_exact.json'))['atoms']
two_cmp, two_worst = {}, mp.mpf(0)
for atom, ps in two.items():
    for p in sorted({int(p) for p in ps} | set(range(-2, 4))):
        vals, f = arch_series(f'{atom}_p{p}')
        if vals is None:
            continue
        ex = {int(k): s.Rational(v) for k, v in ps.get(str(p), {}).items()}
        d = max(abs(vals[k] - (mp.mpf(ex[k].p) / ex[k].q if k in ex else 0)) for k in range(len(vals)) if vals[k] is not None)
        two_cmp[f'{atom}_p{p}'] = nstr(d)
        two_worst = max(two_worst, d)
report['two_kink_exact_vs_archive_series'] = {'files_compared': len(two_cmp), 'max_abs_diff': nstr(two_worst)}
print('two-kink exact vs archive', report['two_kink_exact_vs_archive_series'], flush=True)

indep = {r['id'].split('.')[1]: nstr(mp.mpf(r['value']) - AIN[r['id'].split('.')[1]]) for r in vt['independent_input_values']}
report['independent_three_kink_values_vs_archive'] = indep

# ------------------------------------------------------------------ 3. archive-derived predictions
preds = []
def add_pred(series_name, stem, k, fname, fac=1, note_value=None):
    txt, v, src = pred_file(fname)
    if txt is None:
        return
    vals, f = arch_series(stem)
    rec = {'series': series_name, 'log_power': k, 'provenance': 'archive-derived prediction',
           'exact': txt if len(txt) < 300 else f'<period expression, {len(txt)} chars>', 'archive_prediction_file': src,
           'value': mp.nstr(v, 50), 'archive_series_file': f,
           'archive_series_minus_prediction': nstr(vals[k] * fac - v) if vals and vals[k] is not None else None}
    if note_value is not None:
        rec['note_minus_prediction'] = nstr(note_value - v)
    preds.append(rec)
for k in (7, 3):
    add_pred('C7[v0d0]', 'norm_C7_0_0', k, f'C7_log{k}_predicted.expr')
for k in (7, 3, 2):
    add_pred('C5[v0d1]', 'norm_C5_0_1', k, f'C5_tail_log{k}_predicted.expr')
for k in range(2, 9):
    add_pred('K4[v0d2]/2 (Taylor [delta^2] of K4)', 'norm_K4_0_2', k, f'K4_dd_log{k}_predicted.expr', fac=mp.mpf(1) / 2)
# the note's own higher-log statements vs the archived prediction files (provenance cross-check)
note_vs_pred = {}
for t in vt['targets']:
    fmap = {'C7[v0d0]': 'C7_log{}_predicted.expr', 'C5[v0d1]': 'C5_tail_log{}_predicted.expr', 'C7[v1d0]': 'A7v_log{}_predicted.expr'}
    if t['series'] in fmap:
        txt, v, src = pred_file(fmap[t['series']].format(t['log_power']))
        if txt is not None:
            note_vs_pred[t['id']] = nstr(ev_exact(t['exact']) - v)
bad_p = [p['series'] + f" l^{p['log_power']}" for p in preds
         if p['archive_series_minus_prediction'] is not None and abs(mp.mpf(p['archive_series_minus_prediction'])) > mp.mpf(10)**-40]
report['archive_derived_predictions_vs_archive_series'] = {'n': len(preds), 'mismatches_above_1e-40': bad_p}
report['note_higher_logs_vs_archive_prediction_files'] = {'n': len(note_vs_pred),
                                                          'max_abs_diff': nstr(max([abs(mp.mpf(x)) for x in note_vs_pred.values()] or [0]))}
print('predictions', report['archive_derived_predictions_vs_archive_series'], flush=True)

# ------------------------------------------------------------------ 4. archived finite-cutoff values
FINITE = [
    {'moment': 'A7_base', 'eps': '1/8', 'value': '0.03557288770735261', 'source': 'documentation C6_thermal_note.tex table (hyperlog finite-cutoff); Sobol 0.03557231(56)'},
    {'moment': 'Q6_v', 'eps': '1/8', 'value': '3.6134912002672482576039966814020336266942921298659834827574812757',
     'source': 'data/archived/LRI_1d_complete/stages/C6_integrals/reproducibility/finite_cutoff_hyperlog.json; Sobol 3.613220(335)'},
    {'moment': 'EA5_base', 'eps': '1/8', 'value': '-10.134809249361283280346536688059201955569400580632764915376388177',
     'source': 'finite_cutoff_hyperlog.json; Sobol -10.134935(132); the Sobol run used the unreflected U^odd insertion'},
    {'moment': 'A3_d', 'eps': '1/8', 'value': '-18.062881247394966383679902610945412786843842413429236470425646585',
     'source': 'finite_tail_hyperlog.json key "3"; Sobol -18.0628784(43)'},
    {'moment': 'Z4_d', 'eps': '1/8', 'value': '-36.586656683782873722752539446030932507609997413130182230491285777',
     'source': 'finite_tail_hyperlog.json key "4" (MC integrand W*S2 without dipole -> Z4_d); Sobol -36.58597(42)'},
    {'moment': 'A5_d', 'eps': '1/8', 'value': '-23.79522821848594149392243319862577689626572680430762663723731021',
     'source': 'finite_tail_hyperlog.json key "5"; Sobol -23.795293(91)'},
    {'moment': 'A7_v', 'eps': '1/10', 'value': '24.3373481107902877688066785264334847763066011713500353463703984913212273536',
     'source': 'data/archived/C7_completion/engine/A7_v_finite_raw_check_90.json; Gauss-Jacobi order 22: 24.337348110790277'},
    {'moment': 'Q8_base', 'eps': '1/10', 'value': '0.087189617053451302784774203412279155255810536909627503184649922102',
     'source': 'data/archived/C7_completion/engine/Q8_base_finite_raw_check_80.json; Gauss order 16: 0.08718961705345105'},
    {'moment': 'Q4_dd', 'eps': '1/10', 'value': '324.48697803842399840237498804759297331057987786228153724802549913',
     'source': 'data/archived/C7_completion/engine/Q4_dd_finite_raw_check_80.json; Gauss order 28: 324.4869780384237'},
]
sfc = json.load(open(OUT / 'sanity_finite_cutoff.json'))['values']
fin_cmp = {}
for f in FINITE:
    if f['moment'] in sfc and f['eps'] == '1/8':
        fin_cmp[f['moment']] = nstr(mp.mpf(sfc[f['moment']]) - mp.mpf(f['value']))
report['scipy_finite_cutoff_vs_archive'] = fin_cmp

# ------------------------------------------------------------------ 5. production assembler on archive raw
mp.mp.dps = 60
raw = load_archive_raw()
asm_res = {}
for mode in ('tight', 'safe', 'both'):
    res, ok = asm.run(json.loads(json.dumps(raw)), mode, 58, '1e-40', '1e-40')
    asm_res[mode] = {'minus_claim': res['minus_claim'], 'all_checks_pass': ok,
                     'checks': {k: v for k, v in res['checks'].items() if k != 'genuine_safe_extras_looked_up_on_demand'}}
    if mode == 'both':
        asm_res['both']['inputs'] = res['inputs']
        asm_res['both']['invariants'] = res['invariants']
        inp_dev = max(abs(mp.mpf(res['inputs'][k]) - AIN[k]) for k in names)
        asm_res['both']['inputs_max_abs_minus_archive_inputs'] = nstr(inp_dev)
res_fill, _ = asm.run(json.loads(json.dumps(raw)), 'tight', 58, '1e-40', '1e-40', fill_exact=True)
asm_res['two_kink_archive_minus_exact_max'] = res_fill['checks']['two_kink_supplied_max_dev_from_exact']
asm_res['two_kink_filled_from_exact_absent_in_archive'] = res_fill['checks']['two_kink_filled_from_exact']
report['assembler_on_archive_raw'] = {m: {'C6': asm_res[m]['minus_claim']['C6'], 'D4': asm_res[m]['minus_claim']['D4'],
                                          'C7': asm_res[m]['minus_claim']['C7'], 'checks_pass': asm_res[m]['all_checks_pass']}
                                      for m in ('tight', 'safe', 'both')}
print('assembler', report['assembler_on_archive_raw'], flush=True)
mp.mp.dps = 110

# ------------------------------------------------------------------ 6. tight leading-power bounds vs archived series
req = json.load(open(OUT / 'raw_requirements.json'))['total_tight']
tb = {}
for atom in req:
    p = asm.pmin_tight(atom) - 1
    for pp in (p, p - 1):
        vals, f = arch_series(f'{atom}_p{pp}')
        if vals is not None:
            tb[f'{atom}_p{pp}'] = nstr(max(abs(x) for x in vals if x is not None))
report['tight_bound_evidence'] = {'archived_series_below_tight_bound': len(tb),
                                  'max_abs_coefficient': nstr(max([mp.mpf(x) for x in tb.values()] or [0]))}
print('tight bounds', report['tight_bound_evidence'], flush=True)

# ------------------------------------------------------------------ spec self-test summary (from archive_values.py)
st = json.load(open(CMP / 'spec_selftest.json'))
st_in = max(abs(mp.mpf(v['difference'])) for v in st['inputs_from_definitions'].values() if v['difference'])
st_norm = max(abs(mp.mpf(v['difference']) / mp.mpf(v['archive_normalized'])) for v in st['normalized_from_raw_windows'].values()
              if v['difference'] and mp.mpf(v['archive_normalized']) != 0)
report['spec_selftest'] = {'inputs_from_definitions_on_archive_normalized_max_abs_diff': nstr(st_in),
                           'normalized_atoms_from_archive_raw_tight_windows_max_rel_diff': nstr(st_norm)}

# ------------------------------------------------------------------ assemble the sealed file
araw = json.load(open(CMP / 'archive_raw_coefficients.json'))
anorm = json.load(open(CMP / 'archive_normalized_atoms.json'))
needed = {}
for atom, ps in araw['raw'].items():
    for p, rec in ps.items():
        if rec['needed']:
            needed.setdefault(atom, {})[p] = {'needed_log_orders': rec['needed_log_orders'],
                                              'coefficients_by_log_power': rec['coefficients_by_log_power'],
                                              'archive_file': rec['archive_file'], 'original_archive_path': rec['original_path']}
sealed = {
    'meta': {
        'SEALED': 'ARCHIVE-DERIVED NUMBERS. Comparison only, after our own values exist. Production code (spec/scripts, '
                  'framework, engine, direct production paths) must never read this file.',
        'created': time.strftime('%Y-%m-%d'),
        'written_by': 'spec/comparison/scripts/compare_with_archive.py (and archive_values.py for the extracts)',
        'compendium': str(COMP) + ' (read-only)',
        'readers_allowed': ['spec/comparison/scripts/*', 'final blind comparison step of each team',
                            'review/sensitivities.py and review/cancellation_factors.py (sizing aids only)'],
    },
    'archive_inputs': ain['inputs'],
    'archive_derived_values': ain['derived'],
    'note_quoted_decimals_archive_origin': {
        'remark': 'decimals printed in the note that originate from archived evaluations (not closed forms)',
        'G': '32.7634092768376557983124741174', 'q': '-103.5603579270427462132101236545', 'k': '104.6723927432126373310860847487',
        'V': '-19.518741011574465808', 'R': '-1.148356985726247710', 'J': '32.280324973629037003', 'L': '-7.677303759056569914',
        'M': '13.315217322864044765', 'N': '210.030599248618268410', 'Omega': '-234.4214552889636875265144452523',
        'Q': '-107.0654814955476394045726813165', 'B_old_C6': '-48.0003600840977427059', 'B_old_D4_noted_in': 'not printed in note'},
    'C6_terms_from_archive_inputs': C6_terms,
    'D4_terms_from_archive_inputs': D4_terms,
    'raw_coefficients_needed': needed,
    'raw_coefficients_all_archived_powers_file': 'comparison/archive_raw_coefficients.json',
    'normalized_atoms': anorm['atoms'],
    'period_tables_used': 'union of archived *periods*.json (C7_second dps115, C6 run2 dps100, F1c/F2/F3/F4/P6 100-digit tables, ...); '
                          f'{len(av.PERIODS)} words, {len(av.CONFLICTS)} conflicts; missing periods only in two unneeded coefficients '
                          '(A3_vdd [eps^0 l^0], Q8_base [eps^0 l^0])',
    'archive_derived_validation_predictions': preds,
    'archive_finite_cutoff_values': FINITE,
    'superseded_records': [
        {'id': 'superseded-C7-records', 'issue': 'data/archived/LRI_1d_complete/data/C7_reported_inputs.json holds transcript-only '
         'alpha..P and an inconsistent partial "C7 = 21.7338460355083 - Omega/8"; its Q = -107.065542796939575 is WRONG (final '
         '-107.06548149554763940457...). Correct: C7 = 21.766306701807647890369630323347 - Omega/8.',
         'resolution': 'use C7_completion/engine/final_evaluation_C7_second.json values only'},
        {'id': 'a_check_corrupted', 'issue': 'On this Mac data/archived/C6_closed_form/input_expressions/a_check_symbolic.expr collides '
         'with A_check_symbolic.expr (case-insensitive FS); a = -4 zeta(2) and the numeric archive value agree to 5e-85.'}],
    'comparisons': {
        'algebra_vs_archive_records': alg,
        'invariants_from_archive_inputs': inv_num,
        'archive_free_targets_vs_archive': tcmp,
        'two_kink_exact_vs_archive_series': two_cmp,
        'independent_three_kink_values_minus_archive': indep,
        'note_higher_logs_minus_archive_prediction_files': note_vs_pred,
        'scipy_finite_cutoff_minus_archive': fin_cmp,
        'assembler_on_archive_raw': asm_res,
        'tight_bound_evidence_archived_series_below_bound_max_abs': tb,
        'spec_selftest_summary': report['spec_selftest'],
    },
}
json.dump(sealed, open(CMP / 'archive_comparison.json', 'w'), indent=1)
ok = (report['algebra_vs_archive_records'] and report['archive_inputs_reproduce_claims']
      and not report['archive_free_targets_vs_archive']['mismatches_above_1e-40']
      and mp.mpf(report['two_kink_exact_vs_archive_series']['max_abs_diff']) < mp.mpf(10)**-40
      and not report['archive_derived_predictions_vs_archive_series']['mismatches_above_1e-40']
      and all(abs(mp.mpf(x)) < mp.mpf(10)**-25 for x in indep.values())
      and all(abs(mp.mpf(x)) < mp.mpf(10)**-8 for x in fin_cmp.values())
      and all(v['checks_pass'] and abs(mp.mpf(v['C6'])) < mp.mpf(10)**-50 and abs(mp.mpf(v['D4'])) < mp.mpf(10)**-50
              for v in report['assembler_on_archive_raw'].values())
      and mp.mpf(report['tight_bound_evidence']['max_abs_coefficient']) == 0)
report['ALL_PASS'] = bool(ok)
json.dump(report, open(CMP / 'comparison_report.json', 'w'), indent=1)
import hashlib
(CMP / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256((CMP / n).read_bytes()).hexdigest()}  comparison/{n}\n'
                                        for n in ('archive_comparison.json', 'archive_inputs.json', 'archive_raw_coefficients.json',
                                                  'archive_normalized_atoms.json', 'spec_selftest.json', 'comparison_report.json')))
print('ALL_PASS', ok, 'time', round(time.time() - t0, 1))
