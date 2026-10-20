"""Independent exact linear-period implementation of the growth functional.
It expands only coefficients of regularized periods; it does not evaluate them.
"""
from pathlib import Path
from functools import lru_cache
from fractions import Fraction as F
from math import factorial
import json,time,sys,hashlib
import sum_growth_sources as pol
ROOT=Path(__file__).resolve().parent.parent

def accum(out,inp,scale):
 if not scale:return
 for k,v in inp:
  x=out.get(k,F(0))+scale*v
  if x:out[k]=x
  else:out.pop(k,None)
@lru_cache(maxsize=300000)
def big(w,n,k):
 if k<0:return ()
 if not w:return (((),F(1)),) if n==0 and k==0 else ()
 if n==0:return ((w[k:],F(1,factorial(k))),) if k<=len(w) else ()
 if k>len(w)-1:return ()
 out={}
 for h in range(len(w)-k):
  scale=-F(factorial(k+h),factorial(k)*n**(h+1))
  for r in range(n+1):accum(out,big(w[1:],n-r,k+h),scale*w[0]**r)
 return tuple(out.items())
@lru_cache(None)
def moment(r,k,N):
 if r==0:return F((-1)**k*factorial(k))
 if k>=r:return F(0)
 p=[F(1)]
 for j in range(1,r):
  out=[F(0)]*(len(p)+1)
  for i,c in enumerate(p):out[i]+=c*(r+1-j);out[i+1]+=c
  p=out
 return F((-N)**r*factorial(k),factorial(r))*p[k]
@lru_cache(maxsize=120000)
def phi(w,p,N):
 out={}
 for n in range(p+1):
  for k in range(len(w)+1):accum(out,big(w,n,k),moment(p-n,k,N))
 return tuple(out.items())

def raw_functional(path,N):
 out={};st=time.time();rows=0;maxdeg=0
 for line in Path(path).open():
  ww,ll,tx=json.loads(line);rows+=1
  assert not any(ww[:-1]);w=tuple(map(int,ww[-1]))
  if 1 in ll:continue
  for mon,c in pol.parse(tx):
   m=dict(mon);p=m.pop('r',0);maxdeg=max(maxdeg,p)
   for k in ll:m['log('+str(k)+')']=m.get('log('+str(k)+')',0)+1
   pref=tuple(sorted(m.items()))
   for tail,cf in phi(w,p,N):
    key=tail,pref;v=out.get(key,F(0))+c*cf
    if v:out[key]=v
    else:out.pop(key,None)
  if rows%10000==0:print('LINEAR_GROWTH',rows,len(out),time.time()-st,flush=True)
 return out,{'rows':rows,'max_polynomial_degree':maxdeg,'raw_period_terms':len(out),'seconds_linear':time.time()-st}

def canonicalize(raw):
 import sympy as s
 import asymptotic_gpl as ag
 from read_expression import parse
 atoms={};out={};st=time.time();count=0
 @lru_cache(None)
 def ze(w):return s.expand(ag.Z(w))
 for (w,pr),cf in raw.items():
  pref=s.S.One
  for a,n in pr:
   if a not in atoms:atoms[a]=parse(a)
   pref*=atoms[a]**n
  val=s.expand(s.Rational(cf.numerator,cf.denominator)*pref*ze(w))
  for term in s.Add.make_args(val):
   c,m=term.as_coeff_Mul(rational=True);v=out.get(m,s.S.Zero)+c
   if v:out[m]=v
   else:out.pop(m,None)
  count+=1
  if count%10000==0:print('CANONICAL_GROWTH',count,len(out),time.time()-st,flush=True)
 return s.Add(*(m*c for m,c in out.items()))

if __name__=='__main__':
 folder=Path(sys.argv[1]);path=folder/('growth_stage5.jsonl' if (folder/'growth_stage5.jsonl').exists() else 'stage5.jsonl')
 raw,report=raw_functional(path,5);ans=canonicalize(raw)
 import sympy as s
 target=folder/'linear_growth_finite.expr';target.write_text(s.sstr(ans,order='none'))
 for name in ('growth_finite.expr','finite.expr'):
  if (folder/name).exists():
   from read_expression import load
   assert s.expand(ans-load(folder/name))==0,('difference',name)
   report['agrees_with_'+name]=True
 report.update({'rational_projection':str(ans.as_coeff_Add()[0]),'final_terms':len(s.Add.make_args(ans)),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'all_periods_retained':True})
 (folder/'linear_growth_report.json').write_text(json.dumps(report,indent=2));print('LINEAR_GROWTH_DONE',report,flush=True)
