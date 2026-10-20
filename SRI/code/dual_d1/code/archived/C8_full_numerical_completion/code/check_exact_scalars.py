"""Exact final input map; no numerical period values or fit constants used."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,re
import period_algebra as pa
ROOT=Path(__file__).resolve().parent.parent

def main():
 def load(name):
  text=(ROOT/'data'/(name+'.expr')).read_text()
  for word in re.findall(r'\bR_[A-Za-z0-9_]+',text):
   assert all(a=='0' or (a.startswith('m') and a[1:].isdigit()) for a in word.split('_')[1:]),('Uncancelled positive-letter period',name,word)
  return pa.parse_expr(text)
 p8=load('P8');kv=load('Kv');kknown=load('F3_known')
 r=kv.copy();pa.add(r,p8,4);pa.add(r,kknown,-1);assert not r
 reports={'Kv_plus_4P8_minus_known_exact_zero':True,'P8_terms':len(p8),'Kv_terms':len(kv),'P8_weight_zero':str(p8.get(())),'Kv_weight_zero':str(kv.get(()))}
 assert p8.get(())==F(-757993) and kv.get(())==F(77920,3)
 del p8,kv,kknown
 target=load('J9');s={}
 for name,c in [('A9_log',1),('Z8_log',-1),('EA7_finite',2),('EZ6_finite',-2),('J9_lower_shift',1)]:pa.add(s,load(name),F(c))
 r=target.copy();pa.add(r,s,-1);assert not r
 assert target.get(())==F(-10192,3)
 reports.update(J9_five_input_assembly_exact_zero=True,J9_terms=len(target),J9_weight_zero=str(target.get(())),rational_values_used_as_post_assembly_checks=True)
 dest=ROOT/'verification/replay';dest.mkdir(exist_ok=True);(dest/'exact_scalar_check.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
