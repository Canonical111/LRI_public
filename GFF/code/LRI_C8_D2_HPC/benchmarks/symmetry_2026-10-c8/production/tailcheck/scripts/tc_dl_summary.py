#!/usr/bin/env python3
"""Summary of the double-lift power L8 class for the tail check (Mac; from archived files):
coverage of the class's measured variance by the tested graphs, the targeted run's class and per-graph statistics
(tc_nested_joint.py output) and SE sensitivity scenarios.

  tc_dl_summary.py NESTED_JOINT.json CERT.jsonl.gz SELECT_DATA.csv.gz OUT.json [--se 8.216820957752926]

The class's "measured variance" is the sum over its graph-campaigns of the production's per-graph replicate variance
contribution v divided by Var(C8) (select_data share): an estimate, not a bound on the class's true variance. The SE
scenarios multiply the measured variance of a class by a factor f: SE(f) = SE * sqrt(1 + sum (f - 1) * share). They
are sensitivity scenarios, not error bounds."""
import argparse, csv, gzip, json, math

ap = argparse.ArgumentParser()
ap.add_argument('joint'); ap.add_argument('cert'); ap.add_argument('select'); ap.add_argument('out')
ap.add_argument('--se', type=float, default=8.216820957752926)
a = ap.parse_args()
J = json.load(open(a.joint))
cert = {(r['sector'], r['L'], r['id']): r for r in map(json.loads, gzip.open(a.cert, 'rt')) if not r.get('label')}
sel = {}
for r in csv.DictReader(gzip.open(a.select, 'rt')):
    sel[(r['campaign'], r['sector'], int(r['L']), int(r['graph']))] = r
P8 = sorted({k[3] for k in sel if k[1] == 'power' and k[2] == 8})
dl = [g for g in P8 if cert[('power', 8, g)]['max_orders_cancelled'] >= 2]
unt = [g for g in P8 if min(int(sel[(c, 'power', 8, g)]['points']) for c in 'ab') < 32768]
share = lambda gs: sum(float(sel[(c, 'power', 8, g)]['share']) for g in gs for c in 'ab')
s_dl = share(dl); s_nd = share(set(unt) - set(dl))
tgt = sorted({g['graph'] for g in J['graphs'].values() if g['group'].startswith('double-lift power L8, targeted')})
old = sorted({g['graph'] for g in J['graphs'].values() if g['group'].startswith('untestable power L8, double-lift')})
cls_t = J['classes']['double-lift power L8, targeted (16 largest variance shares)']
cls_o = J['classes']['untestable power L8, double-lift (earlier sample)']
per = []
for gid in sorted(tgt, key=lambda x: -share([x])):
    row = dict(graph=gid, share_of_var_C8=share([gid]), class_fraction=share([gid]) / s_dl, terms=cert[('power', 8, gid)]['terms'],
               clamped=cert[('power', 8, gid)]['clamped'], campaigns={})
    for c in 'ab':
        g = next(x for x in J['graphs'].values() if x['graph'] == gid and x['campaign'] == c and x['group'].startswith('double-lift power L8, targeted'))
        row['campaigns'][c] = dict(production_points=g['production']['points'], production_kurtosis=g['production']['kurtosis'],
                                   production_xi_hat=g['production']['xi_hat'], slope_W0=g['slope_C8_W0'], F=g.get('F'), Phi=g.get('Phi'),
                                   sigma2_rel_2p17_over_2p12=g['sigma2C'][5] / g['sigma2C'][0], hill_2p12=g['hill'][0], hill_2p17=g['hill'][5],
                                   hill_2p19=g['hill'][7] if len(g['levels']) > 7 else None, largest_share_max_2p12=g['share_max'][0],
                                   largest_share_max_2p17=g['share_max'][5], slope_W1=g.get('slope_C8_W1'), slope_extension=g.get('slope_C8_extension_2p17_2p19'))
    per.append(row)
SE = a.se
scen = []
for lab, f, g in [('double-lift class x1.318 (targeted, share-weighted within-run F)', cls_t['F_within_run_2p17_over_Nprod_share_weighted']['value'], 1),
                  ('double-lift class x2.805 (upper end of that F interval)', cls_t['F_within_run_2p17_over_Nprod_share_weighted']['ci95'][1], 1),
                  ('double-lift class x1.737 (upper end of the targeted Phi interval)', cls_t['Phi_fresh_over_production_at_Nprod_share_weighted']['ci95'][1], 1),
                  ('double-lift class x18.9 (earlier 4-graph sample, share-weighted F)', cls_o['F_within_run_2p17_over_Nprod_share_weighted']['value'], 1),
                  ('double-lift class x45 (earlier sample, mean F)', 45.0, 1),
                  ('double-lift class x335 (largest single graph-campaign F of the earlier sample)', 335.0, 1),
                  ('double-lift class x45 and the other untestable power L8 graphs x2', 45.0, 2)]:
    scen.append(dict(scenario=lab, factor_double_lift=f, factor_other_untestable=g, SE=SE * math.sqrt(1 + (f - 1) * s_dl + (g - 1) * s_nd)))
doc = dict(double_lift_graphs=len(dl), double_lift_all_untestable=set(dl) <= set(unt), measured_share_of_var_C8=s_dl,
           other_untestable_graphs=len(set(unt) - set(dl)), other_untestable_measured_share=s_nd,
           targeted=dict(graphs=len(tgt), share_of_var_C8=share(tgt), class_fraction=share(tgt) / s_dl, slope_W0=cls_t['slope_C8_W0'],
                         hill_exponent_W0=cls_t['hill_exponent_W0'], F=cls_t['F_within_run_2p17_over_Nprod_share_weighted'],
                         Phi=cls_t['Phi_fresh_over_production_at_Nprod_share_weighted'], per_graph_slope=cls_t['per_graph_slope_C8_W0'],
                         graphs_with_positive_two_rate_slope=sum(1 for r in per if (r['campaigns']['a']['slope_W0']['value'] + r['campaigns']['b']['slope_W0']['value']) > 0)),
           earlier_sample=dict(graphs=old, share_of_var_C8=share(old), class_fraction=share(old) / s_dl, slope_W0=cls_o['slope_C8_W0'],
                               F=cls_o['F_within_run_2p17_over_Nprod_share_weighted'], Phi=cls_o['Phi_fresh_over_production_at_Nprod_share_weighted']),
           tested_class_fraction=(share(tgt) + share(old)) / s_dl, extensions={k: v for k, v in J['extensions_2p19'].items() if k.startswith('dl:')},
           per_graph=per, se=SE, se_scenarios=scen,
           note='Phi uses graphs SELECTED for large production variance, so regression to the mean biases it low; it is not an unbiased test of '
                'underestimation. The scenarios are sensitivity calculations, not bounds.')
json.dump(doc, open(a.out, 'w'), indent=1)
print(f"double-lift: {len(dl)} graphs, measured share {s_dl:.4e}; tested {len(tgt)}+{len(old)} graphs = {doc['tested_class_fraction']:.4f} of the class's measured variance")
print('targeted slope', cls_t['slope_C8_W0'], 'F', cls_t['F_within_run_2p17_over_Nprod_share_weighted'], 'Phi', cls_t['Phi_fresh_over_production_at_Nprod_share_weighted'])
for s in scen:
    print(f"{s['scenario']:85s} SE {s['SE']:.3f}")
