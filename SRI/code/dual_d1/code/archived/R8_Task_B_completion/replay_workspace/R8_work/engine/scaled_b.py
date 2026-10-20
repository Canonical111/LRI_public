"""Equivalent dimensionless boundary integration with interval factor kept external.
Bhat=(1-N eps) int_0^T r(z)H dz - eps int_0^T z r(z)H dz,
T=1/eps-N, N=n-1. Pure scale logs are restored in final checks.
"""
import task_b as tb
from task_b import *
import negative_moments as nm
from math import comb
OUT=ROOT/'scaled_blocks';OUT.mkdir(exist_ok=True)
tb.OUT=OUT

def setup_scaled(n,face):
 N=n-2;ids=[0]+[i if i<face else i-1 for i in range(1,n)]
 coords=[K(i)+(GEN[j] if j else K.zero) for i,j in enumerate(ids)]
 D=sum((coords[i+1]-coords[i] for i in range(0,n,2)),K.zero)
 factors=[(D,1)];lv={}
 for i in range(n):
  for j in range(i+1,n):
   power=2*(-1)**(i+j);factors.append((coords[j]-coords[i],power))
   ia,ib=ids[i],ids[j];c=K(j-i)
   if ia==ib:continue
   words=[()]*N
   if ia:
    words[ia-1]=(GEN[ib]+c,);addto(lv,(tuple(words),()),K(power));words[ia-1]=()
   words[ib-1]=(-c,);addto(lv,(tuple(words),()),K(power))
 return factors,clean(lv),N,ids

@lru_cache(maxsize=60000)
def aword_scaled(word,N):
 out=[]
 for a in word:
  s=a.diff(GEN[N]);b=sub(a,N,K.zero)
  assert s.numer.is_ground and not s.denf and b.numer.is_ground and not b.denf
  def val(r):return F(str(r))
  out.append((val(s),val(b)))
 return tuple(out)

@lru_cache(maxsize=40000)
def rparts(co,N):
 num=[F(0)]*(max((m[N] for m in co.numer),default=0)+1)
 for m,c in co.numer.items():
  assert all(i==N or v==0 for i,v in enumerate(m)),m
  num[m[N]]+=F(int(c.numerator),int(c.denominator))
 den=[];scalar=F(1)
 for fac,p in co.denf.items():
  ff={}
  for m,c in fac.items():
   assert all(i==N or v==0 for i,v in enumerate(m)),m
   ff[m[N]]=F(int(c.numerator),int(c.denominator))
  assert set(ff)<={0,1} and ff.get(1),ff
  scalar*=ff[1]**(-p);den.append((-ff.get(0,F(0))/ff[1],p))
 return tuple(v*scalar for v in num),tuple(sorted(den))

def eval_parts(num,den,H,n):
 Tn=n-1
 val=mt.functional(num,den,H,0,Tn,0,0)-Tn*mt.functional(num,den,H,1,Tn,0,0)-mt.functional((F(0),)+num,den,H,1,Tn,0,0)
 return val

def negative_parts(num,den,H,n,demands):
 out=[F(0)]*len(demands)
 for kappa,scale,nn in [(0,F(1),num),(1,F(-(n-1)),num),(1,F(-1),(F(0),)+num)]:
  pol,_=tp.quotient(nn,den)
  for k,v in enumerate(pol):
   if v:
    for j,(p,r) in enumerate(demands):out[j]+=scale*v*nm.weighted_poly(k,H,kappa,n-1,p,r)
 return out

def last_two_scaled(items,n):
 # The source has been completely parsed; release cached source strings/references.
 tb.br.rr.rm.parseK.cache_clear()
 N=n-2;idx=N-1;total=F(0);st=time.time();count=0
 demands=tuple((p,r) for p in range(-(n//2-1),0) for r in (0,1));negatives=[F(0)]*len(demands)
 for j,((words,logs),R) in enumerate(items):
  assert not logs and not any(words[:idx-1]);active=words[idx-1];pp,po=apart(R,idx)
  bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
  def endpoint(c,wa,sign):
   nonlocal total,count
   H=mt.canon((aword_scaled(wa,N),aword_scaled(words[N-1],N)));num,den=rparts(c,N)
   total+=sign*eval_parts(num,den,H,n)
   ev=negative_parts(num,den,H,n,demands)
   for k,v in enumerate(ev):negatives[k]+=sign*v
   count+=1
  for kind,root,power,pref in bases:
   audit_basis(kind,root,power,active,idx)
   for wa,c in integrate_basis(kind,root,power,active,idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[N]).items():endpoint(pref*cb,wb,1)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;endpoint(pref*cb,(),-1)
  items[j]=None  # Consume the independent linear source term, not its exact file.
  if j%100==0:print('SCALED_FINAL',j+1,len(items),'sum',str(total),'seconds',time.time()-st,flush=True)
 return total,count,negatives

tb.setup=setup_scaled;tb.last_two=last_two_scaled
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',action='store_true');p.add_argument('--n',type=int,default=8);p.add_argument('--face',type=int);p.add_argument('--block');a=p.parse_args()
 if a.sources:tb.sources(a.n,a.face)
 else:tb.worker(a.block)
