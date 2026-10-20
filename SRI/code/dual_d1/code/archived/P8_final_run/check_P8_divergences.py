"""Fresh rational divergent jets from the full P8 terminal source.
Independent asymptotic integration of polynomial parts; no finite P8 read.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
from math import factorial
import json,sys,time,hashlib,concurrent.futures
sys.path.insert(0,'/mnt/data/P8_final_run')
from linear_boundary import shiftweight
ROOT=Path('/mnt/data/P8_final_run/F3_six_kink_completion/P8_terminal_fibration')
@lru_cache(maxsize=250000)
def g0(w,n,k):
 if k<0:return F(0)
 if not w:return F(int(n==0 and k==0))
 if n==0:return F(1,factorial(k)) if k==len(w) else F(0)
 if k>len(w)-1:return F(0)
 return -sum(F(factorial(k+h),factorial(k)*n**(h+1))*F(w[0])**r*g0(w[1:],n-r,k+h) for h in range(len(w)-k) for r in range(n+1))
@lru_cache(maxsize=30000)
def jet(w,d):
 out={}
 # two powers from (1-eps*(7+r)); integration of r^(d-n)*log^k r
 for degree,kappa,fac in [(d,0,F(1)),(d,1,F(-7)),(d+1,1,F(-1))]:
  for n in range(degree+1):
   exponent=degree-n+1
   for k in range(len(w)+1):
    c=g0(w,n,k)*fac
    if not c:continue
    for j in range(k+1):
     b=c*F((-1)**j*factorial(k),factorial(k-j)*exponent**(j+1))
     for ep in (-3,-2,-1):
      for ell in range(k-j+1):
       v=b*shiftweight(exponent,k-j,kappa,7,ep,ell)
       if v:out[ep,ell]=out.get((ep,ell),F(0))+v
 return tuple((key,val) for key,val in out.items() if val)
def worker(i):
 st=time.time();folder=ROOT/'divergence_replay';folder.mkdir(exist_ok=True);fp=folder/f'b{i:03d}.json'
 if fp.exists():return i
 apart=json.loads((ROOT/'prefactor_apart.json').read_text());pol=[]
 for row in apart:
  pp={}
  for kind,a,d,z,c in row:
   if kind=='poly' and not any(z):pp[d]=pp.get(d,F(0))+F(c)
  pol.append(tuple(pp.items()))
 groups={};src=ROOT/f'b{i:03d}.tsv';rows=0
 for line in src.open():
  key,pid,cs=line.rstrip().split('\t');terms=pol[int(pid)];rows+=1
  if not terms or not key.endswith(',[],[0,0,0,0]]'):continue
  vals=groups.setdefault(key,[F(0),F(0),F(0)]);c=F(cs)
  for degree,a in terms:vals[degree]+=a*c
 out={}
 for key,values in groups.items():
  if not any(values):continue
  w,ll,z=json.loads(key);w=tuple(w)
  for d,c in enumerate(values):
   if not c:continue
   for pair,v in jet(w,d):out[pair]=out.get(pair,F(0))+c*v
 result={'complete':True,'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'input_rows':rows,'values':{f'{p},{m}':str(v) for (p,m),v in out.items() if v},'seconds':time.time()-st,'finite_residue_not_used':True}
 fp.write_text(json.dumps(result,indent=2));print('DIV_BLOCK',i,result['seconds'],flush=True);return i
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(worker,range(256)))
 out={}
 for i in range(256):
  record=json.loads((ROOT/'divergence_replay'/f'b{i:03d}.json').read_text())
  for k,v in record['values'].items():out[k]=out.get(k,F(0))+F(v)
 result={'complete':True,'all256_source_bins':True,'dimensionless_boundary':{k:str(v) for k,v in sorted(out.items()) if v},'no_target_divergence_used':True}
 (ROOT/'divergence_replay/total.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
