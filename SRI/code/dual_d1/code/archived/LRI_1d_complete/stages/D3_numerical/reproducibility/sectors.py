"""Exact Hepp sectors for alternating kinks, including uncut endpoint gaps."""
import itertools,sympy as s

def sectors(n,charge=False,endpoint=False,pair=None):
 m=n+1 if endpoint else n-1;d=m-1
 xx=s.symbols('x:'+str(d),nonnegative=True);lev=[s.Integer(1)]
 for x in xx:lev.append(lev[-1]*x)
 S=sum(lev);nw=n if n%2==0 else n-1;k0=m+int(charge)-nw
 out=[];seen={}
 for perm in itertools.permutations(range(m)):
  rank={r:j for j,r in enumerate(perm)};ew=[0]*d;ee=[0]*d;em=[0]*d;fac={};sv={};se={}
  def factor(indices):
   k=min(rank[j] for j in indices)
   return k,s.expand(sum(lev[rank[j]]/lev[k] for j in indices))
  for i in range(n):
   for j in range(i+1,n):
    sign=(-1)**(i+j);ex=2*sign
    inds=range(i+1,j+1) if endpoint else range(i,j)
    k,P=factor(inds)
    for ax in range(k):ew[ax]+=ex
    if P!=1:fac[P]=fac.get(P,0)+ex
    if pair is None or pair==(i,j):
     if P!=1:sv[P]=sv.get(P,0)+ex
     if pair is not None:
      ee=[ex*int(ax<k) for ax in range(d)]
  if pair is None:cv=ew.copy();shift=-nw
  else:cv=ee.copy();shift=2*(-1)**sum(pair);ee=[0]*d
  if charge:
   inds=range(1,n,2) if endpoint else range(0,m,2)
   k,P=factor(inds)
   for ax in range(k):em[ax]+=1
   if P!=1:fac[P]=fac.get(P,0)+1
  if endpoint:
   for i in range(n):
    sign=(-1)**i
    for inds,ex in [(range(i+1),sign),(range(i+1,m),sign if n%2 else -sign)]:
     k,P=factor(inds)
     for ax in range(k):ee[ax]+=ex
     if P!=1:se[P]=se.get(P,0)+ex
   se[S]=se.get(S,0)-2*(n%2)
  fac[S]=fac.get(S,0)-k0;sv[S]=sv.get(S,0)-shift
  p=tuple(m-2-j+ew[j]+em[j] for j in range(d))
  qrank=max(rank[j] for j in range(1,n)) if endpoint else m-1
  mask=tuple(int(j<qrank) for j in range(d))
  def keyfac(f):return tuple(sorted((str(P),e) for P,e in f.items() if e))
  key=p,tuple(cv),tuple(ee),mask,keyfac(fac),keyfac(sv),keyfac(se)
  if key in seen:out[seen[key]]['mult']+=1
  else:
   seen[key]=len(out)
   out.append(dict(xx=xx,p=p,c=tuple(cv),c2=tuple(ee),qmask=mask,factors=fac,slopes=sv,slopes2=se,S=S,nW=nw,mult=1,perm=perm,n=n,charge=charge,endpoint=endpoint,k0=k0,kshift=shift))
 return out
