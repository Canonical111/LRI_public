import os
from endpoint_growth_finite import *
from finite_extract_fast import extract_finite
T=GEN[6];records=[]
for R in [K.one,T,T**2,T**3,1/(T+1),(T**2+3*T+1)/(T+2),1/(T+2)**2]:
 for ints in [(),(-1,),(-1,-2),(0,-1),(-2,-2),(0,0)]:
  w=tuple(K(a) for a in ints);out={}
  for wa,co in integrate_rat(e*R,w,6).items():
   for wb,cb in endpoint_value(co,wa,6,1/e-5).items():addto(out,wb,cb)
   for wb,cb in endpoint_value(co,wa,6,K.zero,lower=True).items():addto(out,wb,-cb)
  rr=[[list(map(int,w)),[],str(c)] for w,c in clean(out).items()]
  full=extract_finite(rr,5)
  grow=s.expand(sum(scalar(str(c))*functional(ints,p,5) for p,c in polynomial_part(R,6).items()))
  diff=s.expand(full-grow);rec={'R':str(R),'word':ints,'equal':diff==0,'full':str(full),'growth':str(grow),'difference':str(diff)};records.append(rec)
  if diff!=0:print('FAIL',rec,flush=True)
(Path(os.environ.get('F3_REPORT_DIRECTORY',str(ROOT/'data')))/'elementary_growth_check.json').write_text(json.dumps(records,indent=2))
print('ELEMENTARY_GROWTH',len(records),sum(r['equal'] for r in records),flush=True)
