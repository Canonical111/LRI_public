"""Exact monomial substitution and cached modular nondivisibility filters.
Modular tests only reject a divisor; accepted cancellations use exact division.
"""
from functools import lru_cache
from math import comb
import hyperlog_core as hc
import factored_field as ff
from factored_field import Frac
from sympy.polys.domains import QQ
OLD_PSUB=hc.psub
OLD_SUB=hc.sub
COUNTS={'psub_fast':0,'psub_fallback':0,'sub_fast':0,'sub_fallback':0,'mod_spec':0}

def psub(p,idx,a,order=0):
 if a.denf or len(a.numer)>1:
  COUNTS['psub_fallback']+=1;return OLD_PSUB(p,idx,a,order)
 COUNTS['psub_fast']+=1
 if not a:
  return hc.K(hc.K.ring.from_dict({tuple(0 if i==idx else d for i,d in enumerate(mon)):c for mon,c in p.items() if mon[idx]==order}))
 (am,ac),=a.numer.items();nzs=[(j,k) for j,k in enumerate(am) if k];out={}
 for mon,c in p.items():
  n=mon[idx]
  if n<order:continue
  m=list(mon);m[idx]=0;k=n-order
  for j,d in nzs:m[j]+=k*d
  key=tuple(m);val=c*comb(n,order)*(ac**k)
  out[key]=out.get(key,QQ.zero)+val
 return hc.K(hc.K.ring.from_dict({m:c for m,c in out.items() if c}))

def sub(r,idx,a):
 r=hc.K(r)
 if a.denf or len(a.numer)>1:
  COUNTS['sub_fallback']+=1;return OLD_SUB(r,idx,a)
 COUNTS['sub_fast']+=1
 n=psub(r.numer,idx,a).numer;ds={};scalar=QQ.one
 for fac,m in r.denf.items():
  f=psub(fac,idx,a).numer
  if not f:raise ZeroDivisionError
  if f.is_ground:
   scalar*=f.get((0,)*hc.K.ngens,QQ.zero)**m
  else:
   lc=f.LC;scalar*=lc**m;f=f.quo_ground(lc);ds[f]=ds.get(f,0)+m
 n=n.quo_ground(scalar)
 n,ds=ff.cancel_factors(n,ds)
 return Frac(hc.K,n,ds)

VALUES=(37,101,211,307,419,509,613,701,809,907,1009,1103,1201,1301,1409,1511)
PRIME=1000000007
@lru_cache(maxsize=100000)
def mon_value(mon,idx):
 v=1
 for j,n in enumerate(mon):
  if j!=idx and n:v=v*pow(VALUES[j],n,PRIME)%PRIME
 return v
@lru_cache(maxsize=10000)
def inverse(d):return pow(d,-1,PRIME)
@lru_cache(maxsize=150)
def modular_coeffs(p,idx):
 COUNTS['mod_spec']+=1
 degree=max((mon[idx] for mon in p),default=0);cs=[0]*(degree+1)
 for mon,c in p.items():
  dd=int(c.denominator)%PRIME
  if not dd:return None
  val=int(c.numerator)%PRIME*inverse(dd)%PRIME*mon_value(mon,idx)%PRIME
  cs[mon[idx]]=(cs[mon[idx]]+val)%PRIME
 return cs,VALUES,PRIME

def install():
 hc.psub=psub;hc.sub=sub;ff.modular_coeffs=modular_coeffs

if __name__=='__main__':
 import random,time,json
 from pathlib import Path
 random.seed(99871);start=time.time();tests=0
 for j in range(180):
  poly=hc.K.zero
  for k in range(8):
   v=hc.K(random.randint(-5,5))
   for i in range(4):v*=hc.GEN[i]**random.randint(0,2)
   poly+=v
  r=poly/(hc.e+hc.u+hc.v+1)**2/(hc.u-hc.w-2*hc.e)
  idx=1;a=random.choice([hc.K.zero,hc.v,hc.K.one,-2*hc.e])
  try:x=OLD_SUB(r,idx,a)
  except ZeroDivisionError:continue
  y=sub(r,idx,a);assert not x-y
  for order in [0,1,2]:
   assert OLD_PSUB(poly.numer,idx,a,order)==psub(poly.numer,idx,a,order)
  tests+=1
 d={'test':'exact substitution versus original','cases':tests,'seconds':time.time()-start,'counts':COUNTS}
 Path(__file__).parent.parent.joinpath('acceleration_checks.json').write_text(json.dumps(d,indent=2));print(d)
