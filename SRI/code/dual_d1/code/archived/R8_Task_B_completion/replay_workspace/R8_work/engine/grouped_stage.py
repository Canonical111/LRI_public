"""Exact denominator-grouped assembly of an ordered integration.

All elementary primitives are unchanged and differentiated exactly. Terms
with identical word and denominator are added at numerator level before
performing cancellation; this is ordinary rational linearity.
"""
import heapq,time
import task_b as tb
import factored_field as ff
from hyperlog_core import *
ORIGINAL=tb.one_stage

def one_stage(items,idx,N):
 groups={};dirty=set();st=time.time()
 tb.br.rr.rm.parseK.cache_clear()
 def put(key,val):
  if not val:return
  g=groups.setdefault(key,{})
  dirty.add(key)
  den=frozenset(val.denf.items())
  num=g.get(den,K.ring.zero)+val.numer
  if num:g[den]=num
  else:
   g.pop(den,None)
   if not g:groups.pop(key,None)
 def normalize(final=False):
  nonlocal groups,dirty
  new={};out={};counter=0
  while groups:
   key,g=groups.popitem()
   heap=[]
   for den,num in g.items():
    n,d=(num,dict(den)) if key not in dirty and len(g)==1 else ff.cancel_factors(num,dict(den))
    if n:
     val=ff.Frac(K,n,d);heapq.heappush(heap,(len(n)+len(d),counter,val));counter+=1
   while len(heap)>1:
    _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);v=a+b
    if v:heapq.heappush(heap,(len(v.numer)+len(v.denf),counter,v));counter+=1
   if heap:
    v=heap[0][2]
    if final:out[key]=v
    else:new[key]={frozenset(v.denf.items()):v.numer}
  groups=new;dirty.clear()
  return out
 for j,((words,logs),R) in enumerate(items):
  assert not logs;active=words[idx-1];pp,po=apart(R,idx)
  bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
  for kind,root,power,pref in bases:
   audit_basis(kind,root,power,active,idx)
   for wa,c in integrate_basis(kind,root,power,active,idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
     for wf,mu in endpoint_fibrate(wb,idx+1).items():
      for wn,mv in shuffle(wf,words[idx]).items():
       keys=list(words);keys[idx-1]=();keys[idx]=wn
       put((tuple(keys),()),pref*cb*mu*mv)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[idx-1]=()
     put((tuple(keys),()),-pref*cb)
  items[j]=None  # The ordered input list is consumed; the exact source file is unchanged.
  if (j+1)%300==0:
   normalize()
   print('GROUP_COMPACT',idx,j+1,'words',len(groups),flush=True)
  if j%100==0:print('GROUPED_ROW',idx,j+1,len(items),'nonzero_word_groups',len(groups),'seconds',time.time()-st,flush=True)
 out=normalize(final=True)
 print('GROUPED_STAGE_DONE',idx,'input',len(items),'output',len(out),'seconds',time.time()-st,flush=True)
 return out

def install(from_stage=4):
 tb.one_stage=lambda items,idx,N:one_stage(items,idx,N) if idx>=from_stage else ORIGINAL(items,idx,N)
