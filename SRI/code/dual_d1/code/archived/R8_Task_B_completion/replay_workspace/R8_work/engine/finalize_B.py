"""Accept Task B only after complete coverage and all independent divergences.
No missing block is interpreted as zero. No C8 guess is used.
"""
from pathlib import Path
from fractions import Fraction as Q
import json,hashlib,time
import lower_controls as lc
import scaled_b as sb
ROOT=sb.ROOT;OUT=sb.OUT

def main():
 st=time.time();faces=[];negative=[Q(0)]*6;covered=[];crosschecks=[];conversions=[]
 for face,expected_count,mult in [(1,8,2),(2,13,2),(3,8,2),(4,8,1)]:
  mf=OUT/f'n8_face{face}_manifest.json';m=json.loads(mf.read_text());rows=m['blocks']
  assert m['source_complete'] and len(rows)==expected_count
  assert [r['id'] for r in rows]==[f'n8_f{face}_b{j:02d}' for j in range(expected_count)]
  assert len({(r['kind'],r['pole'],r['order']) for r in rows})==expected_count
  total=Q(0)
  for r in rows:
   name=r['id'];folder=OUT/name
   digest=hashlib.sha256((folder/'stage1.jsonl').read_bytes()).hexdigest()
   d=json.loads((folder/'result.json').read_text())
   assert r['source_sha256']==d['source_sha256']==digest,(name,'changed input')
   assert d['status']=='complete_block_not_full_integral'
   assert len(d['dimensionless_negative_inverse_euler'])==6
   reference=ROOT/'blocks'/name/'result.json'
   if reference.exists():
    old=json.loads(reference.read_text());assert Q(old['value'])==Q(d['value'])
    if 'dimensionless_negative_inverse_euler' in old:
     assert list(map(Q,old['dimensionless_negative_inverse_euler']))==list(map(Q,d['dimensionless_negative_inverse_euler']))
    crosschecks.append(name)
   conversion=folder/'conversion.json'
   if conversion.exists():
    cv=json.loads(conversion.read_text());assert cv['independent_source_equality_exact']
    for c in cv['conversions']:
     old=ROOT/'blocks'/name/f"stage{c['stage']}.jsonl"
     new=folder/f"stage{c['stage']}.jsonl"
     assert hashlib.sha256(old.read_bytes()).hexdigest()==c['input_sha256']
     assert hashlib.sha256(new.read_bytes()).hexdigest()==c['output_sha256']
    conversions.append(name)
   total+=Q(d['value'])
   negative=[a+mult*Q(v) for a,v in zip(negative,d['dimensionless_negative_inverse_euler'])]
   covered.append(name)
  faces.append({'face':face,'multiplicity':mult,'blocks':len(rows),'boundary_constant':str(total)})
 assert len(covered)==37 and len(set(covered))==37
 R8=-sum(Q(f['boundary_constant'])*f['multiplicity'] for f in faces)
 # Scale correction from complete archived, independent undifferentiated Q8.
 base=lc.raw(8,'Q','base',-1)
 lower=json.loads((ROOT/'lower_controls.json').read_text())
 checks=[]
 for i,p in enumerate([-3,-2,-1]):
  poly=base.get(p,());inv=sb.tp.integrate_exp(poly,p)
  for m in (0,1):
   val=negative[2*i+m]+8*(inv[m] if m<len(inv) else 0)-8*(poly[m-1] if m and m-1<len(poly) else 0)
   target=Q(lower['six_targets'][str(p)][m])
   checks.append({'power':p,'log_degree':m,'actual':str(val),'independent_lower_prediction':str(target),'exact_equal':val==target})
 good=all(c['exact_equal'] for c in checks)
 result={'status':'Task_B_complete' if good else 'DO_NOT_ACCEPT_divergence_failure','definition':'pi_0 [epsilon^0 log(epsilon)] partial_v Q8 at v=1,delta=0','R8':str(R8),'C8_rational_contribution':str(-R8/8),'updated_C8_constant':str(Q(-298171,3)-R8/8),'faces':faces,'all_37_blocks_present_and_unique':True,'six_divergence_checks':checks,'dimensionless_inverse_euler_sum':list(map(str,negative)),'base_Q8_singular_polynomials':{str(p):list(map(str,v)) for p,v in base.items()},'C8_not_finished':True,'C8_conjecture_used':False,'remaining_groups':['R_tail','R9'],'exact_complete_unscaled_comparisons':crosschecks,'exact_adopted_stage_conversions':conversions,'seconds':time.time()-st}
 (ROOT/'Task_B_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
 assert good,'Complete sum must not be promoted until the independent divergences agree'
if __name__=='__main__':main()
