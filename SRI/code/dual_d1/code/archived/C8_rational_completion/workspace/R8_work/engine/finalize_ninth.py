"""Accept the complete ninth-order rational group only after exact checks.
No numerical or conjectural C8 coefficient is supplied to the integrators.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json
from finalize_tail import load,readtab,add,scale,inverse,trim
ROOT=Path(__file__).resolve().parent.parent

def endpoint(n):
 root=ROOT/'endpoint_odd';m=json.loads((root/f'EA{n}_manifest.json').read_text());assert m['complete_source']
 total=F(0);rows=[];seen=set()
 for b in m['blocks']:
  name=b['id'];assert name not in seen;seen.add(name)
  p=root/name;digest=hashlib.sha256((p/'stage1.jsonl').read_bytes()).hexdigest()
  assert digest==b['source_sha256']
  result=json.loads((p/'result.json').read_text());assert result['status']=='complete_block_not_full_moment';assert result['source_sha256']==digest
  val=F(result['finite_rational_constant']);total+=val
  rows.append({'id':name,'value':str(val),'source_sha256':digest})
 return total,rows

def main():
 a,ap,ar,ac=load('A',9,'base');z,zp,zr,zc=load('Z',8,'base')
 e,er=endpoint(7);e5,e5rows=endpoint(5)
 reference=json.loads((ROOT/'endpoint_control.json').read_text())
 assert e5==F(reference['archived_reference'])
 controls=json.loads((ROOT/'ninth_lower_controls.json').read_text());pred=readtab(controls['polynomials']);checks=[];count=0
 for p in range(-5,0):
  bd=add(ap.get(p,[]),scale(zp.get(p,[]),-1));act=inverse(p,bd);exp=pred.get(p,[])
  assert trim(act)==trim(exp),(p,list(map(str,act)),list(map(str,exp)))
  count+=max(len(act),1);checks.append({'power':p,'actual':list(map(str,act)),'independent_lower_prediction':list(map(str,exp)),'exact_equal':True})
 r9=-a+z+2*e
 old=F(json.loads((ROOT/'Task_C_result.json').read_text())['updated_C8_constant'])
 c8=old+r9/4
 result={'status':'Task_D_complete_and_rational_C8_evaluated',
   'definition':'R9=pi0[epsilon^0 log epsilon](A9-Z8)+2*pi0[epsilon^0 log^0 epsilon]EA7',
   'A9_single_log':str(-a),'Z8_single_log':str(-z),'EA7_finite':str(e),'R9':str(r9),
   'C8_previous_constant':str(old),'C8_Task_D_contribution':str(r9/4),'C8_weight_zero':str(c8),'T4_weight_zero':str(c8/8),
   'A9_faces':ar,'Z8_faces':zr,'EA7_blocks':er,
   'boundary_source_blocks':sum(r['blocks'] for r in ar+zr),'endpoint_source_blocks':len(er),
   'scalar_vector_terminal_checks':ac+zc,'negative_power_coefficient_checks':count,'singular_checks':checks,
   'EA5_control':{'new':str(e5),'archived':reference['archived_reference'],'exact_equal':True,'blocks':len(e5rows)},
   'C8_conjecture_used_as_input':False,'positive_weight_part_of_C8_evaluated':False,
   'scope':'formal weight-zero projection in the archived matched hard-core prescription; not an all-order proof'}
 (ROOT/'Task_D_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
