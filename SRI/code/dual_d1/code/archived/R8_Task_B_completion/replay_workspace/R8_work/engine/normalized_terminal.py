"""Exploit exact scalar linearity before caching the terminal functionals."""
import time
from functools import lru_cache
import scaled_b as sb
from hyperlog_core import *
Q=sb.F
@lru_cache(maxsize=40000)
def parts(co,N):
 num,den=sb.rparts(co,N)
 if not num:return Q(0),(),den
 scalar=next((v for v in num if v),Q(0))
 if not scalar:return Q(0),(),den
 return scalar,tuple(v/scalar for v in num),den

def last_two(items,n):
 sb.tb.br.rr.rm.parseK.cache_clear();N=n-2;idx=N-1;total=Q(0);count=0;st=time.time()
 demands=tuple((p,r) for p in range(-(n//2-1),0) for r in (0,1));negative=[Q(0)]*len(demands)
 for j,((words,logs),R) in enumerate(items):
  assert not logs and not any(words[:idx-1]);active=words[idx-1];pp,po=apart(R,idx)
  bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
  def endpoint(c,wa,sign):
   nonlocal total,count
   scale,num,den=parts(c,N)
   if not scale:return
   H=sb.mt.canon((sb.aword_scaled(wa,N),sb.aword_scaled(words[N-1],N)))
   total+=sign*scale*sb.eval_parts(num,den,H,n)
   nn=sb.negative_parts(num,den,H,n,demands)
   for k,v in enumerate(nn):negative[k]+=sign*scale*v
   count+=1
  for kind,root,power,pref in bases:
   audit_basis(kind,root,power,active,idx)
   for wa,c in integrate_basis(kind,root,power,active,idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[N]).items():endpoint(pref*cb,wb,1)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;endpoint(pref*cb,(),-1)
  items[j]=None
  if j%200==0:print('NORMALIZED_FINAL',j+1,len(items),'sum',str(total),'seconds',time.time()-st,flush=True)
 return total,count,negative

def install():sb.last_two_scaled=last_two;sb.tb.last_two=last_two
