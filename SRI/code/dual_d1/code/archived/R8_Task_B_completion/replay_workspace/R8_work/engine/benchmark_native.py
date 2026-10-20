from pathlib import Path
import random,time,json
import task_b as tb
import native_poly as np
from hyperlog_core import K
from sympy.polys.domains import QQ
rng=random.Random(987341);checks=[]
np.NATIVE_PRODUCT_THRESHOLD=0
for na,nb in [(30,12),(100,12),(300,12),(600,12),(300,30),(100,100),(600,50)]:
 def poly(n):
  d={}
  while len(d)<n:
   m=[0]*K.ngens
   for j in (4,5,6):m[j]=rng.randrange(12)
   d[tuple(m)]=QQ(rng.randrange(-1000,1000))
  return K.ring.from_dict(d)
 a,b=poly(na),poly(nb)
 st=time.time();c=np.ORIGINAL(a,b);t1=time.time()-st
 st=time.time();d=np.multiply(a,b);t2=time.time()-st
 assert c==d
 z={'na':na,'nb':nb,'python_seconds':t1,'GMP_seconds':t2,'equal':True};checks.append(z);print(z,flush=True)
(tb.ROOT/'native_threshold_benchmark.json').write_text(json.dumps(checks,indent=2))
