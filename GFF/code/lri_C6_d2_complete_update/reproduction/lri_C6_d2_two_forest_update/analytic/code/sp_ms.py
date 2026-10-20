"""UV MS counterterms of safely gamma-reducible graphs, in d=2.
External momentum is kept fixed through every quotient.  Missing cographs,
unsafe exceptional momentum configurations, and unsolved counterterms are
reported, never filled with zero. The 1-loop bare finite part differs from
the massive zero-momentum one; the recursive UV counterterm must agree.
"""
from sp_classify import inv,canon,F,Counter,nx,Path,json,itertools
from functools import lru_cache
import mpmath as mp
import sys,time
K=6
DPS=int(sys.argv[1])if len(sys.argv)>1 else 70
mp.mp.dps=DPS
root=Path(__file__).resolve().parents[1]
class Unsolved(Exception):pass

def reduce_fixed(edges,terminals):
 E=[(min(a,b),max(a,b),F(1,2),F(1,4))for a,b in edges];gam=Counter()
 while len(E)>1:
  groups={}
  for a,b,x,y in E:groups.setdefault((a,b),[]).append((x,y))
  pair=next((k for k,v in groups.items()if len(v)>1),None)
  if pair is not None:
   v=groups[pair];eta=(sum(x for x,y in v)-len(v)+1,sum(y for x,y in v))
   for x,y in v:gam[(1-x,-y)]+=1;gam[(x,y)]-=1
   gam[eta]+=1;gam[(1-eta[0],-eta[1])]-=1
   E=[e for e in E if e[:2]!=pair]+[(*pair,*eta)];continue
  adj={}
  for i,(a,b,x,y)in enumerate(E):adj.setdefault(a,[]).append(i);adj.setdefault(b,[]).append(i)
  v=next((v for v,idx in adj.items()if len(idx)==2 and v not in terminals),None)
  if v is None:raise Unsolved('not two-terminal series-parallel')
  i,j=adj[v];e1,e2=E[i],E[j];a=e1[1]if e1[0]==v else e1[0];b=e2[1]if e2[0]==v else e2[0]
  eta=(e1[2]+e2[2],e1[3]+e2[3]);E=[e for k,e in enumerate(E)if k not in(i,j)]
  if a==b:raise Unsolved('tadpole')
  if eta[0]>=1 and E:raise Unsolved('infrared-borderline internal line')
  E.append((min(a,b),max(a,b),*eta))
 if not E or set(E[0][:2])!=set(terminals):raise Unsolved('lost terminals')
 ga=tuple(sorted((x,y,v)for (x,y),v in gam.items()if v))
 if any(x<=0 and x.denominator==1 and y==0 for x,y,v in ga):raise Unsolved('identically singular gamma factor')
 return ga

def mpf(x):return mp.mpf(x.numerator)/x.denominator
@lru_cache(None)
def gamma_series(ga):
 lead=mp.mpf(1);power=0;logs=[mp.mpf(0)]*K
 for a,b,v in ga:
  B=mpf(b)
  if a.denominator==1 and a<=0:
   m=int(-a);power-=v;lead*=((-1)**m/(B*mp.factorial(m)))**v
   for k in range(1,K):logs[k]+=v*B**k*(mp.polygamma(k-1,1)/mp.factorial(k)+sum(mp.mpf(j)**(-k)for j in range(1,m+1))/k)
  else:
   A=mpf(a);lead*=mp.gamma(A)**v
   for k in range(1,K):logs[k]+=v*B**k*mp.polygamma(k-1,A)/mp.factorial(k)
 cs=[lead]
 for k in range(1,K):cs.append(sum(j*logs[j]*cs[k-j]for j in range(1,k+1))/k)
 return {power+k:v for k,v in enumerate(cs)}

def add(*xs):
 out={}
 for x in xs:
  for k,v in x.items():out[k]=out.get(k,mp.mpf(0))+v
 return out

def mul(x,y):
 out={}
 for k,v in x.items():
  for j,w in y.items():
   if -6<=k+j<=5:out[k+j]=out.get(k+j,mp.mpf(0))+v*w
 return out

def quo(edges,subs,term):
 vs={v for e in edges for v in e};par={v:v for v in vs}
 def find(v):
  while par[v]!=v:v=par[v]
  return v
 for s in subs:
  s=sorted(s)
  for v in s[1:]:par[find(v)]=find(s[0])
 out=[]
 for a,b in edges:
  if any(a in s and b in s for s in subs):continue
  a,b=find(a),find(b)
  if a==b:raise Unsolved('tadpole quotient')
  out.append((min(a,b),max(a,b)))
 tt=tuple(find(v)for v in term)
 if out and tt[0]==tt[1]:raise Unsolved('scaleless quotient')
 return out,tt

def subgraphs(edges):
 vs=sorted({v for e in edges for v in e});out=[]
 for n in range(2,len(vs)):
  for sub in itertools.combinations(vs,n):
   s=frozenset(sub);ee=[e for e in edges if set(e)<=s]
   if len(ee)!=2*(n-1):continue
   g=nx.Graph();g.add_nodes_from(s);g.add_edges_from(ee)
   if not nx.is_connected(g):continue
   mult=Counter(tuple(sorted(e))for e in ee)
   if any(mult[tuple(sorted(e))]==1 for e in nx.bridges(g)):continue
   out.append((s,ee))
 return out

def scale_external(x,L,ell):
 return mul(x,{k:(-mp.mpf(L)*ell/2)**k/mp.factorial(k) for k in range(K)})

C={};solved_meta={}
active=set()
def ct(edges):
 key=canon(edges)
 if key in C:return C[key]
 if key in active:raise RuntimeError('recursive self subgraph')
 active.add(key)
 try:
  g=nx.Graph(edges);blocks=list(nx.biconnected_components(g))
  if len(blocks)>1:
   arr=[]
   for s in blocks:
    ee=[e for e in edges if set(e)<=s]
    if len(ee)!=2*(len(s)-1):raise Unsolved('inhomogeneous articulation')
    arr.append(ct(ee))
   out={0:mp.mpf(1)}
   for a in arr:out=mul(out,a)
   C[key]=out;solved_meta[key]={'kind':'articulation_product'};return out
  deg=Counter(v for e in edges for v in e);ex=[v for v in deg if deg[v]<4];req={v for v in deg if deg[v]==2};ss=subgraphs(edges)
  vals=[]
  for term in itertools.combinations(sorted(ex),2):
   if not req<=set(term):continue
   try:
    ga=reduce_fixed(edges,term);raw=gamma_series(ga)
    # Terminal inheritance is essential for finite cograph coefficients.
    use=[]
    for s,ee in ss:use.append((s,ct(ee)))
    spin=[]
    def rec(ch,poss):
     if ch:spin.append(tuple(ch))
     for k,j in enumerate(poss):rec(ch+[j],[u for u in poss[k+1:]if len(use[j][0]&use[u][0])==0])
    rec([],list(range(len(use))))
    prepared=raw.copy(); scaled=scale_external(raw,len(edges)//2,mp.mpf(1))
    for sp in spin:
     subs=[use[i][0]for i in sp]
     # A spinney with no contracted loop left is not a proper preparation.
     keep=[e for e in edges if not any(set(e)<=s for s in subs)]
     if not keep:continue
     qe,qt=quo(edges,subs,term);gg=reduce_fixed(qe,qt);I=gamma_series(gg)
     Is=scale_external(I,len(qe)//2,mp.mpf(1))
     for i in sp:I=mul(I,use[i][1]);Is=mul(Is,use[i][1])
     prepared=add(prepared,I);scaled=add(scaled,Is)
    out={k:-v for k,v in prepared.items()if k<0}
    locality=max((abs(v-scaled.get(k,0)) for k,v in prepared.items()if k<0),default=0)
    if locality>mp.mpf(10)**(-DPS+15):raise RuntimeError(('nonlocal pole',edges,term,locality))
    vals.append((term,out,ga,len(spin),locality))
   except Unsolved:continue
  if not vals:raise Unsolved('no closed safe reduction and MS spinney')
  res=vals[0][1]
  error=max((abs(v-res.get(k,0))for _,vv,_,_,_ in vals for k,v in vv.items()),default=0)
  if error>mp.mpf(10)**(-DPS+15):raise RuntimeError(('routing dependence',edges,[(t,vv)for t,vv,_,_,_ in vals],error))
  C[key]=res;solved_meta[key]={'kind':'gamma_Rprime','routing_checks':len(vals),'max_routing_error':str(error),'terminals':vals[0][0], 'gamma':[[str(a),str(b),v]for a,b,v in vals[0][2]],'spinney_count':vals[0][3], 'maximum_locality_error':str(max(v[4]for v in vals))}
  return res
 finally:active.remove(key)

if __name__=='__main__':
 out=[];st=time.time()
 for row in inv['loops']:
  L=row['loop'];ok=[];failed=[];b=mp.mpf(0);c=mp.mpf(0)
  for g in row['graphs']:
   try:
    cp=ct([tuple(e)for e in g['edges']]);res=-cp.get(-1,0);bb=(-1)**(L+1)*L*mpf(F(g['weight4']))*res;cc=(-1)**(L+1)*L*mpf(F(g['weight2']))*res;b+=bb;c+=cc
    ok.append({'id':g['id'],'MS_counterterm':{str(k):str(v)for k,v in cp.items()},'b_contribution':str(bb),'c_contribution':str(cc),'power_subgraphs':bool(g['power_subgraphs']),**solved_meta[canon(g['edges'])]})
   except Unsolved as e:failed.append({'id':g['id'],'reason':str(e)})
  rec={'loop':L,'solved_count':len(ok),'remaining_count':len(failed),'b_solved':str(b),'c_solved':str(c),'graphs':ok,'unsolved':failed};out.append(rec)
  print('L',L,'solved',len(ok),'left',len(failed),'b',mp.nstr(b,20),'c',mp.nstr(c,20),'elapsed',time.time()-st,flush=True)
  (root/f'verification/sp_ms_{DPS}.json').write_text(json.dumps({'dps':DPS,'scope':'Gamma-evaluable graph sector with inherited nonexceptional terminal momentum, not full C6','loops':out,'seconds':time.time()-st},indent=2))
