#!/usr/bin/env python3
"""SEALED C8 COMPARISON STEP (comparison only; production code never reads this directory).

Order of operations (enforced):
  1. our_results_sha256: hash every archive-free C8 result of the spec (spec_definitions.json incl. C8_EXTENSION, spec.md,
     out/C8/*.json, review/three_kink_C8.json, review/rg_logs_vs_engine_phase2.json, review/crosscheck_framework_C8.json)
     and write ../sealing_record.json BEFORE any archive number is read by this script.  An existing record is kept; a
     changed result is appended as a new entry (history), never overwritten.
  2. archive values (comparison only): the C8-era numbers of the note (Secs. 1, 14-18, typed in below from the TeX, with
     line numbers) and of the archive's numerical JSON records (100 digits; *.expr, *_negative.json, *_audit.json and the
     raw Laurent tables are NOT read) -> ../archive_C8_values.json.
  3. comparisons through OUR algebra (no archive code): B_old polynomial at the archived 25 inputs, B_done, C8, C_fixed,
     the note's F1-F4 identities, the rational projections (pi_0 C8 = 88 through our assembly coefficients), the candidate
     closed form (our evaluation), our independent W; sizing of the cancellations -> ../comparison_C8_report.json.
  4. ../SHA256SUMS.
"""
import datetime, hashlib, json, sys
from pathlib import Path
import sympy as s
import mpmath as mp

HERE = Path(__file__).resolve().parent
CMP = HERE.parent
SPEC = CMP.parent
COMP = Path('/Users/zheng/Documents/Agent_LRI/LRI_SRI_research_compendium')
mp.mp.dps = 110


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------- 1. sealing record
spec_def = json.load(open(SPEC / 'spec_definitions.json'))
if 'C8_EXTENSION' not in spec_def:
    sys.exit('spec_definitions.json has no C8_EXTENSION: run the archive-free pipeline first')
ours = {'spec_definitions.json': sha(SPEC / 'spec_definitions.json'), 'spec.md': sha(SPEC / 'spec.md')}
ours.update({f'out/C8/{p.name}': sha(p) for p in sorted((SPEC / 'out' / 'C8').glob('*.json'))})
for n in ('three_kink_C8', 'rg_logs_vs_engine_phase2', 'crosscheck_framework_C8', 'crosscheck_framework_C8_assembly'):
    p = SPEC / 'review' / f'{n}.json'
    if p.exists():
        ours[f'review/{n}.json'] = sha(p)
rec_path = CMP / 'sealing_record.json'
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
rec = json.load(open(rec_path)) if rec_path.exists() else {
    'note': 'SHA-256 of the archive-free C8 results, written by seal_and_compare_C8.py BEFORE it reads any archive number. '
            'Entries are appended when a result changes; nothing is overwritten.', 'history': []}
if not rec['history'] or rec['history'][-1]['sha256'] != ours:
    rec['history'].append({'written': now, 'sha256': ours})
json.dump(rec, open(rec_path, 'w'), indent=1)
print('sealing record:', len(rec['history']), 'entr(y/ies); latest', rec['history'][-1]['written'], flush=True)

# ----------------------------------------------------------------------------------------------- 2. archive values
A = COMP / 'data' / 'archived'
src = {
    'six': A / 'C8_full_numerical_completion' / 'inherited' / 'six_new_inputs.json',
    'U': A / 'C8_full_numerical_completion' / 'inherited' / 'U_record.json',
    'F3': A / 'C8_full_numerical_completion' / 'data' / 'F3_final_100.json',
    'F4': A / 'C8_full_numerical_completion' / 'data' / 'F4_data_100.json',
    'full': A / 'C8_full_numerical_completion' / 'result.json',
    'P6': A / 'C8_P6_exact_sources' / 'P6_full' / 'P6_eval100.json',
    'cand': A / 'C8_zeta_candidate' / 'result.json',
    'F1c': A / 'F1c_completion' / 'result.json',
}
R = {k: json.load(open(p)) for k, p in src.items()}
V = {}
def put(name, value, source, note=None):
    V[name] = {'value': str(value), 'source': source} | ({'note': note} if note else {})

rel = lambda k: str(src[k].relative_to(COMP))
for nm in ('W', 'S', 'L3', 'M21', 'M12', 'N2'):
    put(nm, R['six']['coefficients'][nm], rel('six'), 'inherited record, single run, dps 100, no input hash (note l.1240-1252)')
put('U', R['U']['values']['U'], rel('U'))
put('A7_d_1', R['U']['values']['A7_tail_log'], rel('U'), '[eps^0 l^1] d_delta A7 (note l.1349)')
put('D_known', R['U']['values']['F2_known_with_endpoint'], rel('U'), 'U - A7_d_1 (note l.1350)')
for k in ('EA5_tail_finite', 'Z6_tail_log', 'EZ4_tail_finite', 'F2_lower_shift'):
    put(k, R['U']['values'][k], rel('U'))
put('P8', R['F3']['values']['P8'], rel('F3'))
put('Kv', R['F3']['values']['Kv'], rel('F3'))
put('F3_known = 16 X_vv - 8 X_E + S3', R['F3']['values']['F3_known'], rel('F3'))
put('F1_known (Ndelta + 4 P6)', R['F3']['values']['F1_known'], rel('F3'))
for k, v in R['F3']['values'].items():
    if k.startswith('beta_'):
        put(f'old_input_{k[5:]}', v, rel('F3'), 'the 25 old inputs as used by the archive C8 assembly')
put('A9_1', R['F4']['values']['A9_log'], rel('F4'))
put('Z8_1', R['F4']['values']['Z8_log'], rel('F4'))
put('(EA7)_0', R['F4']['values']['EA7_finite'], rel('F4'))
put('(EZ6)_0', R['F4']['values']['EZ6_finite'], rel('F4'))
put('D9_lower', R['F4']['values']['J9_lower_shift'], rel('F4'))
put('J9', R['F4']['values']['J9'], rel('F4'))
put('B_old', R['F4']['values']['B_old_full'], rel('F4'))
put('B_done', R['full']['B_done'], rel('full'))
put('C_fixed', R['cand']['Cfixed_inherited_numeric_assembly'], rel('cand'))
put('P6', R['P6']['values']['P6'], rel('P6'), 'eq:P6full, 100-digit evaluation')
put('C8', R['cand']['C8_assembled_without_candidate'], rel('cand'), 'numerical, not interval-certified')
put('C8_candidate_value_archive', R['cand']['candidate_value'], rel('cand'))
put('C8_minus_candidate_archive', R['cand']['candidate_difference'], rel('cand'))
put('D_ct', R['F1c']['Dct_numerical'], rel('F1c'))
put('D_norm + D_ct', R['F1c']['Dnorm_plus_Dct_numerical'], rel('F1c'))
put('Ndelta_known_part', R['F1c']['Nd_known_part_numerical'], rel('F1c'))
for i, c in enumerate(R['full']['cases']):
    put(f'superseded_P6_run_{i}', c['P6'], rel('full'), 'earlier F1a quadrature (superseded by eq:P6full)')
mp_ = lambda k: mp.mpf(V[k]['value'])
V['Ndelta'] = {'value': mp.nstr(mp_('F1_known (Ndelta + 4 P6)') - 4 * mp_('P6'), 95),
               'source': 'derived here from the archive records: F1_known - 4 P6 (eq:NdP6)'}
# note-only values (typed in from the TeX; line numbers)
NOTE = {
    'X_vv (note l.1366)': '8059.736102186616125752727901120985',
    'X_E (note l.1367)': '-88077.172363552137052197675538291236',
    'S3 (note l.1363)': '24144.925877712789692098427372845263',
    'D_norm (note l.1311)': '-2670.168541372163931149878165554559',
    'D_norm products (note l.1309)': ['-1300.763962200486633', '-108', '-1261.404579171677298'],
    'D_norm zero-power-only (note l.1312)': '-1497.3871181439',
    '(Q4_vvd)_0 (note l.1323)': '17290.15809730659828787662714975844',
    '(EE Q4_vd)_0 (note l.1324)': '34463.59564045596175027158175593235',
    'Q6_vv(eps=1/10) full moment (note l.1377)': '425.5449632473382428',
    'P6 early angular estimate (note l.1270)': '1261.9448',
    'C8_num (note l.89)': '247.3812048049935484073550747661',
    'B_old (note l.1167)': '-861.6635672354797792014971909923',
    'B_done (note l.1410)': '563.404066124777663118309147204616',
    'C_fixed (note l.1418)': '878.353653726563794093781271241865882423221643308',
    'P6 (note eq:P6full l.1287)': '1261.944897843140491372852392951531767542124984174',
    'U (note l.1351)': '-1296.687960291526491656393773342069',
    'A7_d_1 (note l.1349)': '315459.451152690228448576716538300797',
    'D_known (note l.1350)': '-316756.139112981754940233110311642866',
    'P8 (note l.1368)': '214801.261132598641881962805253618627',
    'Kv (note l.1369)': '-1486.962109278823406127742917363593',
    'J9 (note l.1399)': '-273.724515999324646514077910398647',
    'A9_1 (note l.1393)': '-613817.497451118368344265', 'Z8_1 (note l.1394)': '11059.024476469114411035',
    '(EA7)_0 (note l.1395)': '-14142.938944879185749695', '(EZ6)_0 (note l.1396)': '305.264828822013665772',
    'D9_lower (note l.1397)': '653499.204958990556939720',
    'Ndelta known part (note eq:NdP6 l.1330)': '11218.914021881803142302231182488606',
    'D_ct (note l.1316)': '-134.559964098286854425679630067592',
    'W (note table l.1243)': '-37.708111514952555', 'S (note)': '878.183733747745103', 'L3 (note)': '-0.638692810583406',
    'M21 (note)': '-171.235576565588699', 'M12 (note)': '-422.715057969894520', 'N2 (note)': '189.742012494084223',
}
RATIONAL = {   # rational projections and raw rational scalars of the archive (note Secs. 1, 15, 16, appendix)
    'pi0 C8 (note l.86)': '88', 'pi0 B_old (appendix l.2783)': '1153/6',
    'R6 (note l.1188)': '399343/2', 'R8': '-757993', 'R_tail': '-910891/6', 'R9': '1423087/3',
    'C8^(0) reduction (note l.1192)': '5345/12 - R6/2 - R8/8 + 3 R_tail/4 + R9/4',
    '(d_delta A7)_1^(0)': '-468683/3', '(d_delta Z6)_1^(0)': '-8825/2', '(A9)_1^(0)': '666540', '(Z8)_1^(0)': '23294/3',
    '(EE A7)_0^(0)': '-184413/2',
    'U^(0)': '16534/3', 'J9^(0)': '-10192/3', 'Ndelta^(0)': '-20848', 'Kv^(0)': '77920/3',
    'W^(0)': '168', 'S^(0)': '-1751', 'L3^(0)': '128', 'M21^(0)': '-384', 'M12^(0)': '2720', 'N2^(0)': '3712',
    'T^(0)(delta)': 'delta/2 + 2 delta^2 + 13/2 delta^3 + 11 delta^4',
    'pi0 D_norm': '-8719/2', 'pi0 D_ct': '-190100', 'pi0 P6': '399343/2',
    'Q6_vd singular (c_-2,0, c_-2,1, c_-1,0, c_-1,1)^(0) (note l.1236)': '(-7, -32, 2193, 555)',
    'Q8_v singular (p: c_p0, c_p1)^(0) (note l.1240-1245)': '-3: (2/3, 2); -2: (-104/3, -52/3); -1: (-80255/12, -20429/6)',
}
CLAIMS = {'C8_candidate (note eq:C8-candidate-main)': '88 - 178 z2 + 110 z3 + 113 z4 + 4892 z5 - 2376 z2 z3 - 8630/3 z6 + 1872 z3^2 '
                                                     '- 12168 z7 + 6048 z2 z5 + 1536 z3 z4',
          'leading log (note l.1356, also in the archive-free spec)': '[eps^0 l^8] d_delta A7 = -2362/315, [l^9] = 0'}
json.dump({'note': 'SEALED ARCHIVE NUMBERS, COMPARISON ONLY. Never read by production code (spec/scripts, framework, engine, '
                   'direct, assembly production paths).', 'records_100_digit': V, 'note_quoted_decimals': NOTE,
           'rational_projections_and_raw_rationals': RATIONAL, 'claims': CLAIMS,
           'sources_not_read': '*.expr, *_negative.json, *_audit.json, *.periods.json, P6/P8/U/J9/Kv expression files, raw Laurent '
                               'tables (e.g. P6_N36_kahan_fresh.json coefficient blocks)'},
          open(CMP / 'archive_C8_values.json', 'w'), indent=1)
print('archive values sealed:', len(V), 'records,', len(NOTE), 'note decimals,', len(RATIONAL), 'rationals', flush=True)

# ----------------------------------------------------------------------------------------------- 3. comparisons
inv = spec_def['C8_EXTENSION']['DEFINITIONS']['assembly']
OLD = 'a p A E V alpha beta gamma b G R Phi Psi J Omega c f q L M Q k N P K'.split()
NEWC = {k: s.Rational(v) for k, v in spec_def['C8_EXTENSION']['DEFINITIONS']['new_inputs'].items()
        for v in [v['C8_coefficient']]}
SY = {n: s.Symbol(n) for n in OLD + list(NEWC)}
Bpoly = s.sympify(inv['B_old_C8'], locals=SY)
oldv = {n: mp_(f'old_input_{n}') for n in OLD}
p1 = json.load(open(SPEC / 'comparison' / 'archive_inputs.json'))['inputs']
old_consistency = max(abs(oldv[n] - mp.mpf(p1[n]['value'])) for n in OLD)
f_B = s.lambdify([SY[n] for n in OLD], Bpoly, 'mpmath')
B_ours = f_B(*[oldv[n] for n in OLD])
newv = {n: mp_(n) for n in NEWC}
lin = lambda names: sum(mp.mpf(NEWC[n].p) / NEWC[n].q * newv[n] for n in names)
B_done_ours = B_ours + lin(['W', 'S', 'L3', 'M21', 'M12', 'N2'])
C8_ours = B_ours + lin(list(NEWC))
z = {k: mp.zeta(k) for k in range(2, 8)}
cand = (88 - 178 * z[2] + 110 * z[3] + 113 * z[4] + 4892 * z[5] - 2376 * z[2] * z[3] - mp.mpf(8630) / 3 * z[6] + 1872 * z[3]**2
        - 12168 * z[7] + 6048 * z[2] * z[5] + 1536 * z[3] * z[4])
# pi_0 consistency: our C8 coefficients with the archive rational projections
q = s.Rational
pi0 = {'W': 168, 'S': -1751, 'U': q(16534, 3), 'J9': q(-10192, 3), 'L3': 128, 'M21': -384, 'M12': 2720, 'N2': 3712,
       'Ndelta': -20848, 'Kv': q(77920, 3)}
pi0_C8 = q(1153, 6) + sum(NEWC[n] * pi0[n] for n in NEWC)
pi0_red = q(5345, 12) - q(399343, 2) / 2 - q(-757993, 1) / 8 + q(3, 4) * q(-910891, 6) + q(1423087, 3) / 4
pi0_Nd = q(399343, 2) - q(8719, 2) - 190100
our_W = mp.mpf(json.load(open(SPEC / 'review' / 'three_kink_C8.json'))['inputs']['W']['value'])
budget = json.load(open(SPEC / 'out' / 'C8' / 'budget_C8.json'))['scalars']
size = {}
for lbl, key in [('A9_base [eps^0 l^1]', 'A9_1'), ('Z8_base [eps^0 l^1]', 'Z8_1'), ('EA7_base [eps^0 l^0]', '(EA7)_0'),
                 ('EZ6_base [eps^0 l^0]', '(EZ6)_0'), ('A7_d [eps^0 l^1]', 'A7_d_1'), ('Q8_v [eps^0 l^1]', 'P8')]:
    dx = abs(s.Rational(budget[lbl]['dC8_dx']))
    mag = abs(mp_(key))
    size[lbl] = {'archive_magnitude': mp.nstr(mag, 6), 'abs_dC8_dx': str(dx),
                 'relative_precision_for_1e-4_absolute_in_C8': mp.nstr(mp.mpf(1e-4) / (mp.mpf(dx.p) / dx.q) / mag, 3),
                 'relative_precision_for_1e-4_relative_in_C8': mp.nstr(mp.mpf(1e-4) * abs(C8_ours) / (mp.mpf(dx.p) / dx.q) / mag, 3)}
size['Q6_vd [eps^0 l^1] (P6)'] = {'archive_magnitude': mp.nstr(mp_('P6'), 6), 'abs_dC8_dx': '1/2',
                                  'relative_precision_for_1e-4_absolute_in_C8': mp.nstr(mp.mpf(2e-4) / mp_('P6'), 3)}
cmp = {
    'old_inputs_F3_record_vs_phase1_sealed_inputs_max_abs_diff': mp.nstr(old_consistency, 3),
    'B_old: our polynomial at the archived inputs minus archive B_old': mp.nstr(B_ours - mp_('B_old'), 3),
    'B_done: ours (B_old + 4W + 2S + 3/32 L3 - M21/4 + M12/2 - N2/16) minus archive': mp.nstr(B_done_ours - mp_('B_done'), 3),
    'C8: our assembly at the archived inputs minus archive C8': mp.nstr(C8_ours - mp_('C8'), 3),
    'C_fixed - P6/2 minus archive C8': mp.nstr(mp_('C_fixed') - mp_('P6') / 2 - mp_('C8'), 3),
    'C8 candidate (our evaluation) minus archive C8': mp.nstr(cand - mp_('C8'), 3),
    'J9 identity A9_1 - Z8_1 + 2 EA7 - 2 EZ6 + D9_lower - J9': mp.nstr(mp_('A9_1') - mp_('Z8_1') + 2 * mp_('(EA7)_0') - 2 * mp_('(EZ6)_0')
                                                                         + mp_('D9_lower') - mp_('J9'), 3),
    'U identity A7_d_1 + D_known - U': mp.nstr(mp_('A7_d_1') + mp_('D_known') - mp_('U'), 3),
    'Kv identity -4 P8 + F3_known - Kv': mp.nstr(-4 * mp_('P8') + mp_('F3_known = 16 X_vv - 8 X_E + S3') - mp_('Kv'), 3),
    'F3_known vs note 16 X_vv - 8 X_E + S3': mp.nstr(16 * mp.mpf(NOTE['X_vv (note l.1366)']) - 8 * mp.mpf(NOTE['X_E (note l.1367)'])
                                                     + mp.mpf(NOTE['S3 (note l.1363)']) - mp_('F3_known = 16 X_vv - 8 X_E + S3'), 3),
    'pi0: 1153/6 + sum c_I pi0(I) with OUR coefficients (must be 88)': str(pi0_C8),
    'pi0: note reduction 5345/12 - R6/2 - R8/8 + 3 R_tail/4 + R9/4 (must be 88)': str(pi0_red),
    'pi0: Ndelta = -4 (R6 - 8719/2 - 190100) (must be -20848)': str(-4 * pi0_Nd),
    'W: our independent three-kink value minus archive W': mp.nstr(our_W - mp_('W'), 3),
    'note decimals vs 100-digit records (max |diff| over shared quantities)': None,
}
shared = [('W (note table l.1243)', 'W'), ('S (note)', 'S'), ('L3 (note)', 'L3'), ('M21 (note)', 'M21'), ('M12 (note)', 'M12'),
          ('N2 (note)', 'N2'), ('U (note l.1351)', 'U'), ('A7_d_1 (note l.1349)', 'A7_d_1'), ('P8 (note l.1368)', 'P8'),
          ('Kv (note l.1369)', 'Kv'), ('J9 (note l.1399)', 'J9'), ('A9_1 (note l.1393)', 'A9_1'), ('P6 (note eq:P6full l.1287)', 'P6'),
          ('B_old (note l.1167)', 'B_old'), ('B_done (note l.1410)', 'B_done'), ('C_fixed (note l.1418)', 'C_fixed'),
          ('C8_num (note l.89)', 'C8'), ('D_ct (note l.1316)', 'D_ct')]
cmp['note decimals vs 100-digit records (max |diff| over shared quantities)'] = mp.nstr(
    max(abs(mp.mpf(NOTE[a]) - mp_(b)) / max(1, abs(mp_(b))) for a, b in shared), 3) + ' (relative; note digits only)'
checks = {
    'B_old': abs(B_ours - mp_('B_old')) < mp.mpf(10)**-60,
    'B_done': abs(B_done_ours - mp_('B_done')) < mp.mpf(10)**-60,
    'C8_assembly': abs(C8_ours - mp_('C8')) < mp.mpf(10)**-60,
    'C_fixed': abs(mp_('C_fixed') - mp_('P6') / 2 - mp_('C8')) < mp.mpf(10)**-60,
    'pi0_C8_88': pi0_C8 == 88 and pi0_red == 88 and -4 * pi0_Nd == -20848,
    'W_independent': abs(our_W - mp_('W')) < mp.mpf(10)**-24,
}
report = {'note': 'SEALED comparison (comparison only).', 'sealing_record_latest': rec['history'][-1]['written'],
          'comparisons': cmp, 'checks': checks, 'ALL_PASS': all(checks.values()),
          'sizing_from_archive_magnitudes (comparison/sizing only)': size,
          'what_is_NOT_tested_here': 'the five inherited inputs S, L3, M21, M12, N2 and the packages U, J9, Kv, Ndelta can only be '
                                     'tested against project values (engine); this file holds the archive side of that comparison'}
json.dump(report, open(CMP / 'comparison_C8_report.json', 'w'), indent=1)
for k, v in cmp.items():
    print(f'  {k}: {v}')
print('checks', checks, 'ALL_PASS', report['ALL_PASS'])

# ----------------------------------------------------------------------------------------------- 4. hashes
files = sorted(p for p in CMP.rglob('*') if p.is_file() and p.name != 'SHA256SUMS' and '__pycache__' not in str(p))
(CMP / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(CMP)}\n' for p in files))
print('SHA256SUMS written for', len(files), 'files')
