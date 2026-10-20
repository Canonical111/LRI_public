"""Exact finite part of e*integral_0^(1/e-N) R(t)G_w(t)dt.
The proper rational part cannot contribute: its integral grows at most as
logarithms, and the external e kills every such contribution. Full constant
periods in the asymptotics of G are retained. Only kap=1 is implemented.
"""
from full_runner import *
from finite_extract_fast import big_coefficient
from read_expression import parse as parse_scalar
import sympy as s
from functools import lru_cache
from fractions import Fraction as Q

@lru_cache(maxsize=10000)
def polynomial_part(R,idx):
 active=[(f,m) for f,m in R.denf.items() if degree(f,idx)>0]
 dd=sum(m*degree(f,idx) for f,m in active)
 if degree(R.numer,idx)<dd:return {}
 if not active:
  inv=ff.Frac(K,K.ring.one,R.denf.copy())
  return {p:K(c)*inv for p,c in pcoeff(R.numer,idx).items()}
 dp=K.ring.one;spec={f:m for f,m in R.denf.items() if degree(f,idx)<=0}
 for f,m in active:dp*=f**m
 ns=dict(pcoeff(R.numer,idx));ds=pcoeff(dp,idx);dd=max(ds);sinv=ff.Frac(K,K.ring.one,spec);out={}
 while ns and max(ns)>=dd:
  dn=max(ns);c=ns[dn]/ds[dd];j=dn-dd;out[j]=out.get(j,K.zero)+c*sinv
  for k,b in ds.items():
   kn=k+j;v=K.zero if k==dd else ns.get(kn,K.zero)-c*b
   if v:ns[kn]=v
   else:ns.pop(kn,None)
 return clean(out)

@lru_cache(None)
def moment(r,k,N):
 # (-N)^r d_alpha^k[binomial(alpha,r)/alpha] at alpha=r+1.
 if r==0:return s.Integer((-1)**k*factorial(k))
 if k>=r:return s.S.Zero
 a=s.Symbol('a');p=s.sympify(s.prod(a-j for j in range(1,r)))/s.Integer(factorial(r))
 return s.expand((-N)**r*s.diff(p,a,k).subs(a,r+1))

@lru_cache(maxsize=100000)
def functional(word,p,N):
 return s.expand(sum(moment(p-n,k,N)*big_coefficient(word,n,k) for n in range(p+1) for k in range(len(word)+1) if moment(p-n,k,N)))

@lru_cache(maxsize=10000)
def scalar(text):return parse_scalar(text)

def evaluate_source(path,idx,N):
 out={};total=0;nonproper=0;st=time.time()
 for line in Path(path).open():
  ww,ll,text=json.loads(line);total+=1
  assert all(not w for w in ww[:-1]);word=tuple(int(rm.parseK(a)) for a in ww[-1]);R=rm.parseK(text)
  assert not R.diff(e),('unexpected cutoff dependence',text)
  pp=polynomial_part(R,idx)
  if not pp:continue
  nonproper+=1;logs=s.prod(s.log(k) for k in ll)
  value=s.expand(logs*sum(scalar(str(c))*functional(word,p,N) for p,c in pp.items()))
  for term in s.Add.make_args(value):
   cf,mon=term.as_coeff_Mul(rational=True);out[mon]=out.get(mon,s.S.Zero)+cf
  if total%1000==0:print('GROWTH',total,nonproper,len(out),time.time()-st,flush=True)
 ans=s.Add(*(m*c for m,c in out.items() if c));return ans,{'rows':total,'nonproper_rows':nonproper,'terms':len(s.Add.make_args(ans)),'seconds':time.time()-st,'no_constant_period_projection':True}

def main(folder):
 folder=Path(folder);ans,report=evaluate_source(folder/'stage5.jsonl',6,5)
 (folder/'growth_finite.expr').write_text(s.sstr(ans,order='none'))
 if (folder/'finite.expr').exists():
  from read_expression import load as readfull
  assert s.expand(ans-readfull(folder/'finite.expr'))==0
  report['agrees_with_complete_final_integration']=True
 report['rational_projection']=str(ans.as_coeff_Add()[0]);report['source_sha256']=hashlib.sha256((folder/'stage5.jsonl').read_bytes()).hexdigest()
 (folder/'growth_report.json').write_text(json.dumps(report,indent=2));print('GROWTH_FINISHED',report,flush=True)
if __name__=='__main__':main(sys.argv[1])
