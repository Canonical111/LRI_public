"""Full endpoint / volume ordered integrals. All log constants are retained.
Sources, complete stages and endpoint coefficients are atomically checkpointed.
"""
import os,json,time,gc,sys,hashlib,heapq
from pathlib import Path
sys.setrecursionlimit(200000)
import install_fastq;install_fastq.install_domain()
import hyperlog_core as hc
import native_poly;native_poly.install()
import exact_acceleration;exact_acceleration.install()
import native_linear;native_linear.install()
import native_mod;native_mod.install()
import native_fused;native_fused.install()
import fast_exact_text;fast_exact_text.install()
from hyperlog_core import *
import safe_parse;safe_parse.install(K)
import run_moment as rm
import ordered_moments as om
import factored_field as ff
ROOT=Path(__file__).resolve().parent.parent

def dump(path,expr):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix('.tmp')
 items=expr.items() if isinstance(expr,dict) else expr
 with tmp.open('w') as f:
  for (ww,ll),c in items:
   if c:f.write(json.dumps([[list(map(str,w)) for w in ww],list(ll),str(c)],separators=(',',':'))+'\n')
 tmp.replace(path)

def load(path):
 out=[]
 for line in path.open():
  ww,ll,c=json.loads(line)
  out.append(((tuple(tuple(rm.parseK(a) for a in w) for w in ww),tuple(ll)),rm.parseK(c)))
 return out

def clear():
 for fun in [hc.apart,hc.integrate_basis,hc._pc,hc.fibrate,hc.endpoint_fibrate,hc.local_gpl,hc.audit_basis,hc.shuffle,rm.parseK,ff.lininfo,ff.modular_coeffs,ff.divide_linear_cached]:fun.cache_clear()
 native_poly.encoded.cache_clear();gc.collect()
 import ctypes
 ctypes.CDLL(None).malloc_trim(0)

def blocks(n,kind):
 absolute=kind.startswith('E');Q=kind.endswith('Q')
 N=n if absolute else n-1
 Xs=[i*e+GEN[i+1] for i in range(n)] if absolute else [K.zero]+[i*e+GEN[i] for i in range(1,n)]
 act=0 if absolute else 1
 same=[i for i in range(n) if (i-act)%2==0 and i!=act]
 opp=[i for i in range(n) if (i-act)%2]
 def ws(indices):
  W=K.one
  for k,i in enumerate(indices):
   for j in indices[k+1:]:W*=(Xs[j]-Xs[i])**(2*(-1)**(i+j))
  return W if absolute else W*(1-Xs[-1])
 out=[]
 if absolute and n%2:
  assert not Q;out.append(('poly',K.zero,0,ws(list(range(1,n)))))
 for p in opp:
  rem=[i for i in range(n) if i not in [act,p]]
  C=ws(rem);root=Xs[p]-(0 if absolute else e)
  dd=sum([2/(Xs[p]-Xs[j]) for j in same]+[-2/(Xs[p]-Xs[j]) for j in opp if j!=p],K.zero)
  if Q:
   D=C*sum(((-1)**(i+1)*Xs[i] for i in rem),K.zero)
   simple=C*(-1 if absolute else 1)+D*dd
  else:D=C;simple=C*dd
  if D:out.append(('pole',root,2,D))
  if simple:out.append(('pole',root,1,simple))
 return out,N

def first(bl,ins,N):
 kin,root,p,C=bl;loc={};st=time.time()
 for j,((words,logs),cf) in enumerate(ins.items()):
  audit_basis(kin,root,p,words[0],1)
  for wa,c in integrate_basis(kin,root,p,words[0],1).items():
   for wb,cb in endpoint_value(c,wa,1,GEN[2]).items():
    for wf,mu in endpoint_fibrate(wb,2).items():
     for wn,mv in shuffle(wf,words[1]).items():
      keys=list(words);keys[0]=();keys[1]=wn
      addto(loc,(tuple(keys),logs),cf*cb*mu*mv)
   for wb,cb in endpoint_value(c,wa,1,K.zero,lower=True).items():
    assert not wb;keys=list(words);keys[0]=();addto(loc,(tuple(keys),logs),-cf*cb)
  if j%200==0:print('FIRST',j,len(ins),len(loc),time.time()-st,flush=True)
 return {key:c*C for key,c in clean(loc).items()}

def sources(n,kind,der):
 folder=ROOT/f'{kind}{n}_{der}';folder.mkdir(exist_ok=True)
 ins,N=rm.initial(n,kind,der,kernel=False)
 bs,N=blocks(n,kind)
 records=[]
 for i,bl in enumerate(bs):
  p=folder/f'b{i:02}/stage1.jsonl'
  if not p.exists():
   expr=first(bl,ins,N);dump(p,expr);del expr
  records.append({'block':f'b{i:02}','rows':sum(1 for _ in p.open()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pole':str(bl[1]),'order':bl[2]})
  print('SOURCE',kind,n,der,records[-1],flush=True);clear()
 (folder/'manifest.json').write_text(json.dumps({'n':n,'kind':kind,'deriv':der,'N':N,'blocks':records,'full_periods':True},indent=2))

def one_stage(items,idx,N,n):
 groups={};dirty=set();st=time.time();rm.parseK.cache_clear()
 def put(key,val):
  if not val:return
  g=groups.setdefault(key,{});dirty.add(key);den=frozenset(val.denf.items())
  num=g.get(den,K.ring.zero)+val.numer
  if num:g[den]=num
  else:
   g.pop(den,None)
   if not g:groups.pop(key,None)
 def normalize(final=False):
  nonlocal groups,dirty
  out={};seq=0
  keys=tuple(groups) if final else tuple(dirty)
  for key in keys:
   g=groups.pop(key,None)
   if g is None:continue
   heap=[]
   for den,num in g.items():
    nn,dd=ff.cancel_factors(num,dict(den)) if key in dirty or len(g)>1 else (num,dict(den))
    if nn:
     val=ff.Frac(K,nn,dd);heapq.heappush(heap,(len(nn)+len(dd),seq,val));seq+=1
   while len(heap)>1:
    _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);v=a+b
    if v:heapq.heappush(heap,(len(v.numer)+len(v.denf),seq,v));seq+=1
   if heap:
    v=heap[0][2]
    if final:out[key]=v
    else:groups[key]={frozenset(v.denf.items()):v.numer}
  dirty=set();return out
 for j,((words,logs),R) in enumerate(items):
  active=words[idx-1];pp,po=apart(R,idx)
  for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
   audit_basis(kin,a,p,active,idx)
   for wa,c in integrate_basis(kin,a,p,active,idx).items():
    bound=GEN[idx+1] if idx<N else 1-(n-1)*e
    for wb,cb in endpoint_value(c,wa,idx,bound).items():
     if idx<N:
      for wf,mu in endpoint_fibrate(wb,idx+1).items():
       for wn,mv in shuffle(wf,words[idx]).items():
        keys=list(words);keys[idx-1]=();keys[idx]=wn;put((tuple(keys),logs),pref*cb*mu*mv)
     else:
      keys=[()]*N;keys[-1]=wb;put((tuple(keys),logs),pref*cb)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[idx-1]=();put((tuple(keys),logs),-pref*cb)
  items[j]=None
  if (j+1)%250==0:normalize()
  if j%100==0:print('ROW',idx,j+1,len(items),len(groups),time.time()-st,flush=True)
 out=normalize(True);print('STAGE_DONE',idx,len(out),time.time()-st,flush=True);return out

def worker(tag,block,stop=None):
 folder=ROOT/tag/block;meta=json.loads((folder.parent/'manifest.json').read_text());N=meta['N'];n=meta['n']
 for idx in range(2,min(N,stop or N)+1):
  p=folder/f'stage{idx}.jsonl'
  if p.exists():continue
  rows=load(folder/f'stage{idx-1}.jsonl');ans=one_stage(rows,idx,N,n);dump(p,ans);del rows,ans;clear()
 if stop and stop<N:return
 if not (folder/'negative.json').exists():
  rows=load(folder/f'stage{N}.jsonl');out=[]
  for (ww,ll),c in rows:
   assert not any(ww[:-1]);word=[int((a/e).as_expr()) for a in ww[-1]]
   trailing=0
   for a in reversed(word):
    if a:break
    trailing+=1
   for j in range(trailing+1):out.append([word[:-j] if j else word,list(ll)+[1]*j,str(c/factorial(j))])
  (folder/'negative.json').write_text(json.dumps(out));print('NEGATIVE',tag,block,len(out),flush=True)
 if not (folder/'coefficient_0.expr').exists():
  import sympy as s
  from finite_extract_fast import extract_finite
  result=extract_finite(json.loads((folder/'negative.json').read_text()),n-1)
  tmp=folder/'coefficient_0.tmp';tmp.write_text(s.sstr(result,order='none'));tmp.replace(folder/'coefficient_0.expr')
 if not (folder/'result.json').exists():
  (folder/'result.json').write_text(json.dumps({'tag':tag,'block':block,'complete':True,'full_constant_periods':True,'raw_sha256':hashlib.sha256((folder/'negative.json').read_bytes()).hexdigest(),'target':'finite constant only'}));print('COMPLETE_BLOCK',tag,block,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--n',type=int);p.add_argument('--kind');p.add_argument('--deriv');p.add_argument('--sources',action='store_true');p.add_argument('--tag');p.add_argument('--block');p.add_argument('--stop',type=int);a=p.parse_args()
 if a.sources:sources(a.n,a.kind,a.deriv)
 else:worker(a.tag,a.block,a.stop)
