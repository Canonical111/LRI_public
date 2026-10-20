"""Numerical recognition AFTER independently evaluated P6; not a proof."""
from pathlib import Path
import json,sys,mpmath as mp
from fractions import Fraction
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'C8_full_numerical_completion'
mp.mp.dps=100
f3=json.loads((BASE/'data/F3_final_100.json').read_text())['values']
f4=json.loads((BASE/'data/F4_data_100.json').read_text())['values']
six=json.loads((BASE/'inherited/six_new_inputs.json').read_text())['coefficients']
u=json.loads((BASE/'inherited/U_record.json').read_text())['values']['U']
B=mp.mpf(f4['B_old_full'])
for k,w in [('W',4),('S',2),('L3',mp.mpf(3)/32),('M21',-mp.mpf(1)/4),('M12',mp.mpf(1)/2),('N2',-mp.mpf(1)/16)]:B+=w*mp.mpf(six[k])
fixed=B+mp.mpf(f3['F1_known'])/8+3*mp.mpf(u)/4+mp.mpf(f3['Kv'])/32+mp.mpf(f4['J9'])/4
print('Cfixed',mp.nstr(fixed,95))
report={'Cfixed':mp.nstr(fixed,95),'Bdone':mp.nstr(B,95),'scope':'Independent arithmetic from archived numerical inputs; no integer relation has been imposed.'}
if len(sys.argv)>1:
 dat=json.loads(Path(sys.argv[1]).read_text());p6=mp.mpf(dat['values']['P6']);c8=fixed-p6/2
 print('P6',mp.nstr(p6,95));print('C8',mp.nstr(c8,95));report.update(P6=mp.nstr(p6,95),C8=mp.nstr(c8,95))
 z=mp.zeta;basis=[z(2),z(3),z(4),z(5),z(2)*z(3),z(6),z(3)**2,z(7),z(2)*z(5),z(3)*z(4)]
 names=['z2','z3','z4','z5','z2*z3','z6','z3^2','z7','z2*z5','z3*z4']
 trials=[]
 for exp,bd in [(40,10000),(55,100000),(65,1000000),(75,1000000)]:
  rel=mp.pslq(mp.matrix([c8-88]+basis),tol=mp.mpf(10)**(-exp),maxcoeff=bd,maxsteps=10000)
  print('RELATION',exp,bd,rel,flush=True)
  if rel and rel[0]:
   co=[str(Fraction(-v,rel[0])) for v in rel[1:]]
   value=88+sum(mp.mpf(-v)*b/rel[0] for v,b in zip(rel[1:],basis))
   trials.append({'tol_exp':exp,'maxcoeff':bd,'relation':rel,'coefficients':dict(zip(names,co)),'value':mp.nstr(value,95),'residual':mp.nstr(c8-value,20),'status':'numeric_candidate_not_a_proof'})
 report['recognition_trials']=trials
(ROOT/'C8_numeric_recognition.json').write_text(json.dumps(report,indent=2))
if len(sys.argv)>1:
 (ROOT/(Path(sys.argv[1]).stem+'_recognition.json')).write_text(json.dumps(report,indent=2))
