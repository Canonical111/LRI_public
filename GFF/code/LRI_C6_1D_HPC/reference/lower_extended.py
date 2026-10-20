import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,pickle,json,time
from pathlib import Path
import numpy as np,mpmath as mp
sys.path.insert(0,str(Path(__file__).resolve().parent/'lri_numerical_resolution/verification/source'))
import ising_five_loop as old
root=Path(__file__).resolve().parent
# Copy the existing interpolation engine, increasing retained epsilon order by one.
import inspect
src=inspect.getsource(old.qweights.__wrapped__)
src=src.replace('@lru_cache(None)\n','').replace('4 if log else 5','5 if log else 6').replace('(5,N+1)','(6,N+1)').replace('range(5)','range(6)')
ns=old.__dict__;exec(src,ns);old.qweights=old.lru_cache(None)(ns['qweights'])
src=inspect.getsource(old.integrate).replace('(2,5)','(2,6)').replace('maxp=5-L+p','maxp=6-L+p').replace('range(5)','range(6)')
exec(src,ns)
old.SECTOR_CACHE={}
for n in [3,4,5]:
 f=root/f'sectors{n}.pkl'
 if f.exists():old.SECTOR_CACHE[n]=pickle.load(open(f,'rb'))
 else:
  gg=old.graphs(n);old.SECTOR_CACHE[n]=old.sectors(n,gg);pickle.dump(old.SECTOR_CACHE[n],open(f,'wb'))
 print('prepared',n,len(old.SECTOR_CACHE[n][1]),flush=True)
for N in map(int,sys.argv[1:]):
 for cut in ['maxgap','span']:
  fn=root/f'lower6_{cut}_{N}.json'
  if fn.exists():continue
  out={}
  for L in [2,3,4]:
   out[L]=[{str(k):str(v)for k,v in a.items()}for a in old.integrate(L+1,N,cut)]
  fn.write_text(json.dumps(out,indent=2))
