"""Exact gapped ordered integrals in rational functions and hyperlogarithms.
Produces finite-cutoff responses, not a zeta-value ansatz.
"""
from hyperlog_core import *
from pathlib import Path
import json,time,sys,os

AUDIT_COUNTS={'antiderivatives':0}

def multiply(A,B,N):
 out={}
 for (ww,logs),ca in A.items():
  for (vv,ls),cb in B.items():
   states={((),tuple(sorted(logs+ls))):1}
   for i in range(N):
    nxt={}
    for (prefix,l),m in states.items():
     for z,n in shuffle(ww[i],vv[i]).items():nxt[prefix+(z,),l]=m*n
    states=nxt
   for key,m in states.items():addto(out,key,ca*cb*m)
 return clean(out)

def log_distance(i,j,N):
 ww=[()]*N;out={};c=(j-i)*e
 if i:
  ww[i-1]=(GEN[j]+c,);out[tuple(ww),()]=K.one;ww[i-1]=()
 ww[j-1]=(-c,);out[tuple(ww),()]=K.one
 ww[j-1]=();out[tuple(ww),(j-i,)]=K.one
 return out

def make_initial(n,kind):
 N=n-1;Xs=[K.zero]+[j*e+GEN[j] for j in range(1,n)]
 W=K.one
 for i in range(n):
  for j in range(i+1,n):W*= (Xs[j]-Xs[i])**(2*(-1)**(i+j))
 W*=1-Xs[-1]
 if kind.startswith('Q'):W*=sum((Xs[i+1]-Xs[i] for i in range(0,n,2)),K.zero)
 base={(tuple([()]*N),()):W}
 if kind.endswith('base'):return base
 insert={}
 for i in range(n):
  for j in range(i+1,n):
   L=log_distance(i,j,N)
   if kind.endswith('v') or kind.endswith('vv'):
    for key,c in L.items():addto(insert,key,c*2*(-1)**(i+j))
   elif kind.endswith('delta'):
    for key,c in multiply(L,L,N).items():addto(insert,key,c*(-1)**(i+j))
   else:raise ValueError(kind)
 if kind.endswith('vv'):insert=multiply(insert,insert,N)
 return multiply(base,clean(insert),N)

def dump(path,expr):
 data=[]
 for (ww,logs),c in expr.items():data.append(([list(map(str,w)) for w in ww],list(logs),str(c)))
 Path(path).write_text(json.dumps(data))

def six_first_stage():
 N=5;Xs=[K.zero]+[j*e+GEN[j] for j in range(1,6)]
 plus=[K.zero,Xs[2],Xs[4]];neg=[Xs[3],Xs[5]]
 out=[]
 for p in plus:
  rem=[x for x in plus if x!=p]
  W4=(rem[1]-rem[0])**2*(neg[1]-neg[0])**2
  for xp in rem:
   for yn in neg:W4/=(xp-yn)**2
  W4*=1-Xs[5]
  dip=sum(neg,K.zero)-sum(rem,K.zero)
  D=dip*W4
  root=p-e;keys=tuple([()]*N)
  out.append(((keys,()),-D/(GEN[2]-root)))
  out.append(((keys,()),-D/root))
  Cs=[W4]+[W4*dip*2/(p-y) for y in neg]+[-W4*dip*2/(p-x) for x in rem]
  for ww,m in fibrate((root,),2).items():
   ks=[()]*N;ks[1]=ww
   for C in Cs:out.append(((tuple(ks),()),C*m))
 return out

def calc(n,kind,root=Path(__file__).resolve().parent):
 N=n-1;start=time.time();startidx=1
 if n==6 and kind=='Qbase':expr=six_first_stage();startidx=2
 else:expr=make_initial(n,kind)
 print('initial',n,kind,len(expr),time.time()-start,flush=True)
 for idx in range(startidx,n):
  out={};items=list(expr.items()) if isinstance(expr,dict) else expr
  for j,((words,logs),R) in enumerate(items):
   active=words[idx-1];ant=integrate_rat(R,active,idx)
   if os.environ.get('LRI_AUDIT_PRIMITIVES') == '1':
    residual=differentiate(ant,idx)
    addto(residual,active,-R)
    assert not clean(residual), ('Primitive derivative check failed',n,kind,idx,j)
    AUDIT_COUNTS['antiderivatives']+=1
   if idx<N:
    bound=GEN[idx+1]
    for wa,c in ant.items():
     for wb,cb in endpoint_value(c,wa,idx,bound).items():
      for wf,mu in endpoint_fibrate(wb,idx+1).items():
       for wn,mv in shuffle(wf,words[idx]).items():
        keys=list(words);keys[idx-1]=();keys[idx]=wn
        addto(out,(tuple(keys),logs),cb*mu*mv)
     low=endpoint_value(c,wa,idx,K.zero,lower=True)
     for wb,cb in low.items():
      assert not wb
      keys=list(words);keys[idx-1]=()
      addto(out,(tuple(keys),logs),-cb)
   else:
    bound=1-N*e
    for wa,c in ant.items():
     for wb,cb in endpoint_value(c,wa,idx,bound).items():
      assert all(not a.diff(GEN[idx]) for a in wb)
      keys=[()]*N;keys[idx-1]=wb
      addto(out,(tuple(keys),logs),cb)
     for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
      assert not wb
      addto(out,(tuple([()]*N),logs),-cb)
   if j%10==0:print('stage',idx,'item',j+1,'/',len(items),'terms',len(out),'seconds',time.time()-start,flush=True)
  expr=clean(out)
  dump(root/f'{kind}{n}_stage{idx}.json',expr)
  print('stage done',idx,len(expr),time.time()-start,flush=True)
 rows=[]
 for (ww,logs),c in expr.items():
  assert all(not q for q in ww[:-1])
  word=ww[-1]
  assert all(not a.diff(GEN[i]) for a in word for i in range(1,n))
  assert all(sub(a,0,K.zero)==0 for a in word)
  aa=[int((a/e).as_expr()) for a in word]
  assert not aa or aa[-1]!=0
  rows.append((aa,list(logs),str(c)))
 outpath=root/f'{kind}{n}_negative.json';outpath.write_text(json.dumps(rows))
 print('DONE',kind,n,'terms',len(rows),'seconds',time.time()-start,'audit',AUDIT_COUNTS,flush=True)
 return rows

if __name__=='__main__':calc(int(sys.argv[1]),sys.argv[2])
