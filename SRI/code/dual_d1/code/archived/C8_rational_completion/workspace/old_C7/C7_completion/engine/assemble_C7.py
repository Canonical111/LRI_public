"""Determinant-order response assembly from freshly evaluated raw moments."""
import assemble_C6 as ac
import sympy as s,json,sys,time
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parent
v,d,ell=ac.v,ac.d,ac.ell
ac.DERIV[(1,2)]='vdd'
for name in ['Q8','EQ6','EZ6']:
 ac.rawf[name]=s.Function(name)(v,d)
Q8,EQ6=ac.rawf['Q8'],ac.rawf['EQ6']
Q6=ac.rawf['Q6'];Z2=ac.rawf['Z2'];Z4=ac.rawf['Z4'];Z6=ac.rawf['Z6']
Q4=ac.rawf['Q4'];Q2=ac.rawf['Q2']
EQ4=ac.rawf['EQ4'];EQ2=ac.rawf['EQ2'];EZ2=ac.rawf['EZ2'];EZ4=ac.rawf['EZ4']
ac.norms['K8']=Q8-Q6*Z2+Q4*(Z2**2-Z4)+Q2*(-Z2**3+2*Z2*Z4-Z6)
ac.norms['EK6']=EQ6-EQ4*Z2-Q4*EZ2+EQ2*(Z2**2-Z4)+Q2*(2*Z2*EZ2-EZ4)
# Fixed cutoff powers, expanded before vacuum normalization.
@lru_cache(None)
def rawcut(name,iv=0,idd=0):
 k=name.rstrip('0123456789');n=int(name[len(k):]);der=ac.DERIV[iv,idd]
 if n>=7:return {0:ac.ms.pol(n,k,der,0)}
 pmin=-(n//2);pmax=3 if n<=3 else 2 if n==4 else 1
 return {p:ac.ms.pol(n,k,der,p) for p in range(pmin,pmax+1)}
ac.rawcut=rawcut
K60=ac.f('K6',0);K81=ac.f('K8',1);EK60=ac.f('EK6',0)
l6=-2*K60-4*v*s.diff(K60,v)+2*v*EK60
h8=K81-2*ac.Q20*ac.b7-4*ac.K40*ac.b5-6*K60*ac.b3-ac.l2*ac.h6-ac.l4*ac.h4+l6
needed={
 'alpha':s.diff(ac.b3,v,3)/6,
 'beta':s.diff(ac.b3,v,2,d)/2,
 'gamma':s.diff(ac.b3,v,d,2)/2,
 'Phi':s.diff(ac.b5,v,2)/2,
 'Psi':s.diff(ac.b5,v,d),
 'Omega':s.diff(ac.b7,v),
 'Qnew':-2*s.diff(ac.h4,d,2),
 'Pnew':-4*s.diff(ac.h6,d),
 'Knew':-4*h8,
}
def requirements(expr):
 fs=set()
 for x in expr.atoms(s.Derivative):
  name=str(x.expr.func);iv=dict(x.variable_count).get(v,0);idd=dict(x.variable_count).get(d,0)
  if name.endswith(('_f','_l')):fs.add((name.rsplit('_',1)[0],int(iv),int(idd)))
 for x in expr.atoms(s.Function):
  name=str(x.func)
  if name.endswith(('_f','_l')):fs.add((name.rsplit('_',1)[0],0,0))
 raw=set()
 for stem,iv,idd in fs:
  rr=s.diff(ac.norms[stem],v,iv,d,idd)
  for x in rr.atoms(s.Derivative):
   co=dict(x.variable_count);name=str(x.expr.func)
   if name in ac.rawf:raw.add((name,int(co.get(v,0)),int(co.get(d,0))))
  for x in rr.atoms(s.Function):
   if str(x.func) in ac.rawf:raw.add((str(x.func),0,0))
 return sorted((name+'_'+ac.DERIV[iv,idd] for name,iv,idd in raw),key=lambda k:(int(''.join(filter(str.isdigit,k.split('_')[0]))),k))
# Exact coefficient-directed cutoff convolutions (validated against old expansions).
import targeted_series
targeted_series.install()

if __name__=='__main__':
 which=sys.argv[1:] or list(needed)
 if '--requirements' in which:
  out={name:requirements(ex) for name,ex in needed.items()}
  missing=sorted(set(t for vals in out.values() for t in vals if not (ROOT/(t+'_negative.json')).exists()),key=lambda k:(int(''.join(filter(str.isdigit,k.split('_')[0]))),k))
  (ROOT/'C7_raw_requirements.json').write_text(json.dumps({'all':out,'missing':missing},indent=2))
  print('\n'.join(missing))
 else:
  for name in which:
   try:ac.betaexpr(needed[name],name)
   except FileNotFoundError as e:print('MISSING',name,str(e),flush=True)
