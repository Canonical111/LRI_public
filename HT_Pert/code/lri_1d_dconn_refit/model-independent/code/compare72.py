#!/usr/bin/env python3
"""refit72: compare the model-independent lens on the hi=72 delta model with the archived hi=44 run (read-only).
Reads OUT (new) and the archived out/ directory; writes OUT/compare72.json and prints the tables.
usage: compare72.py OUT"""
import sys, os, json, glob
import numpy as np
O = sys.argv[1]
ARCH = '<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/model-independent/out'
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
P = 'LSQ-full E wf (primary)'
J = lambda p: json.load(open(p))
A = J(os.path.join(O, 'run2_fmedoid', 'analysis.json'))
A0 = J(os.path.join(ARCH, 'run2_medoid', 'analysis.json'))
S = J(os.path.join(O, 'final_summary.json')); S0 = J(os.path.join(ARCH, 'final_summary.json'))
H = J(os.path.join(O, 'headline.json')); H0 = J(os.path.join(ARCH, 'headline.json'))
X = {}


def fam(an, name, hi):
    return an['families'].get('%s|hi%d' % (name, hi), {})


def c8(an, name, hi):
    e = fam(an, name, hi).get('C8') or {}
    return dict(N_adq=e.get('N_adequate'), N_cal=e.get('N_cal'), uncal=e.get('uncal_median'), cal=e.get('cal_median'),
                uncal_range=e.get('uncal_range'), cal_range=e.get('cal_range'), cal_alt=e.get('cal_alt'),
                bias=e.get('bias_median_x1e3'), all_adq=e.get('all_adequate_median'))


def low(an, name, hi, n):
    e = fam(an, name, hi).get('C%d' % n) or {}
    return dict(N=e.get('N_adequate'), uncal=e.get('median'), rel=e.get('rel_median_x1e3'), cal=e.get('cal_median'),
                cal_rel=e.get('cal_rel_x1e3'), p10_p90=e.get('p10_p90'), N_cal=e.get('N_cal'))


f = lambda x, nd=0: '-' if x is None else ('%.' + str(nd) + 'f') % x
# ------------------------------------------------------------------ 1. primary family, all upper edges
print('=== primary LSQ-full E wf: new (hi72 delta) vs archived (hi44 delta)')
T = {}
for hi in (60, 72, 92, 118):
    row = {}
    for n in range(4, 8):
        row['C%d' % n] = dict(new=low(A, P, hi, n), old=low(A0, P, hi, n))
    if hi <= 92:
        row['C8'] = dict(new=c8(A, P, hi), old=c8(A0, P, hi))
    T[hi] = row
    for n in range(4, 8):
        a, b = row['C%d' % n]['new'], row['C%d' % n]['old']
        nd = 5 if n == 4 else 3 if n == 5 else 2 if n == 6 else 0
        print(' hi%-3d C%d uncal %s (N%s, rel %s e-3) cal %s | old %s (N%s) cal %s | d_uncal %s d_cal %s' % (
            hi, n, f(a['uncal'], nd), a['N'], f(a['rel'], 3), f(a['cal'], nd), f(b['uncal'], nd), b['N'], f(b['cal'], nd),
            f(None if a['uncal'] is None or b['uncal'] is None else a['uncal'] - b['uncal'], nd + 1),
            f(None if a['cal'] is None or b['cal'] is None else a['cal'] - b['cal'], nd + 1)))
    if hi <= 92:
        a, b = row['C8']['new'], row['C8']['old']
        print(' hi%-3d C8 uncal %s cal %s (Nadq %s Ncal %s; cal range %s) | old uncal %s cal %s (Ncal %s) | d %s / %s | b x1e3 %s' % (
            hi, f(a['uncal']), f(a['cal']), a['N_adq'], a['N_cal'], a['cal_range'] and [round(x) for x in a['cal_range']],
            f(b['uncal']), f(b['cal']), b['N_cal'],
            f(None if a['uncal'] is None or b['uncal'] is None else a['uncal'] - b['uncal']),
            f(None if a['cal'] is None or b['cal'] is None else a['cal'] - b['cal']),
            a['bias'] and ' '.join('%+.3f' % a['bias'][str(n)] for n in range(3, 8))))
X['primary'] = T
# ------------------------------------------------------------------ 2. other families at hi 72 and 92
print('\n=== other LSQ families (C8 uncal / cal, Ncal; C6, C7 uncal)')
OF = {}
for name in ('LSQ-full3 E wf (+l^2 T2)', 'LSQ-full E wf_eff (fitted omega3-5)', 'LSQ-full S wf (self-consistent)', 'LSQ-full E raw-omega',
             'LSQ-full3 S wf (self-consistent)'):
    for hi in (72, 92):
        a, b = c8(A, name, hi), c8(A0, name, hi)
        l6, l7 = low(A, name, hi, 6), low(A, name, hi, 7)
        OF['%s|hi%d' % (name, hi)] = dict(new=a, old=b, C6=l6, C7=l7)
        print(' %-40s hi%d C8 %s / %s (N%s) | old %s / %s (N%s) | C6 %s C7 %s' % (
            name, hi, f(a['uncal']), f(a['cal']), a['N_cal'], f(b['uncal']), f(b['cal']), b['N_cal'], f(l6['uncal'], 2), f(l7['uncal'])))
X['other_families'] = OF
# ------------------------------------------------------------------ 3. accelerators
print('\n=== accelerators dconn E wf (Neville N>=6,step>=2 | BST), C8 raw and calibrated')
AC = {}
for top in (60, 72, 84, 88, 92, 118):
    e = A['accelerators'].get('dconn E wf top%d' % top); e0 = A0['accelerators'].get('dconn E wf top%d' % top)
    if not e:
        continue
    ent = {n: dict(nev=e[str(n)]['neville'], bst=e[str(n)]['bst']) for n in range(4, 9) if str(n) in e}
    ent['C8_nev_cal'] = e.get('C8_neville_cal'); ent['C8_bst_cal'] = e.get('C8_bst_cal')
    if e0:
        ent['old'] = {n: dict(nev=e0[str(n)]['neville'], bst=e0[str(n)]['bst']) for n in range(4, 9) if str(n) in e0}
        ent['old']['C8_nev_cal'] = e0.get('C8_neville_cal'); ent['old']['C8_bst_cal'] = e0.get('C8_bst_cal')
    AC[top] = ent
    s = ' top%-3d' % top + ' '.join(' C%d %s|%s' % (n, f(ent[n]['nev'], 2 if n < 8 else 0), f(ent[n]['bst'], 2 if n < 8 else 0)) for n in range(4, 9) if n in ent)
    if 8 in ent:
        s += ' | C8 cal nev %s bst %s' % (f(ent['C8_nev_cal']), f(ent['C8_bst_cal']))
        if e0:
            s += ' | old C8 %s|%s cal %s|%s' % (f(ent['old'][8]['nev']), f(ent['old'][8]['bst']), f(ent['old']['C8_nev_cal']), f(ent['old']['C8_bst_cal']))
    print(s)
X['accelerators'] = AC
# ------------------------------------------------------------------ 4. delta-model budget (exact member propagation)
print('\n=== delta-model budget (std / half-range, quadrature over k): new | old')
DM = {}
for key in sorted(S['delta_model_budget']):
    a = S['delta_model_budget'][key]; b = S0['delta_model_budget'].get(key)
    DM[key] = dict(new=a, old=b)
    print(' %-34s std %8.3g hr %8.3g per-k std %s | old std %s hr %s' % (key, a['total_std'], a['total_halfrange_quad'],
          {k: round(v['std'], 3) for k, v in a['per_k'].items()}, b and '%.3g' % b['total_std'], b and '%.3g' % b['total_halfrange_quad']))
X['delta_budget'] = DM
M = J(os.path.join(O, 'mem1', 'members_analysis.json'))
print(' member check base vs grid maxrel', M['checks'])
cons = {}
for fk, ent in M['families'].items():
    for tk, s in ent.items():
        cons['%s|%s' % (fk, tk)] = (s['n_consistent'], s['n_members'])
X['member_consistency'] = cons
print(' consistent members (>=50% of cal configs stay adequate):', {k: v for k, v in cons.items() if k.startswith('full E hi92')})
# ------------------------------------------------------------------ 5. nonlinear reruns
print('\n=== nonlinear member reruns (primary hi92), shift vs primary: new | old')
X['nonlinear_spread'] = dict(new=S.get('nonlinear_spread'), old=S0.get('nonlinear_spread'),
                             reruns=S.get('nonlinear_member_reruns_primary_hi92'))
for k, v in (S.get('nonlinear_spread') or {}).items():
    o = (S0.get('nonlinear_spread') or {}).get(k, {})
    print(' %-14s [%+9.1f, %+9.1f] | old [%s, %s]' % (k, v['min'], v['max'], f(o.get('min'), 1), f(o.get('max'), 1)))
for t, v in sorted((S.get('nonlinear_member_reruns_primary_hi92') or {}).items()):
    print('   %-13s C8 %s / %s Ncal %s C7 %s C6 %s' % (t, f(v['C8_uncal']), f(v['C8_cal']), v['N_cal'], f(v['C7']), f(v['C6'], 2)))
# ------------------------------------------------------------------ 6. comparison runs (central, noise, raw source, reproduction)
print('\n=== comparison runs (light analysis), primary family: C8 uncal/cal (Ncal) and C4..C7 uncal, per hi')
CR = {}
for run in ('run2_fmedoid', 'run1', 'run_mimedoid', 'run_fmean', 'run_s46', 'run3_rawc8', 'run0_repro'):
    p = os.path.join(O, run, 'analysis_light.json')
    if not os.path.exists(p):
        continue
    L = J(p); CR[run] = {}
    for hi in (60, 72, 92, 118):
        ent = dict(C8=c8(L, P, hi) if hi <= 92 else None, low={n: low(L, P, hi, n) for n in range(4, 8)})
        CR[run][hi] = ent
        s = ' %-13s hi%-3d' % (run, hi)
        if ent['C8']:
            s += ' C8 %s / %s (N%s)' % (f(ent['C8']['uncal']), f(ent['C8']['cal']), ent['C8']['N_cal'])
        s += ' ' + ' '.join('C%d %s' % (n, f(ent['low'][n]['uncal'], 4 if n == 4 else 3 if n == 5 else 2 if n == 6 else 0)) for n in range(4, 8))
        print(s)
X['comparison_runs'] = CR
# reproduction check against the archive (archived data and code path, 'medoid' central)
if 'run0_repro' in CR:
    R0 = J(os.path.join(O, 'run0_repro', 'analysis.json')) if os.path.exists(os.path.join(O, 'run0_repro', 'analysis.json')) else None
    mx = 0.0; cnt = 0
    for key, ent in A0['families'].items():
        if R0 is None or key not in R0['families']:
            continue
        for q, v in ent.items():
            for kk in ('median', 'cal_median', 'uncal_median'):
                if isinstance(v, dict) and kk in v and kk in R0['families'][key].get(q, {}):
                    a, b = v[kk], R0['families'][key][q][kk]
                    mx = max(mx, abs(a - b) / max(1.0, abs(b))); cnt += 1
    accmx = 0.0
    if R0:
        for lab, e in A0['accelerators'].items():
            if lab.startswith('_') or lab not in R0['accelerators']:
                continue
            for n, v in e.items():
                if isinstance(v, dict) and 'neville' in v:
                    accmx = max(accmx, abs(v['neville'] - R0['accelerators'][lab][n]['neville']) / max(1, abs(v['neville'])))
    X['repro'] = dict(n_compared=cnt, max_rel_diff_families=mx, max_rel_diff_neville=accmx)
    print('\nreproduction of the archived run2_medoid (archived data, same code path): %d family quantities, max rel diff %.2e; Neville max rel %.2e' % (cnt, mx, accmx))
# ------------------------------------------------------------------ 7. selection sensitivity
print('\n=== selection sensitivity (FAC NOISE BMAX): primary hi92 / hi72 C8 uncal, cal, Ncal')
SEL = {}
for run in ('run2_fmedoid', 'run_s46'):
    for p in sorted(glob.glob(os.path.join(O, run, 'sel_*.json'))):
        L = J(p); tag = os.path.basename(p)[4:-5]
        SEL['%s|%s' % (run, tag)] = {hi: c8(L, P, hi) for hi in (72, 92)}
        a, b = SEL['%s|%s' % (run, tag)][92], SEL['%s|%s' % (run, tag)][72]
        print(' %-13s %-16s hi92 %s / %s (N%s)  hi72 %s / %s (N%s)' % (run, tag, f(a['uncal']), f(a['cal']), a['N_cal'], f(b['uncal']), f(b['cal']), b['N_cal']))
X['selection'] = SEL
# ------------------------------------------------------------------ 8. floors
print('\n=== residual floors (5th pct maxres) primary family, n = 6, 7, 8: new | old | s46')
FL = {}
Ls46 = J(os.path.join(O, 'run_s46', 'analysis.json')) if os.path.exists(os.path.join(O, 'run_s46', 'analysis.json')) else None
for hi in (60, 72, 92, 118):
    key = '%s|hi%d' % (P, hi)
    a = A['floors'].get(key, {}); b = A0['floors'].get(key, {}); c = (Ls46 or {}).get('floors', {}).get(key, {})
    FL[hi] = dict(new=a, old=b, s46=c)
    print(' hi%-3d ' % hi + ' '.join('n%s %.2e|%.2e|%s' % (n, a.get(n, np.nan), b.get(n, np.nan), ('%.2e' % c[n]) if n in c else '-') for n in ('6', '7', '8') if n in a))
X['floors'] = FL
# ------------------------------------------------------------------ 9. headline + budget
X['headline'] = H; X['headline_old'] = H0
print('\n=== headline C8 (new | old)')
for q in ('uncal_primary', 'cal_primary', 'sym_total', 'rule_onesided_up', 'N_cal'):
    print(' %-18s %s | %s' % (q, H['C8'][q], H0['C8'][q]))
for q, v in H['C8']['budget_1sigma_like'].items():
    print('   budget %-50s %9.1f | %9.1f' % (q, v, H0['C8']['budget_1sigma_like'][q]))
print(' cal rules', {k: round(v) for k, v in H['C8']['cal_rules'].items()}, '| old', {k: round(v) for k, v in H0['C8']['cal_rules'].items()})
print(' family uncal', {k: round(v) for k, v in H['C8']['family_uncal'].items()})
print(' family cal  ', {k: round(v) for k, v in H['C8']['family_cal'].items()})
for n in range(4, 8):
    h, h0 = H['C%d' % n], H0['C%d' % n]
    print(' C%d uncal %.6g cal %s rules %s | old uncal %.6g cal %s' % (n, h['uncal'], h['cal_heldout_mean'], {k: round(v, 3) for k, v in h['cal_rules'].items()},
                                                                  h0['uncal'], h0['cal_heldout_mean']))
print(' C7 ref sensitivity', S['C7_reference_sensitivity'], '| jacobian', S['jacobian_dC8_dlim'])
print(' held-out calibration test', json.dumps(S['heldout_calibration_test_primary_hi92']))
json.dump(X, open(os.path.join(O, 'compare72.json'), 'w'), indent=1, default=float)
