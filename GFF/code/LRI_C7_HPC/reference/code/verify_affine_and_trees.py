"""Independent rational fixed-point/Lagrange and binary-cluster geometry checks."""
from fractions import Fraction as F
from math import factorial,comb
from functools import lru_cache
from pathlib import Path
import random,json,time
W=Path(__file__).resolve().parents[1];N=8;rng=random.Random(9052319)
z=[F(0)]*N;one=z.copy();one[0]=1

def mul(a,b):
 c=z.copy()
 for i,x in enumerate(a):
  if x:
   for j,y in enumerate(b[:N-i]):c[i+j]+=x*y
 return c

def fixed(b,c):
 g=z.copy();eps=z.copy();eps[1]=1
 for _ in range(N):
  out=z.copy();gp=g.copy()
  for L in range(2,N):
   gp=mul(gp,g);v=mul(b[L],gp);out=[x+y for x,y in zip(out,v)]
  g=[(x-y)/3 for x,y in zip(eps,out)]
 out=z.copy();gp=one
 for L in range(1,N):
  gp=mul(gp,g);v=mul(c[L],gp);out=[x+y for x,y in zip(out,v)]
 out[0]+=F(1,2);out[1]-=F(1,2)
 return out

def bgmul(a,b):
 out=[z.copy()for _ in range(N)]
 for i,x in enumerate(a):
  if any(x):
   for j,y in enumerate(b[:N-i]):
    if any(y):out[i+j]=[u+v for u,v in zip(out[i+j],mul(x,y))]
 return out

def lagrange(b,c):
 X=[z.copy()for _ in range(N)]
 for L in range(2,N):X[L-1]=[a/3 for a in b[L]]
 powers=[[one]+[z.copy()for _ in range(N-1)]]
 for j in range(1,N):powers.append(bgmul(powers[-1],X))
 out=z.copy();out[0]=F(1,2);out[1]=-F(1,2)
 for k in range(1,N):
  bp=[z.copy()for _ in range(N)]
  for j in range(k):
   co=F((-1)**j*comb(k+j-1,j),3**k)
   for a in range(k):bp[a]=[u+co*v for u,v in zip(bp[a],powers[j][a])]
  val=z.copy()
  for L in range(1,k+1):val=[u+F(L,k)*v for u,v in zip(val,mul(c[L],bp[k-L]))]
  for n in range(k,N):out[n]+=val[n-k]
 return out
checks=[];t0=time.time()
for trial in range(32):
 b={1:[F(3)]+z[1:]};c={1:one.copy()}
 for L in range(2,N):
  b[L]=[F(rng.randint(-4,4),rng.randint(1,5))for j in range(N-L)]+[F(0)]*L
  c[L]=[F(rng.randint(-4,4),rng.randint(1,5))for j in range(N-L)]+[F(0)]*L
 a=fixed(b,c);v=lagrange(b,c);assert a==v
 b0={L:(v if L<5 else z.copy())for L,v in b.items()};c0={L:(v if L<5 else z.copy())for L,v in c.items()}
 f0=fixed(b0,c0);sumdelta=z.copy()
 for L in range(5,N):
  bb=dict(b0);cc=dict(c0);bb[L]=b[L];cc[L]=c[L];fl=fixed(bb,cc);sumdelta=[x+y-v for x,y,v in zip(sumdelta,fl,f0)]
 assert a==[x+y for x,y in zip(f0,sumdelta)]
 checks.append({'trial':trial,'fixed_equals_lagrange':True,'high_loop_affine':True})

# Exact normalization of all ordered binary-tree projective sectors.
normal=[]
for n in range(2,9):
 full=(1<<n)-1;weights={1<<i:F(1)for i in range(n)}
 for s in range(1,full+1):
  if s in weights:continue
  bit=s&-s;total=F(0);a=(s-1)&s
  while a:
   if a&bit:total+=2*weights[a]*weights[s^a]
   a=(a-1)&s
  weights[s]=total/(1 if s==full else s.bit_count()-1)
 target=factorial(n)*(n-1);assert weights[full]==target
 normal.append({'vertices':n,'Z':str(weights[full]),'factorial_times_L':target})

def det(M):
 M=[row.copy()for row in M];v=F(1)
 for i in range(len(M)):
  k=next(k for k in range(i,len(M))if M[k][i]);
  if k!=i:M[k],M[i]=M[i],M[k];v=-v
  a=M[i][i];v*=a
  for j in range(i,len(M)):M[i][j]/=a
  for k in range(i+1,len(M)):
   a=M[k][i]
   for j in range(i,len(M)):M[k][j]-=a*M[i][j]
 return v
geometries=[]
for n in range(2,9):
 for trial in range(12):
  parents=[];sizes=[];gaps=[]
  def tree(vs,parent):
   if len(vs)==1:return
   i=len(parents);parents.append(parent);sizes.append(len(vs));k=rng.randrange(1,len(vs))
   tree(vs[:k],i);gaps.append(i);tree(vs[k:],i)
  tree(list(range(n)),-1);L=n-1;ts=[F(rng.randint(1,5),7)for _ in range(L)];ts[0]=F(3,2)
  scales=[]
  for i in range(L):scales.append(ts[i]*(scales[parents[i]]if i else 1))
  jac=[]
  for g in gaps:
   anc=set();j=g
   while j>=0:anc.add(j);j=parents[j]
   jac.append([scales[g]/ts[j]if j in anc else F(0)for j in range(L)])
  rhs=ts[0]**(L-1)
  for j in range(1,L):rhs*=ts[j]**(sizes[j]-2)
  assert abs(det(jac))==rhs
  geometries.append({'vertices':n,'trial':trial,'jacobian_exact':True})
# Enumerated probabilities for arbitrary subset-dependent rates.
probs=[]
for n in range(2,6):
 full=(1<<n)-1;rates={s:F(1+((s*13)%7),3)for s in range(1,full+1)if s.bit_count()>1};rates[full]=1
 @lru_cache(None)
 def enum(s):
  if s.bit_count()==1:return (F(1),)
  vals=[];bit=s&-s;a=(s-1)&s
  while a:
   if a&bit:
    for x in enum(a):
     for y in enum(s^a):vals.extend([x*y/rates[s]]*2)
   a=(a-1)&s
  return tuple(vals)
 vals=enum(full);Z=sum(vals,F(0));assert sum((v/Z for v in vals),F(0))==1
 probs.append({'vertices':n,'ordered_trees':len(vals),'probability_sum_exact':True})
result=dict(assembly=checks,constant_measure_normalization=normal,jacobians=geometries,tree_probabilities=probs,seconds=time.time()-t0)
(W/'verification/affine_and_tree_exact_checks.json').write_text(json.dumps(result,indent=2))
print('passed',len(checks)*2+len(normal)+len(geometries)+len(probs),'checks in',result['seconds'])
