import json,sys,itertools,math
import mpmath as m
from fractions import Fraction as F
from pathlib import Path
W=Path(__file__).parent;B=W/'lri_C6_d2_two_forest_update';sys.path.insert(0,str(B/'analytic/code'))
from sp_classify import canon
m.mp.dps=65
inv=json.load(open(B/'classified_inventory.json'))['loops'];status=json.load(open(B/'verification/C6_d2_continuation_result.json'))
a=json.load(open(W/'position_kite_leaf_ms_32_45_.02.json'));b=json.load(open(W/'position_kite_leaf_ms_48_55_.016.json'))
errs=[];count=0;rootmax=m.mpf(0)
for ra,rb in zip(a['loops'],b['loops']):
 aa={g['id']:g for g in ra['solved']};bb={g['id']:g for g in rb['solved']};assert aa.keys()==bb.keys()
 for name,g in aa.items():
  gg=bb[name];er=max(abs(m.mpf(v)-m.mpf(gg['ct'].get(k,'0')))for k,v in g['ct'].items());errs.append((er,name));count+=len(g['ct']);rootmax=max(rootmax,m.mpf(gg['root_error']))
refs=json.load(open(B/'verification/reference_periods.json'));P4=m.mpf(refs['P4_2']);twos=[]
for name in ['L6G106','L6G117']:
 g=next(x for x in inv[5]['graphs']if x['id']==name);assert not g['log_subgraphs'];assert len(g['power_subgraphs'])==1
 mask,nv,ne=g['power_subgraphs'][0];ss={v for v in range(7)if mask>>v&1};assert nv==2 and ne==3
 e=g['edges'];att=[xy for xy in e if len(set(xy)&ss)==1];assert len(att)==2
 bd=[next(v for v in xy if v not in ss)for xy in att]
 reduced=[xy for xy in e if not(set(xy)&ss)]+[bd]
 target=next(h['id']for h in inv[3]['graphs']if canon(h['edges'])==canon(reduced));assert next(h for h in inv[3]['graphs']if h['id']==target)['primitive']
 assert F(g['weight4'])==2 and F(g['weight2'])==0
 twos.append({'id':name,'subgraph_vertices':sorted(ss),'boundary':bd,'reduced_primitive':target,'gamma_factor_at_zero':-4,'MS_b6':'16*P4(2)','MS_c6':'0'})
total=0;counts={};remain={};parts={}
for L,key in [(5,'remaining_five_loop_mass_ids'),(6,'remaining_six_loop_ids')]:
 target=set(status[key]);solved={g['id']:g for g in b['loops'][L-1]['solved']};names=target&solved.keys();delta=m.mpf(0)
 for name in names:
  g=solved[name]
  delta+=(3*m.mpf(g['c'])-m.mpf(g['b']))/2187 if L==6 else -24*m.log(2)*m.mpf(g['c'])/2187
 if L==6:
  assert {'L6G106','L6G117'}<=target;names|={'L6G106','L6G117'};delta-=32*P4/2187
 counts[L]=len(names);remain[L]=sorted(target-names);parts[L]=str(delta);total+=delta
 assert not any(g['power_subgraphs']for g in inv[L-1]['graphs']if g['id']in remain[L])
# Existing partial value is preserved as input, not used to determine any graph.
print('old status keys',list(status))
old=m.mpf('175.90008447')
report={'method':'Coordinate-space Riesz convolution, complex Selberg and split-contour 3F2; separately verified critical sunset contraction', 'Cauchy_runs':[[32,45,'.02'],[48,55,'.016']], 'pole_coefficients_compared':count,'max_absolute_comparison':str(max(errs)[0]),'max_comparison_graph':max(errs)[1],'max_root_discrepancy':str(rootmax),'sunset_contractions':twos,'newly_evaluated_target_counts':counts,'new_target_contributions_C6':parts,'new_total_contribution_C6':str(total),'updated_partial_from_rounded_baseline':str(old+total),'partial_is_not_estimate':True,'remaining_ids':remain,'full_C6_2':None}
W.joinpath('analytic_extension_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='remaining_ids'},indent=2))
