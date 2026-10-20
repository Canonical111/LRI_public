"""Standard-library acceptance check of completed Task C.
No conjectural C8 value is used; partial coverage or divergent mismatch fails.
"""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib
ROOT=Path(__file__).resolve().parent.parent

def trim(p):
 p=list(p)
 while p and not p[-1]:p.pop()
 return p
def add(p,q):
 r=list(p)+[F(0)]*max(0,len(q)-len(p))
 for j,c in enumerate(q):r[j]+=c
 return trim(r)
def scale(p,c):return trim([c*v for v in p])
def shift(p,m):return [F(0)]*m+list(p) if p else []
def boundary(p,a):return trim([-p*c-(j+1)*(a[j+1] if j+1<len(a) else F(0)) for j,c in enumerate(a)])
def inverse(p,b):
 assert p<0
 out=[F(0)]*len(b)
 for j in range(len(b)-1,-1,-1):out[j]=(-b[j]-(j+1)*(out[j+1] if j+1<len(out) else F(0)))/p
 return trim(out)
def readtab(d):return {int(p):list(map(F,a)) for p,a in d.items()}
def load(kind,n,deriv,jets=True):
 root=ROOT/'tail_blocks'/f'{kind}_{deriv}';total=F(0);polys={};rows=[];seen=[];nchecks=0
 for f in range(1,n//2+1):
  m=json.loads((root/f'n{n}_face{f}_manifest.json').read_text());assert m['source_complete'];val=F(0)
  mult=1 if f*2==n else 2
  for b in m['blocks']:
   assert b['id'] not in seen;seen.append(b['id']);folder=root/b['id']
   assert hashlib.sha256((folder/'stage1.jsonl').read_bytes()).hexdigest()==b['source_sha256']
   r=json.loads((folder/'result.json').read_text());assert r['status']=='complete_block_not_full_integral';assert r['source_sha256']==b['source_sha256']
   val+=F(r['value'])
   if jets:
    js=json.loads((folder/'full_boundary_jets.json').read_text());src=ROOT/js['source']
    assert hashlib.sha256(src.read_bytes()).hexdigest()==js['source_sha256']
    tab=readtab(js['boundary_polynomials']);assert (tab.get(0) or [F(0)])[0]==F(r['value']);nchecks+=js['agreement_with_separate_scalar_functional']
    for p,a in tab.items():polys[p]=add(polys.get(p,[]),scale(a,mult))
  rows.append({'face':f,'multiplicity':mult,'boundary_constant':str(val),'blocks':len(m['blocks'])});total+=mult*val
 return total,polys,rows,nchecks

def main():
 a,ah,ar,ac=load('A',7,'d');z,zh,zr,zc=load('Z',6,'d');tail=z-a
 controls=json.loads((ROOT/'tail_lower_controls.json').read_text());arch=controls['archived_base_and_charge_polynomials']
 ab,zb,av,zv=[readtab(arch[k]) for k in ['A7_base','Z6_base','A7_v','Z6_v']]
 pred=readtab(controls['singular_tail_difference']);checks=[];count=0
 actual_polys={}
 for p in range(-4,0):
  b0=add(boundary(p,ab.get(p,[])),scale(boundary(p,zb.get(p,[])),-1))
  bv=add(boundary(p,av.get(p,[])),scale(boundary(p,zv.get(p,[])),-1))
  bd=add(ah.get(p,[]),scale(zh.get(p,[]),-1))
  physical=add(add(bd,shift(bv,1)),scale(shift(b0,2),3))
  actual=inverse(p,physical);expected=pred.get(p,[])
  assert trim(actual)==trim(expected),(p,list(map(str,actual)),list(map(str,expected)))
  count+=max(len(actual),1);actual_polys[p]=actual
  checks.append({'power':p,'actual':list(map(str,actual)),'independent_lower_prediction':list(map(str,expected)),'exact_equal':True})
 regression=[]
 for k,n,d,expected in [('Z',6,'base',F(233,2)),('Z',6,'v',F(-1145)),('Z',4,'d',F(-65)),('A',5,'d',F(-708))]:
  v,_,_,_=load(k,n,d,False);assert -v==expected
  regression.append({'raw_moment':f'{k}{n}_{d}','single_log':str(-v),'archived_exact':str(expected),'exact_equal':True})
 result={'status':'Task_C_tail_complete','definition':'pi_0 [epsilon^0 log(epsilon)] partial_delta(A7-Z6) at v=1,delta=0',
   'A7_tail_single_log':str(-a),'Z6_tail_single_log':str(-z),'R_tail':str(tail),
   'C8_rational_contribution':str(F(3,4)*tail),'updated_C8_constant':str(F(-111389,24)+F(3,4)*tail),
   'A7_faces':ar,'Z6_faces':zr,'source_blocks':sum(r['blocks'] for r in ar+zr),
   'scalar_vector_terminal_checks':ac+zc,'negative_power_coefficient_checks':count,'singular_checks':checks,
   'complete_archived_control_integrals':regression,'remaining_group':'R9','C8_not_finished':True,'C8_conjecture_used':False}
 (ROOT/'Task_C_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
