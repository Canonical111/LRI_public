import sys,json,mpmath as m
from pathlib import Path
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'code'))
import power_ms_d3 as p
m.mp.dps=75
j=p.corejet();print('core poles',j)
a=p.pair(p.D/2,-p.F(1,2));e=p.pair(3*p.D/2,-p.F(7,2))
cc=p.mul(p.bseries(a,e),p.bseries(p.plus(a,e,p.pair(-p.D)),a))
dF0=cc[0]*101;dF1=cc[0]*(-37)+cc[1]*101
pred={'L5G086':2*dF0/5,'L6G332':p.A*dF0/3+2*dF1/15,'L6G333':p.A*dF0/3-2*dF1/15}
a=json.load(open(W/'records/power_ms_d3_complete.json'));b=json.load(open(W/'records/power_ms_d3_shifted.json'))
ta={g['id']:g for r in a['loops']for g in r['done']};tb={g['id']:g for r in b['loops']for g in r['done']};checks=[]
for gid,v in pred.items():
 obs=-m.mpf(tb[gid]['ct']['-1'])+m.mpf(ta[gid]['ct']['-1']);err=obs-v
 assert abs(err)<m.mpf('1e-66'),(gid,err)
 checks.append({'id':gid,'predicted_simple_residue_change':str(v),'observed_change':str(obs),'difference':str(err)})
out={'core_pole_jet':{str(k):str(v)for k,v in j.items()if k<0},'chain_constant':str(cc[0]),'chain_linear':str(cc[1]),'checks':checks,'scope':'Independent analytic unknown-jet propagation compared with complete graph/forest recursion.'}
(W/'records/core_propagation_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
