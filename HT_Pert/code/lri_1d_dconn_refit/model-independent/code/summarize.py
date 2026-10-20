#!/usr/bin/env python3
"""Final summary of the model-independent lens on the Dconn-corrected data.
Inputs (all under OUT = ../out): run2_medoid/{grid,analysis}.json (primary, smooth medoid central), mem1/members_analysis.json
(exact member propagation), run2_k*_q*/analysis_light.json (nonlinear member reruns), run1/analysis_light.json
(published pointwise-median central), run3_rawc8/analysis_light.json (lri_c8 lower orders).
usage: summarize.py [OUTDIR]
"""
import sys, os, json, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, '..', 'out'))
os.environ['MI_LIGHT'] = '1'
PRIMARY = os.environ.get('MI_PRIMARY', 'run2_medoid')   # refit72: primary run directory name
sys.argv = [sys.argv[0], os.path.join(OUTD, PRIMARY)]
sys.path.insert(0, HERE)
import analyze_core as an
np = an.np
REF = an.REF
S = {}

A = json.load(open(os.path.join(OUTD, PRIMARY, 'analysis.json')))
M = json.load(open(os.path.join(OUTD, 'mem1', 'members_analysis.json')))
fam = A['families']
P = 'LSQ-full E wf (primary)|hi92'

# ------------------------------------------------------------------ held-out calibration-rule test (primary, hi92)
famk = ('dconn', 'E', 'full', 'wf', 92)
F = an.R[famk]; fl = an.floors(famk)
HO = {}
for n in (5, 6, 7):
    adq = [k for k in F if n in F[k] and an.adequate(F[k][n], fl)]
    low = list(range(4, n))
    cal = [k for k in adq if all(j in F[k] and abs(an.bias(famk, k, j)) < an.BMAX for j in low)]
    rules = collections.defaultdict(list)
    for k in cal:
        c = F[k][n]['c']; b = np.array([an.bias(famk, k, j) for j in low])
        rules['none'].append(c)
        rules['mean'].append(c - b.mean() * abs(c))
        rules['last'].append(c - b[-1] * abs(c))
        if len(low) >= 2:
            a1, a0 = np.polyfit(low, b, 1)
            rules['lintrend'].append(c - (a1 * n + a0) * abs(c))
    HO[n] = {r: dict(N=len(v), median=float(np.median(v)), rel_x1e3=float((np.median(v) - REF[n]) / abs(REF[n]) * 1e3)) for r, v in rules.items()}
S['heldout_calibration_test_primary_hi92'] = HO

# ------------------------------------------------------------------ paired corrected - raw (same configs, exact limits)
famr = ('raw', 'E', 'full', 'raw', 92)
famw = ('raw', 'E', 'full', 'wf', 92)
_, sel = an.c8_family(famk)
PAIR = {}
for n in range(4, 9):
    d = [F[k][n]['c'] - an.R[famw][k][n]['c'] for k in sel['cal'] if n in an.R[famw].get(k, {})]
    PAIR[n] = dict(median=float(np.median(d)), min=float(min(d)), max=float(max(d)))
famH = ('raw', 'H', 'full', 'raw', 92)
for n in range(4, 9):
    d = [F[k][n]['c'] - (an.R[famH][k][n]['c'] + an.GUESS[n]) for k in sel['cal'] if n in an.R[famH].get(k, {})]
    PAIR['vsH_%d' % n] = dict(median=float(np.median(d)), min=float(min(d)), max=float(max(d)))
S['paired_corrected_minus_raw_cal_set'] = PAIR
S['dC_at_92'] = {k: an.D['dC'][k][92] for k in range(4, 9)}

# ------------------------------------------------------------------ nonlinear member reruns
NL = collections.defaultdict(dict)
for d in sorted(glob.glob(os.path.join(OUTD, 'run2_k*_q*'))):
    f = os.path.join(d, 'analysis_light.json')
    if not os.path.exists(f):
        continue
    J = json.load(open(f))
    tag = os.path.basename(d)
    e = J['families'][P]
    NL[tag] = dict(C8_uncal=e['C8'].get('uncal_median'), C8_cal=e['C8'].get('cal_median'), N_cal=e['C8'].get('N_cal'),
                   C7=e['C7'].get('median'), C6=e['C6'].get('median'),
                   members=J['meta'].get('central_members'))
S['nonlinear_member_reruns_primary_hi92'] = NL
base = fam[P]
for k in (6, 7, 8):
    tags = [t for t in NL if t.startswith('run2_k%d_' % k)]
    if tags:
        for q in ('C8_uncal', 'C8_cal', 'C7', 'C6'):
            v = [NL[t][q] for t in tags if NL[t][q] is not None]
            b0 = base['C8']['uncal_median'] if q == 'C8_uncal' else base['C8']['cal_median'] if q == 'C8_cal' else base[q]['median']
            if v:
                S.setdefault('nonlinear_spread', {})['k%d_%s' % (k, q)] = dict(min=float(min(v) - b0), max=float(max(v) - b0))

# ------------------------------------------------------------------ other runs
for name in ('run1', 'run3_rawc8'):
    f = os.path.join(OUTD, name, 'analysis_light.json')
    if os.path.exists(f):
        J = json.load(open(f)); e = J['families'][P]
        S['run_' + name] = dict(C8_uncal=e['C8'].get('uncal_median'), C8_cal=e['C8'].get('cal_median'), N_cal=e['C8'].get('N_cal'),
                                lower={n: e['C%d' % n].get('median') for n in range(4, 8)})

# ------------------------------------------------------------------ delta-model error budget (primary, hi92; std over members)
def dm(level_mode_hi, q, typ='smooth'):
    ent = M['families'][level_mode_hi]
    out = {}
    for k in (6, 7, 8):
        s = ent.get('%s_k%d' % (typ, k), {}).get(q)
        if s:
            out[k] = dict(std=s['std'], halfrange=s['halfrange'], cons_std=s.get('cons_std'), cons_halfrange=s.get('cons_halfrange'))
    tot_std = float(np.sqrt(sum(v['std'] ** 2 for v in out.values()))) if out else None
    tot_hr = float(np.sqrt(sum(v['halfrange'] ** 2 for v in out.values()))) if out else None
    return dict(per_k=out, total_std=tot_std, total_halfrange_quad=tot_hr)


DM = {}
for q in ('C6', 'C7', 'C8_uncal', 'C8_cal'):
    for lmh in ('full E hi92', 'full E hi118', 'full3 E hi92', 'full E hi72'):
        for typ in ('smooth', 'seam'):
            r = dm(lmh, q, typ)
            if r['per_k']:
                DM['%s|%s|%s' % (lmh, q, typ)] = r
S['delta_model_budget'] = DM

# ------------------------------------------------------------------ headline tables
def c8row(lab):
    e = fam[lab]['C8']
    return dict(N_cal=e.get('N_cal'), uncal=e.get('uncal_median'), uncal_range=e.get('uncal_range'), cal=e.get('cal_median'),
                cal_range=e.get('cal_range'), cal_alt=e.get('cal_alt'), bias_x1e3=e.get('bias_median_x1e3'))


S['C8_families'] = {lab: c8row(lab) for lab in fam if 'C8' in fam[lab] and fam[lab]['C8'].get('N_cal')}
ACC = A['accelerators']
S['accelerators_C8'] = {lab: dict(neville=e['8']['neville'], neville_cal=e.get('C8_neville_cal'), bst=e['8']['bst'], bst_cal=e.get('C8_bst_cal'),
                                  rel_x1e3={n: [e[str(n)]['neville_rel_x1e3'], e[str(n)]['bst_rel_x1e3']] for n in range(3, 8)})
                        for lab, e in ACC.items() if not lab.startswith('_') and '8' in e}
S['lower_orders'] = {lab: {n: fam[lab]['C%d' % n] for n in range(3, 8)} for lab in fam if lab.endswith(('hi92', 'hi118'))}
S['C7_reference_sensitivity'] = A['C7_reference_sensitivity']
S['jacobian_dC8_dlim'] = A['jacobian_dC8_dlim']
json.dump(S, open(os.path.join(OUTD, 'final_summary.json'), 'w'), indent=1, default=float)

# ------------------------------------------------------------------ print
print('held-out calibration test (primary hi92), rel x1e3 of the calibrated median vs reference:')
for n, r in HO.items():
    print('  C%d: ' % n + ' | '.join('%s %+.3f (N%d)' % (k, v['rel_x1e3'], v['N']) for k, v in r.items()))
print('paired corrected - raw (exact limits, same cal configs): ' + ' '.join('C%d %+.4g [%+.4g,%+.4g]' % (n, PAIR[n]['median'], PAIR[n]['min'], PAIR[n]['max']) for n in range(4, 9)))
print('paired corrected - (raw H + guess):                     ' + ' '.join('C%d %+.4g' % (n, PAIR['vsH_%d' % n]['median']) for n in range(4, 9)))
print('dC at L=92:', {k: round(v, 5) for k, v in S['dC_at_92'].items()})
print('nonlinear member reruns (primary hi92):')
for t, v in NL.items():
    print('  %-14s C8 uncal %s cal %s Ncal %s C7 %s C6 %s' % (t, v['C8_uncal'], v['C8_cal'], v['N_cal'], v['C7'], v['C6']))
print('nonlinear spread vs medoid:', json.dumps(S.get('nonlinear_spread'), indent=0)[:1500])
for k in ('run_run1', 'run_run3_rawc8'):
    print(k, S.get(k))
print('delta-model budget (std quad over k; halfrange quad):')
for k, v in DM.items():
    print('  %-40s std %.3g  hr %.3g  per-k std %s' % (k, v['total_std'], v['total_halfrange_quad'], {kk: round(vv['std'], 2) for kk, vv in v['per_k'].items()}))
