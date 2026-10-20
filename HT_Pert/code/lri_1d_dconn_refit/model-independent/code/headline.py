#!/usr/bin/env python3
"""Headline numbers and C8 error budget of the model-independent lens (from final_summary.json + analysis.json).
usage: headline.py [OUTDIR]"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
O = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, '..', 'out'))
S = json.load(open(os.path.join(O, 'final_summary.json')))
A = json.load(open(os.path.join(O, os.environ.get('MI_PRIMARY', 'run2_medoid'), 'analysis.json')))   # refit72: primary dir via env
F = A['families']; ACC = A['accelerators']
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
P = 'LSQ-full E wf (primary)|hi92'
fams8 = {'primary LSQ-full': P, 'LSQ-full3 (+l^2 T2)': 'LSQ-full3 E wf (+l^2 T2)|hi92',
         'LSQ-full eff-omega': 'LSQ-full E wf_eff (fitted omega3-5)|hi92', 'LSQ-full self-consistent': 'LSQ-full S wf (self-consistent)|hi92'}
H = {'C8': {}}
unc, cal = {}, {}
for lab, key in fams8.items():
    c = F[key]['C8']; unc[lab] = c['uncal_median']; cal[lab] = c['cal_median']
for top in (84, 88, 92):
    e = ACC['dconn E wf top%d' % top]
    unc['Neville top%d' % top] = e['8']['neville']; cal['Neville top%d' % top] = e['C8_neville_cal']
    unc['BST top%d' % top] = e['8']['bst']; cal['BST top%d' % top] = e['C8_bst_cal']
H['C8']['family_uncal'] = unc; H['C8']['family_cal'] = cal
fam_meds = [cal[k] for k in fams8] + [cal['Neville top92'], cal['BST top92']]
c0 = F[P]['C8']['cal_median']
DM = S['delta_model_budget']
budget = {
    'family_spread_std (6 family medians, calibrated)': float(np.std(fam_meds)),
    'delta_model_std_quad (smooth members, k=6,7,8)': DM['full E hi92|C8_cal|smooth']['total_std'],
    'delta_model_halfrange_quad': DM['full E hi92|C8_cal|smooth']['total_halfrange_quad'],
    'C7_reference_41': abs(S['C7_reference_sensitivity']['C7+41']['cal_median_shift']),
    'window_hi72_vs_92_half': abs(F['LSQ-full E wf (primary)|hi72']['C8']['cal_median'] - c0) / 2,
    'eff_omega_vs_gap': abs(cal['LSQ-full eff-omega'] - c0),
}
sym = float(np.sqrt(budget['family_spread_std (6 family medians, calibrated)'] ** 2 + budget['delta_model_halfrange_quad'] ** 2
                    + budget['C7_reference_41'] ** 2 + budget['window_hi72_vs_92_half'] ** 2 + budget['eff_omega_vs_gap'] ** 2))
alt = F[P]['C8']['cal_alt']
H['C8'].update(
    uncal_primary=F[P]['C8']['uncal_median'], uncal_range=F[P]['C8']['uncal_range'], N_cal=F[P]['C8']['N_cal'],
    cal_primary=c0, cal_range=F[P]['C8']['cal_range'], cal_rules=alt,
    budget_1sigma_like=budget, sym_total=sym, rule_onesided_up=alt['lintrend47'] - c0,
    vs_diag=dict(uncal=F[P]['C8']['uncal_median'] - REF[8], cal=c0 - REF[8],
                 z_cal=(c0 - REF[8]) / np.hypot(sym, 8015.0), z_uncal=(F[P]['C8']['uncal_median'] - REF[8]) / np.hypot(sym, 8015.0)),
    earlier_raw_lens=dict(uncal_phys=8063754, cal_phys=8066040, d_uncal=F[P]['C8']['uncal_median'] - 8063754, d_cal=c0 - 8066040))
for n in range(4, 8):
    e = F[P]['C%d' % n]; e118 = F['LSQ-full E wf (primary)|hi118']['C%d' % n]
    HO = S['heldout_calibration_test_primary_hi92'].get(str(n), {})
    H['C%d' % n] = dict(uncal=e['median'], uncal_p10_p90=e['p10_p90'], N=e['N_adequate'], uncal_hi118=e118['median'],
                        cal_heldout_mean=e.get('cal_median'), cal_rules={r: v['median'] for r, v in HO.items()},
                        neville_top92=ACC['dconn E wf top92'][str(n)]['neville'], bst_top92=ACC['dconn E wf top92'][str(n)]['bst'],
                        full3=F['LSQ-full3 E wf (+l^2 T2)|hi92']['C%d' % n]['median'],
                        rel_uncal_x1e3=(e['median'] - REF[n]) / abs(REF[n]) * 1e3, ref=REF[n])
json.dump(H, open(os.path.join(O, 'headline.json'), 'w'), indent=1)
print(json.dumps(H, indent=1))
