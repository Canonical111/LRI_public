#!/usr/bin/env python3
"""refit72: headline numbers of the model-independent lens on the hi=72 delta model, the C8 budget with the new noise
term, the data-consistent delta-model systematic, the floor-member nonlinear reruns and the delta-free hi=72 check.
usage: final72.py OUT   (reads compare72.json, headline.json, final_summary.json, members_subset.json, run2_k*_f*/)"""
import sys, os, json, glob
import numpy as np
O = sys.argv[1]
J = lambda p: json.load(open(os.path.join(O, p)))
C = J('compare72.json'); H = J('headline.json'); S = J('final_summary.json'); MS = J('members_subset.json')
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
P = 'LSQ-full E wf (primary)'
prim = C['primary']; CR = C['comparison_runs']
out = {}
# ---------------------------------------------------------------- noise (S10 46..72) sensitivity: primary vs s46
noise = {}
for hi in ('72', '92'):
    a, b = CR['run2_fmedoid'][hi], CR['run_s46'][hi]
    noise[hi] = dict(C8_uncal=a['C8']['uncal'] - b['C8']['uncal'], C8_cal=a['C8']['cal'] - b['C8']['cal'],
                     **{'C%d' % n: a['low'][str(n)]['uncal'] - b['low'][str(n)]['uncal'] for n in (6, 7)})
for hi in ('118',):
    a, b = CR['run2_fmedoid'][hi], CR['run_s46'][hi]
    noise[hi] = {'C%d' % n: a['low'][str(n)]['uncal'] - b['low'][str(n)]['uncal'] for n in (6, 7)}
out['noise_primary_minus_s46'] = noise
# delta-model change alone: s46 (smooth data, new continuation) vs archived run (smooth data, old continuation)
old = C['primary']
out['s46_minus_archived_hi92'] = dict(C8_uncal=CR['run_s46']['92']['C8']['uncal'] - old['92']['C8']['old']['uncal'],
                                      C8_cal=CR['run_s46']['92']['C8']['cal'] - old['92']['C8']['old']['cal'],
                                      **{'C%d' % n: CR['run_s46']['92']['low'][str(n)]['uncal'] - old['92']['C%d' % n]['old']['uncal'] for n in (6, 7)})
# ---------------------------------------------------------------- delta-model systematic (primary family)
T = MS['totals']
def tot(fam, typ, sub, q):
    v = T.get('%s|%s|%s|%s' % (fam, typ, sub, q)); return None if v is None else dict(std=v['std'], halfrange=v['halfrange'])
dm = {}
for q in ('C6', 'C7', 'C8_uncal', 'C8_cal'):
    dm[q] = {'%s/%s' % (typ, sub): tot('full E hi92', typ, sub, q) for typ in ('seam', 'smooth') for sub in ('all', 'mi_cons', 'floor')}
    dm[q]['hi72_smooth_all(in-window artefact)'] = tot('full E hi72', 'smooth', 'all', q)
    dm[q]['full3_seam_floor'] = tot('full3 E hi92', 'seam', 'floor', q)
for q in ('C6', 'C7'):
    dm[q + '_hi118'] = {'%s/%s' % (typ, sub): tot('full E hi118', typ, sub, q) for typ in ('seam', 'smooth') for sub in ('all', 'mi_cons', 'floor')}
out['delta_model'] = dm
# ---------------------------------------------------------------- floor-member nonlinear reruns
fl = {}
base = CR['run2_fmedoid']['92']
for d in sorted(glob.glob(os.path.join(O, 'run2_k*_f*'))):
    p = os.path.join(d, 'analysis_light.json')
    if not os.path.exists(p):
        continue
    L = json.load(open(p))['families']; e = L['%s|hi92' % P]
    fl[os.path.basename(d)] = dict(C8_uncal=e['C8']['uncal_median'] - base['C8']['uncal'], C8_cal=e['C8']['cal_median'] - base['C8']['cal'],
                                   N_cal=e['C8']['N_cal'], C7=e['C7']['median'] - base['low']['7']['uncal'], C6=e['C6']['median'] - base['low']['6']['uncal'],
                                   hi118_C7=L['%s|hi118' % P]['C7']['median'] - CR['run2_fmedoid']['118']['low']['7']['uncal'])
out['floor_member_reruns_shift_vs_primary_hi92'] = fl
# ---------------------------------------------------------------- C8 budget
b = dict(H['C8']['budget_1sigma_like'])
b['noise_S10_46_72 (primary - s46, calibrated, hi92)'] = abs(noise['92']['C8_cal'])
keys_sym = ['family_spread_std (6 family medians, calibrated)', 'delta_model_halfrange_quad', 'C7_reference_41',
            'window_hi72_vs_92_half', 'eff_omega_vs_gap', 'noise_S10_46_72 (primary - s46, calibrated, hi92)']
sym = float(np.sqrt(sum(b[k] ** 2 for k in keys_sym)))
c8c = H['C8']['cal_primary']; c8u = H['C8']['uncal_primary']
out['C8'] = dict(cal=c8c, uncal=c8u, N_cal=H['C8']['N_cal'], cal_range_cfg=H['C8']['cal_range'], uncal_range_cfg=H['C8']['uncal_range'],
                 budget=b, sym_total=sym, rule_onesided_up=H['C8']['rule_onesided_up'], range=[c8c - sym, c8c + sym + H['C8']['rule_onesided_up']],
                 cal_rules=H['C8']['cal_rules'], z_cal=(c8c - REF[8]) / np.hypot(sym, 8015.0), z_uncal=(c8u - REF[8]) / np.hypot(sym, 8015.0),
                 d_vs_earlier=dict(cal=c8c - 8065481.009297927, uncal=c8u - 8062908.08747769))
# uncalibrated budget (same items with the uncalibrated delta and noise; family spread of uncalibrated medians)
fam_unc = [H['C8']['family_uncal'][k] for k in ('primary LSQ-full', 'LSQ-full3 (+l^2 T2)', 'LSQ-full eff-omega', 'LSQ-full self-consistent', 'Neville top92', 'BST top92')]
bu = {'family_spread_std (6 family medians, uncalibrated)': float(np.std(fam_unc)),
      'delta_model_halfrange_quad (smooth, all)': S['delta_model_budget']['full E hi92|C8_uncal|smooth']['total_halfrange_quad'],
      'C7_reference_41': abs(S['C7_reference_sensitivity']['C7+41']['uncal_median_shift']),
      'window_hi72_vs_92_half': abs(prim['72']['C8']['new']['uncal'] - c8u) / 2,
      'noise_S10_46_72': abs(noise['92']['C8_uncal'])}
out['C8']['budget_uncal'] = bu; out['C8']['sym_total_uncal'] = float(np.sqrt(sum(v ** 2 for v in bu.values())))
# ---------------------------------------------------------------- delta-free hi = 72
df = dict(primary={n: prim['72']['C%d' % n]['new'] for n in range(4, 8)}, C8=prim['72']['C8']['new'],
          C8_old_hi72=prim['72']['C8']['old'], s46=CR['run_s46']['72'],
          other={k: v['new'] for k, v in C['other_families'].items() if k.endswith('hi72')},
          accel={t: C['accelerators'][t] for t in ('60', '72') if t in C['accelerators']},
          selection={k: v['72'] for k, v in C['selection'].items() if k.startswith('run2_fmedoid')})
out['delta_free_hi72'] = df
json.dump(out, open(os.path.join(O, 'final72.json'), 'w'), indent=1, default=float)
print(json.dumps({k: out[k] for k in ('noise_primary_minus_s46', 's46_minus_archived_hi92', 'floor_member_reruns_shift_vs_primary_hi92')}, indent=1, default=float))
print('C8', json.dumps(out['C8'], indent=1, default=float))
for q, v in dm.items():
    print(q, {k: (None if x is None else '%.3g/%.3g' % (x['std'], x['halfrange'])) for k, x in v.items()})
