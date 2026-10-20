"""Ordered-gap sectors for full charge/tail derivatives. No period projection."""
import itertools
import sympy as s

def sectors(n):
 m=n-1;d=m-1;xx=s.symbols('x:'+str(d));lev=[s.Integer(1)]
 for x in xx:lev.append(lev[-1]*x)
 S=sum(lev);out=[];seen={}
 for perm in itertools.permutations(range(m)):
  rank={r:j for j,r in enumerate(perm)};ew=[0]*d;em=[0]*d;fac={};pair={}
  def factor(indices):
   k=min(rank[j] for j in indices)
   return k,s.expand(sum(lev[rank[j]]/lev[k] for j in indices))
  for i in range(n):
   for j in range(i+1,n):
    sign=(-1)**(i+j);k,P=factor(range(i,j))
    for a in range(k):ew[a]+=2*sign
    if P!=1:fac[P]=fac.get(P,0)+2*sign
    pair[k,P]=pair.get((k,P),0)+sign
  k,PD=factor(range(0,m,2))
  for a in range(k):em[a]+=1
  if PD!=1:fac[PD]=fac.get(PD,0)+1
  fac={p:c for p,c in fac.items() if c};pair={k:c for k,c in pair.items() if c}
  p=tuple(m-2-j+ew[j]+em[j] for j in range(d))
  key=p,tuple(sorted((str(P),c) for P,c in fac.items())),tuple(sorted((k,str(P),c) for (k,P),c in pair.items()))
  if key in seen:out[seen[key]]['mult']+=1
  else:
   seen[key]=len(out);out.append(dict(xx=xx,p=p,c=tuple(v//2 for v in ew),factors=fac,pairs=pair,S=S,mult=1,perm=perm,n=n,k0=m+1-n))
 return out
if __name__=='__main__':
 for n in (4,6):
  ss=sectors(n);print(n,len(ss),sum(x['mult'] for x in ss),sorted(set(p for x in ss for p in x['p'])))
