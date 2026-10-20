"""Conservative structural audit only; does not assign values to missing cores."""
from pathlib import Path
import sys,json,itertools,time
W=Path(__file__).resolve().parents[1];R=W/'reference/power_routing';sys.path.insert(0,str(R))
import position_kite_leaf_ms as pm
# Its rawfactors builds Gamma/KLT representations, but does not evaluate them.
# Check raw graphs and every quotient needed by the recursive MS construction.
from position_ms import normalized,uvsubs,forestsets,quotient,rootsafe,Unsolved,Singular
from functools import lru_cache
@lru_cache(None)
def route(ed):
 roots=rootsafe(ed)
 for rr in roots:
  try:
   ff=pm.rawfactors(ed,rr)
   return {'root':rr,'gamma_factor_count':len(ff[1]),'kite_factor_count':len(ff[2]),'factorization':str(ff)}
  except (Unsolved,Singular,ValueError,ZeroDivisionError):pass
 return None
@lru_cache(None)
def closed(ed):
 ed=normalized(ed)
 for ss,ee in uvsubs(ed):
  if not closed(ee):return False
 for rr in rootsafe(ed):
  try:
   ff=pm.rawfactors(ed,rr)
   for fs in forestsets(ed):
    qd,qr=quotient(ed,[ss for ss,ee in fs],rr);pm.rawfactors(qd,qr)
   return True
  except (Unsolved,Singular,ValueError,ZeroDivisionError):pass
 return False
if __name__=='__main__':
 st=time.time();ans=[];inv=json.load(open(W/'inputs/L7/inventory.json'))
 for g in inv:
  if not g['power_subgraphs']or g['mass_numerator']==4:continue
  ed=[];k=0
  for a in range(8):
   for b in range(a+1,8):
    ed +=[(a,b)]*((g['key']>>(2*k))&3);k+=1
  ed=tuple(ed);r=route(ed)
  ans.append({'id':g['id'],'raw_has_Gamma_KLT_route':r is not None,'route':r,'MS_closed':closed(ed)if r else False})
  if len(ans)%25==0:
   print(len(ans),'raw',sum(x['raw_has_Gamma_KLT_route']for x in ans),'ms',sum(x['MS_closed']for x in ans),'s',time.time()-st,flush=True)
   (W/'verification/power_route_audit_partial.json').write_text(json.dumps(dict(complete=False,rows=ans,seconds=time.time()-st),indent=2))
 (W/'verification/power_route_audit.json').write_text(json.dumps(dict(complete=True,numerical_evaluation_performed=False,rows=ans,seconds=time.time()-st),indent=2))
