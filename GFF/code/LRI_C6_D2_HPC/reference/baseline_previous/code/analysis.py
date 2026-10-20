"""Assembly and replicate-based errors, preserving all loop-jet covariance."""
from pathlib import Path
import json,importlib.util
import numpy as np
W=Path(__file__).resolve().parents[1]
def base_module(d):
 path=W/'baseline'/f'lri_C6_d{d}_complete_update'/('code/analyze_d3.py'if d==3 else 'reproduction/mom_analysis.py')
 spec=importlib.util.spec_from_file_location(f'base_d{d}',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
F={d:base_module(d).coefficients for d in (2,3)}
def jacobians(d,means):
 J={}
 for L,a in means.items():
  out=[]
  for j in range(len(a)):
   tmp={k:np.asarray(v,dtype=complex)for k,v in means.items()};tmp[L][j]+=1e-20j;out.append(F[d](tmp).imag/1e-20)
  J[L]=np.array(out).T
 return J

def evaluate(d,tag,write=True):
 raw={L:json.load(open(W/f'records/{tag}_d{d}_L{L}.json'))for L in (3,4,5,6)}
 ar={L:np.array(v['batches'])for L,v in raw.items()};means={L:a.mean(0)for L,a in ar.items()};J=jacobians(d,means)
 pieces={L:J[L]@np.cov(a,rowvar=False,ddof=1)@J[L].T/len(a)for L,a in ar.items()};cov=sum(pieces.values());coeff=F[d](means)
 out={'dimension':d,'tag':tag,'coefficients':coeff.tolist(),'sampling_se':np.sqrt(np.maximum(0,np.diag(cov))).tolist(),'covariance':cov.tolist(),'error_by_loop':{str(L):float(max(0,x[6,6])**.5)for L,x in pieces.items()},'means':{str(L):a.tolist()for L,a in means.items()},'jacobians':{str(L):a.tolist()for L,a in J.items()},'samples':{str(L):x['N']for L,x in raw.items()},'replicates':{str(L):len(ar[L])for L in ar},'quad_fallbacks':{str(L):x['quad_fallbacks']for L,x in raw.items()},'mp_fallbacks':{str(L):x['mp_fallbacks']for L,x in raw.items()}}
 if write:(W/f'verification/{tag}_d{d}_analysis.json').write_text(json.dumps(out,indent=2))
 return out
if __name__=='__main__':
 import sys
 for d in (2,3):
  try:
   v=evaluate(d,sys.argv[1]if len(sys.argv)>1 else'pilot');print(d,v['coefficients'],v['sampling_se'],'loops',v['error_by_loop'],flush=True)
  except FileNotFoundError as e:print(e)
