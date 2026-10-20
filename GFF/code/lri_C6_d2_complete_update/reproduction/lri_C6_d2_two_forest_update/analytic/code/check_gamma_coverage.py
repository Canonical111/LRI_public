"""Exact-symbolic/numerical cross-checks and disjoint target coverage.
All unsupported graph counterterms remain explicitly missing.
"""
from pathlib import Path
import json,collections
from fractions import Fraction as F
import networkx as nx
import sympy as s
import mpmath as mp
R=Path(__file__).resolve().parents[1];old=R.parent
inv=json.load(open(old/'classified_inventory.json'));ex=json.load(open(R/'verification/sp_exact.json'));nu=json.load(open(R/'verification/sp_ms_90.json'))
mp.mp.dps=80;ell,zeta2,zeta3,zeta5=s.symbols('ell zeta2 zeta3 zeta5');dic={ell:s.log(2),zeta2:s.zeta(2),zeta3:s.zeta(3),zeta5:s.zeta(5)}
parsed=lambda x:s.sympify(x,locals={'ell':ell,'zeta2':zeta2,'zeta3':zeta3,'zeta5':zeta5})
matches=0;mx=mp.mpf(0);local=mp.mpf(0);route=mp.mpf(0);nroute=0;lc=[]
for X,N,row in zip(ex['loops'],nu['loops'],inv['loops']):
 assert X['loop']==N['loop']==row['loop'];gd={g['id']:g for g in N['graphs']}
 for g in X['graphs']:
  ng=gd[g['id']]
  for k,v in g['counterterm'].items():
   value=mp.mpf(str(s.N(parsed(v).subs(dic),80)));err=abs(value-mp.mpf(ng['MS_counterterm'].get(k,0)));mx=max(mx,err);assert err<mp.mpf('1e-65');matches+=1
  nroute+=ng.get('routing_checks',0);local=max(local,mp.mpf(ng.get('maximum_locality_error',0)));route=max(route,mp.mpf(ng.get('max_routing_error',0)))
 Gset={g['id']for g in X['graphs']};artset=set()
 for g in row['graphs']:
  blocks=list(nx.biconnected_components(nx.Graph(g['edges'])))
  if len(blocks)>1 and all(sum(set(e)<=b for e in g['edges'])==2*(len(b)-1)for b in blocks):artset.add(g['id'])
 gamma_nonzero={g['id']for g in X['graphs']if parsed(g['counterterm'].get('-1','0'))!=0}
 primitive={g['id']for g in row['graphs']if g['primitive']}
 single={g['id']for g in row['graphs']if len(g['log_subgraphs'])==1 and not g['power_subgraphs']}
 double={g['id']for g in row['graphs']if len(g['log_subgraphs'])==2 and not g['power_subgraphs']}
 # Known data used at L6 and L5 are different.
 computed=Gset|artset|(primitive|single|double if row['loop']==6 else single if row['loop']==5 else set())
 if row['loop']==6:
  zero_weight={g['id']for g in row['graphs']if 3*F(g['weight2'])-F(g['weight4'])==0}
 elif row['loop']==5:zero_weight={g['id']for g in row['graphs']if F(g['weight2'])==0}
 else:zero_weight=set()
 computed|=zero_weight
 rest=[g for g in row['graphs']if g['id']not in computed]
 assert not(Gset&primitive) if row['loop']>=3 else True
 if row['loop']in(5,6):
  assert not(Gset&single)
  if row['loop']==6:assert not(Gset&double)
 lc.append({'loop':row['loop'],'all_classes':len(row['graphs']),'gamma_solved':len(Gset),'gamma_nonzero_simple_poles':len(gamma_nonzero),'homogeneous_articulation_classes':len(artset),'additional_articulation_zeros':sorted(artset-Gset),'direct_target_zero_weight':len(zero_weight),'computed_or_exact_zero':len(computed),'remaining_target_classes':len(rest),'remaining_power':sum(bool(g['power_subgraphs'])for g in rest),'remaining_log_profile':dict(collections.Counter(len(g['log_subgraphs'])for g in rest)),'remaining_ids':[g['id']for g in rest],'gamma_ids':sorted(Gset),'primitive_ids':sorted(primitive),'single_ids':sorted(single),'double_ids':sorted(double),'target_zero_weight_ids':sorted(zero_weight)})
b6=parsed(ex['loops'][5]['b']);c6=parsed(ex['loops'][5]['c']);c5=parsed(ex['loops'][4]['c'])
raw=s.expand((3*c6-b6)/2187);joined=s.expand((3*c6-b6-24*ell*c5)/2187)
# Two-loop exact control and full three-loop control after restoring two non-Gamma graphs.
A=4*ell;Q=s.Symbol('Q2');b3=parsed(ex['loops'][2]['b']);c3=parsed(ex['loops'][2]['c'])
assert parsed(ex['loops'][1]['b'])==-6*A and parsed(ex['loops'][1]['c'])==-A
assert s.expand(c3+s.Rational(3,4)*A*A/3-(s.Rational(7,2)*A*A-s.Rational(4,3)))==0
assert s.expand(b3+s.Rational(9,4)*A*A/3+6*Q-(s.Rational(87,4)*A*A-4+6*Q))==0
out={'gamma_counterterm_coefficients_compared':matches,'maximum_absolute_symbolic_vs_90dps_error':str(mx),'accepted_terminal_routings':nroute,'maximum_routing_error_90dps':str(route),'maximum_scale_locality_error_90dps':str(local),'exact_2_loop_controls':2,'exact_3_loop_controls_after_restoring_known_wineglass_and_primitive':2,'scope':'Graph-sector results and carried inputs, not a complete physical C6(2). Graph-count closure is not relative numerical accuracy.','gamma_six_loop_only':str(raw),'gamma_six_loop_only_tex':s.latex(raw),'gamma_six_loop_only_value':str(s.N(raw.subs(dic),70)),'gamma_physical_combination':str(joined),'gamma_physical_combination_tex':s.latex(joined),'gamma_physical_combination_value':str(s.N(joined.subs(dic),70)),'coverage':lc}
(R/'verification/gamma_and_coverage_checks.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items()if k!='coverage'});print('COVERAGE',[(x['loop'],x['computed_or_exact_zero'],x['remaining_target_classes'],x['remaining_power'])for x in lc])
