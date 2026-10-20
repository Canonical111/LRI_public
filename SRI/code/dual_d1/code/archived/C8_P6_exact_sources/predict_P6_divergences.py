from pathlib import Path
from fractions import Fraction as F
import zipfile,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'C8_full_numerical_completion/code'))
import period_algebra as pa
r=ROOT/'P6_full/control';r.mkdir(exist_ok=True)
def raw(name,p):
 path=ROOT/'lower_moments'/(name+'_p'+str(p)+'.expr')
 if not path.is_file():raise FileNotFoundError(path)
 return pa.parse_expr(path.read_text())
def moment(name,lo,hi):
 return {(a,b,p):raw(name+'_'+d,p) for a,b,d in [(0,0,'base'),(1,0,'v'),(0,1,'d'),(1,1,'vd')] for p in range(lo,hi+1)}
def mul(A,B):
 out={}
 for (a,b,p),v in A.items():
  for (c,d,q),w in B.items():
   if a+c<=1 and b+d<=1:
    key=(a+c,b+d,p+q);pa.add(out.setdefault(key,{}),pa.mul(v,w))
 return out
Q2=moment('Q2',0,1);Z2=moment('Z2',-1,0);Q4=moment('Q4',-2,0);Z4=moment('Z4',-2,0)
out={}
for A,sgn in [(mul(Q4,Z2),1),(mul(Q2,mul(Z2,Z2)),-1),(mul(Q2,Z4),1)]:
 for key,v in A.items():pa.add(out.setdefault(key,{}),v,sgn)
def logcoeff(p,m):
 ans={}
 for mon,c in out[1,1,p].items():
  mm=dict(mon)
  if mm.get('ell',0)==m:
   mm.pop('ell',None);pa.add(ans,{tuple(sorted(mm.items())):c})
 return ans
manifest={};record={}
for p in [-2,-1]:
 a=logcoeff(p,0);bb=logcoeff(p,1)
 pred={};pa.add(pred,a,-p);pa.add(pred,bb,-1)
 name='B_p'+str(p);path=r/(name+'_predicted.expr');path.write_text(pa.dump(pred));manifest[name]=str(path)
 record[name]={'rational_projection':str(pred.get((),0)),'volume_rational_constant':str(a.get((),0)),'volume_rational_log':str(bb.get((),0)),'terms':len(pred)}
assert record['B_p-2']['rational_projection']=='18'
assert record['B_p-1']['rational_projection']=='1638'
(r/'divergence_manifest.json').write_text(json.dumps(manifest,indent=2));(r/'divergence_prediction.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
