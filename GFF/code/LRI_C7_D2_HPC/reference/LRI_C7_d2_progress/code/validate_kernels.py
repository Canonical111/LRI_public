from pathlib import Path
from fractions import Fraction as F
import itertools,json,time,random
W=Path(__file__).resolve().parents[1]
# Independent determinant evaluation using the graph Laplacian, not polynomial masks.
def det(M):
 n=len(M);A=[list(map(F,r))for r in M];out=F(1)
 for i in range(n):
  k=next((k for k in range(i,n)if A[k][i]),None)
  if k is None:return F(0)
  if k!=i:A[k],A[i]=A[i],A[k];out=-out
  x=A[i][i];out*=x
  for k in range(i+1,n):
   y=A[k][i]/x
   for j in range(i+1,n):A[k][j]-=y*A[i][j]
 return out

def independent(ed,x):
 n=max(max(e)for e in ed)+1;full=(1<<n)-1;E=len(ed);subs=[]
 for s in range(1,full):
  vs=[i for i in range(n)if s>>i&1];es=[k for k,(a,b)in enumerate(ed)if s>>a&1 and s>>b&1]
  if len(vs)<2 or len(es)!=2*(len(vs)-1):continue
  if any(sum(((s0>>ed[k][0])^(s0>>ed[k][1]))&1 for k in es)<2 for s0 in range(1,full)if s0&s==s0 and s0!=s):continue
  subs.append(s)
 cache={}
 def block(P,children):
  pp=list(range(n))
  def root(a):
   while pp[a]!=a:a=pp[a]
   return a
  for c in children:
   r=(c&-c).bit_length()-1
   for i in range(n):
    if c>>i&1:pp[root(i)]=root(r)
  vs=sorted(set(root(i)for i in range(n)if P>>i&1));ids={v:j for j,v in enumerate(vs)};ee=[]
  for k,(a,b)in enumerate(ed):
   if not(P>>a&1 and P>>b&1)or any(c>>a&1 and c>>b&1 for c in children):continue
   ee.append((k,ids[root(a)],ids[root(b)]))
  if not ee:return F(1),[]
  key=tuple(ee)
  if key not in cache:
   M=[[F(0)for _ in vs]for _ in vs]
   for k,a,b in ee:
    v=1/x[k];M[a][a]+=v;M[b][b]+=v;M[a][b]-=v;M[b][a]-=v
   cache[key]=det([row[:-1]for row in M[:-1]])*__import__('math').prod(x[k]for k,a,b in ee)
  return cache[key],[k for k,a,b in ee]
 total=F(0);forests=0
 def emit(ch):
  nonlocal total,forests
  sets=ch+[full];den=F(1);root=[]
  for P in sets:
   children=[c for c in ch if c!=P and c&P==c and not any(c!=z and z!=P and c&z==c and z&P==z for z in ch)]
   d,ids=block(P,children);den*=d
   if P==full:root=ids
  total+=(-1)**len(ch)*sum(x[k]for k in root)/den;forests+=1
 def rec(ch,possible):
  emit(ch)
  for i,c in enumerate(possible):rec(ch+[c],[z for z in possible[i+1:]if (c&z)==c or (c&z)==z or (c&z).bit_count()<=1])
 rec([],subs)
 return total/sum(x),forests

def stored(g,x):
 p=W/'inputs'/g['file'];it=iter(p.read_text().split());hdr=[next(it)for _ in range(7)];M,T=int(hdr[-2]),int(hdr[-1]);masks=[int(next(it))for _ in range(M)];mons=[__import__('math').prod(x[j]for j in range(len(x))if mask>>j&1)for mask in masks];v=F(0)
 for _ in range(T):
  k=int(next(it));den=sum(mons[int(next(it))]for _ in range(k));co=[int(next(it))for _ in x];v+=sum(a*b for a,b in zip(co,x))/den
 return v/sum(x)
if __name__=='__main__':
 start=time.time();rows=json.load(open(W/'inputs/L7/inventory.json'));gs=[g for g in rows if g['status']=='finite-kernel'];rr=random.Random(95887);chosen=rr.sample(gs,20)+[g for g in gs if g['primitive']][:4];out=[]
 for i,g in enumerate(chosen):
  x=[F(rr.randrange(1,12),rr.randrange(1,12))for e in g['edges']];a,n=independent(g['edges'],x);b=stored(g,x);assert a==b,(g['id'],a,b);out.append(dict(id=g['id'],forests=n,exact_match=True));print(i,g['id'],n,flush=True)
 (W/'verification/kirchhoff_exact_checks.json').write_text(json.dumps(dict(checks=out,seconds=time.time()-start),indent=2))
