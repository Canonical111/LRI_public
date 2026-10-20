from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import sys,json,hashlib
sys.path.insert(0,'/mnt/data/P8_final_run')
import period_algebra as pa
SER=Path('/mnt/data/P8_final_run/old_C7/C7_completion/engine/series');OUT=Path('/mnt/data/P8_final_run/F3_six_kink_completion/P8_terminal_fibration/positive_divergence');OUT.mkdir(exist_ok=True);used={}
@lru_cache(None)
def raw(name,der,p,m):
 if name=='Z2' and p not in(-1,0):return {}
 if name=='Q2' and p not in(0,1):return {}
 path=SER/f'{name}_{der}_p{p}.expr';assert path.exists(),path
 used[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();out={}
 for mon,c in pa.parse_expr(path.read_text()).items():
  if sum(k for a,k in mon if a=='ell')==m:pa.add(out,{tuple((a,k) for a,k in mon if a!='ell'):c})
 return out
@lru_cache(None)
def conv(seq,p,m):
 if not seq:return {():F(1)} if p==m==0 else {}
 if len(seq)==1:return raw(*seq[0],p,m)
 lower=lambda item:0 if item[0]=='Q2' else -int(item[0][1:])//2
 # match raw prescription conservative bound floor; negative numerator cutoff handled
 lo=lower(seq[0]);hi=p-sum(lower(x) for x in seq[1:]);out={}
 for pp in range(lo,hi+1):
  for mm in range(m+1):
   a=raw(*seq[0],pp,mm)
   if a:
    b=conv(seq[1:],p-pp,m-mm)
    if b:pa.add(out,pa.mul(a,b))
 return out
terms=[(1,('Q6','Z2')),(-1,('Q4','Z2','Z2')),(1,('Q4','Z4')),(1,('Q2','Z2','Z2','Z2')),(-2,('Q2','Z2','Z4')),(1,('Q2','Z6'))]
M=[]
for ell in (0,1):
 o={}
 for sign,names in terms:
  for i in range(len(names)):
   seq=tuple((name,'v' if i==j else 'base') for j,name in enumerate(names));pa.add(o,conv(seq,-2,ell),F(sign))
 M.append(o)
out={};pa.add(out,M[0],F(2));pa.add(out,M[1],F(-1))
(OUT/'predicted.expr').write_text(pa.dump(out));(OUT/'prediction.json').write_text(json.dumps({'full_constant_periods_retained':True,'formula':'2*[eps^-2 ell^0] normalized lower products_v - [eps^-2 ell^1] normalized lower products_v','terms':len(out),'raw_inputs':used,'P8_unknown_not_used':True},indent=2));print('PREDICTED_TERMS',len(out))
