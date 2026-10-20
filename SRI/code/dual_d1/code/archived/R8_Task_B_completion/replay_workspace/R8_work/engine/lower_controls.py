"""Independent Fraction-only Laurent extraction of complete archived lower moments.
No R8 source result, C8 conjecture, or new boundary answer is read.
"""
from pathlib import Path
import json,time
from fractions import Fraction as Q
from math import comb,factorial
from functools import lru_cache
import task_b as tb
import terminal_projection as tp
ROOT=Path(__file__).resolve().parent.parent
ARCH=ROOT/'provenance/C7_completion/engine'

def rseries(text,maxp):
 r=tb.K.from_expr(text);num={}
 for mon,c in r.numer.items():
  if any(mon[1:]):continue
  num[mon[0]]=num.get(mon[0],Q(0))+Q(int(c.numerator),int(c.denominator))
 shift=0;an=[];scalar=Q(1)
 for fac,m in r.denf.items():
  co={}
  for mon,c in fac.items():
   assert not any(mon[1:]);co[mon[0]]=Q(int(c.numerator),int(c.denominator))
  if set(co)=={1}:
   shift-=m;scalar*=co[1]**(-m)
  elif set(co)<={0,1}:
   assert co.get(0);an.append((co.get(1,Q(0))/co[0],m));scalar*=co[0]**(-m)
  else:raise ValueError(co)
 pmin=min(num,default=0)+shift;degree=maxp-pmin
 analytic=(scalar,)
 for b,m in an:analytic=tp.pmul(analytic,tuple(Q((-1)**j*comb(m+j-1,j))*b**j for j in range(degree+1)))[:degree+1]
 out={}
 for k,c in num.items():
  for j,a in enumerate(analytic):
   power=k+shift+j
   if power<=maxp:out[power]=out.get(power,Q(0))+c*a
 return {p:c for p,c in out.items() if c}

@lru_cache(None)
def shiftpoly(N,k,d,lp):
 # [a^d] (1-N a)^(-k) log(1-N a)^lp
 if lp>d:return Q(0)
 h=tuple([Q(0)]+[Q(-N**j,j) for j in range(1,d+1)])
 hpow=(Q(1),)
 for _ in range(lp):hpow=tp.pmul(hpow,h)[:d+1]
 return sum(c*(Q(comb(k+d-j-1,d-j))*N**(d-j) if k else Q(int(d==j))) for j,c in enumerate(hpow) if j<=d)

@lru_cache(None)
def gjet(word,N,d):
 out=()
 for k in range(d+1):
  P=tp.large(tuple(Q(a) for a in word),k)
  for degree,c in enumerate(P):
   for m in range(degree+1):
    val=c*comb(degree,m)*(-1)**m*shiftpoly(N,k,d-k,degree-m)
    if val:out=tp.padd(out,tuple([Q(0)]*m+[val]))
 return out

@lru_cache(None)
def raw(n,kind,derivative,maxp):
 rows=json.loads((ARCH/f'{kind}{n}_{derivative}_negative.json').read_text());out={}
 for word,logs,text in rows:
  for p,c in rseries(text,maxp).items():
   for degree in range(maxp-p+1):
    jet=gjet(tuple(word),n-1,degree)
    if jet:out[p+degree]=tp.padd(out.get(p+degree,()),tuple([Q(0)]*len(logs)+[c*v for v in jet]))
 return {p:c for p,c in out.items() if c}

def mult(A,B,minp=-8,maxp=1):
 out={}
 for p,a in A.items():
  for q,b in B.items():
   if minp<=p+q<=maxp:out[p+q]=tp.padd(out.get(p+q,()),tp.pmul(a,b))
 return {p:c for p,c in out.items() if c}

def main():
 start=time.time()
 factors=[(6,'Q'),(4,'Q'),(2,'Q'),(6,'Z'),(4,'Z'),(2,'Z')]
 tables={}
 for n,k in factors:
  for d in ['base','v']:
   mx=1 if k=='Q' else 0
   tables[n,k,d]=raw(n,k,d,mx)
   print('RAW',k,n,d,len(tables[n,k,d]),time.time()-start,flush=True)
 # Differentiated vacuum-normalization singular identity.
 terms=[(1,[(6,'Q'),(2,'Z')]),(-1,[(4,'Q'),(2,'Z'),(2,'Z')]),(1,[(4,'Q'),(4,'Z')]),(1,[(2,'Q'),(2,'Z'),(2,'Z'),(2,'Z')]),(-2,[(2,'Q'),(2,'Z'),(4,'Z')]),(1,[(2,'Q'),(6,'Z')])]
 out={}
 for sign,fs in terms:
  for iv in range(len(fs)):
   prod={0:(Q(1),)}
   for j,(n,k) in enumerate(fs):prod=mult(prod,tables[n,k,'v' if j==iv else 'base'],maxp=4)
   for p,poly in prod.items():
    if p<0:out[p]=tp.padd(out.get(p,()),tuple(sign*v for v in poly))
 expected={-3:(Q(2,3),Q(2)),-2:(Q(-104,3),Q(-52,3)),-1:(Q(-80255,12),Q(-20429,6))}
 for p,v in expected.items():
  assert out[p][:2]==v,(p,out[p],v)
 report={'status':'exact_lower_moment_prediction','singular_polynomials':{str(p):list(map(str,v)) for p,v in out.items()},'six_targets':{str(p):list(map(str,v)) for p,v in expected.items()},'lower_moments':{f'{k}{n}_{d}':{str(p):list(map(str,co)) for p,co in vals.items()} for (n,k,d),vals in tables.items()},'R8_read_as_input':False,'C8_conjecture_used':False,'seconds':time.time()-start}
 (ROOT/'lower_controls.json').write_text(json.dumps(report,indent=2));print('CONTROLS_PASS',report['six_targets'],time.time()-start,flush=True)
if __name__=='__main__':main()
