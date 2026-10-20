"""Independent exact arithmetic, shuffle-cache, and archived-integral checks."""
from pathlib import Path
import json,sys,random,time
import sympy as s
from hyperlog_core import *
from factored_field import field
ROOT=Path(__file__).resolve().parent
ARCH=ROOT.parent/'archive/LRI_1d_complete/stages/C6_integrals/reproducibility'
# A saved cached shuffle must survive all endpoint reductions.
from itertools import product
snap={}
for n in range(1,7):
 for ww in product((0,1),repeat=n):
  for k in range(n+1):
   key=(ww[:k],ww[k:]);snap[key]=shuffle(*key).copy()
for n in range(1,7):
 for ww in product((0,1),repeat=n):scaled_phi(ww);phi(ww)
assert all(shuffle(*k)==val for k,val in snap.items())
# Rational primitive identities with polynomial spectator cancellations.
for R,word in [((u+v)/v,()),((u**2-v**2)/(u+e),()),((u+v)**3/((u-e)**2*(u+v)),(-e,)),((e+v)*(e+w)/(u+e)**3,(v+e,-e))]:
 ant=integrate_rat(R,word,1);audit_primitive(ant,R,word,1)
 df=differentiate(ant,1);addto(df,word,-R);assert not clean(df)
# Saved raw expression equality is in QQ(e), word by word.
def rd(p):
 out={}
 for w,l,c in json.loads(p.read_text()):
  key=(tuple(w),tuple(l));addto(out,key,K.from_expr(c))
 return clean(out)
checks={}
for name in sys.argv[1:] or ['Q4_v']:
 a,b=rd(ROOT/(name+'_negative.json')),rd(ARCH/(name+'_negative.json'))
 diff={key:a.get(key,K.zero)-b.get(key,K.zero) for key in a.keys()|b.keys()}
 nonzero=clean(diff)
 checks[name]={'exact_match':not nonzero,'new_terms':len(a),'old_terms':len(b),'difference_terms':len(nonzero)}
 print(name,checks[name],flush=True)
 assert not nonzero,name
print('PASS arithmetic, endpoint regularization, cache immutability, and selected raw data',flush=True)
(ROOT/'backend_checks.json').write_text(json.dumps(checks,indent=2))
