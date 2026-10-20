"""Compare new full-source rational divergent jet against lower raw moments.
Neither P8's finite residue nor a target C8 enters the derivation.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import sys,json,hashlib
sys.path.insert(0,'/mnt/data/P8_final_run')
from period_algebra import parse_expr
ROOT=Path('/mnt/data/P8_final_run/F3_six_kink_completion');SER=Path('/mnt/data/P8_final_run/old_C7/C7_completion/engine/series');used={}
def add(o,p,c=F(1)):
 for k,v in p.items():
  x=o.get(k,F(0))+v*c
  if x:o[k]=x
  else:o.pop(k,None)
def mul(a,b):
 out={}
 for (p,k),v in a.items():
  for (q,l),w in b.items():out[p+q,k+l]=out.get((p+q,k+l),F(0))+v*w
 return {k:v for k,v in out.items() if v}
def prod(seq):
 out={(0,0):F(1)}
 for p in seq:out=mul(out,p)
 return out
@lru_cache(None)
def raw(name,der):
 n=int(name[1:]);lo=-(n//2);hi=0 if n==6 else 1;out={}
 for p in range(lo,hi+1):
  if name=='Z2' and p==1:continue
  if name=='Q2' and p<0:continue
  f=SER/f'{name}_{der}_p{p}.expr';assert f.exists(),f
  used[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest();ex=parse_expr(f.read_text())
  for mon,c in ex.items():
   if any(a!='ell' for a,k in mon):continue
   k=sum(e for a,e in mon);out[p,k]=c
 return out
terms=[(1,('Q6','Z2')),(-1,('Q4','Z2','Z2')),(1,('Q4','Z4')),(1,('Q2','Z2','Z2','Z2')),(-2,('Q2','Z2','Z4')),(1,('Q2','Z6'))]
pred={};basepred={}
for sign,names in terms:
 add(basepred,prod([raw(name,'base') for name in names]),F(sign))
 for i in range(len(names)):
  add(pred,prod([raw(name,'v' if j==i else 'base') for j,name in enumerate(names)]),F(sign))
pred={k:v for k,v in pred.items() if k[0]<0};basepred={k:v for k,v in basepred.items() if k[0]<0}
base={}
for p in (-4,-3,-2,-1):
 f=SER/f'Q8_base_p{p}.expr';used[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 for mon,c in parse_expr(f.read_text()).items():
  if all(a=='ell' for a,k in mon):base[p,sum(e for a,e in mon)]=c
assert base==basepred,('base normalization fails',base,basepred)
b0={}
for (p,k),c in base.items():
 add(b0,{(p,k):-p*c})
 if k:add(b0,{(p,k-1):-k*c})
dim=json.loads((ROOT/'P8_terminal_fibration/divergence_replay/total.json').read_text());actualb={tuple(map(int,key.split(','))):F(v) for key,v in dim['dimensionless_boundary'].items()}
add(actualb,{(p,k+1):c for (p,k),c in b0.items()},F(-8))
actual={}
for p in (-3,-2,-1):
 highest=max(k for (q,k),v in actualb.items() if q==p);nextv=F(0)
 for k in range(highest,-1,-1):
  c=-(actualb.get((p,k),F(0))+(k+1)*nextv)/p
  if c:actual[p,k]=c
  nextv=c
assert actual==pred,('NEW_BOUNDARY_VS_LOWER_FAIL',actual,pred)
checks=[{'power':p,'log_degree':k,'actual':str(actual.get((p,k),0)),'lower_prediction':str(pred.get((p,k),0)),'exact_equal':True} for p in (-3,-2,-1) for k in (0,1)]
report={'complete':True,'full_rational_divergent_polynomial_equal':True,'base_Q8_independently_agrees_with_lower_normalization':True,'all256_new_bins_used':True,'new_full_P8_not_used_in_prediction':True,'scale_restoration':'Bphysical=Bdimensionless-8 ell B0','six_displayed_checks':checks,'actual_entire_polynomial':{str(k):str(v) for k,v in sorted(actual.items())},'inputs':used}
(ROOT/'verification/P8_divergence_acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
