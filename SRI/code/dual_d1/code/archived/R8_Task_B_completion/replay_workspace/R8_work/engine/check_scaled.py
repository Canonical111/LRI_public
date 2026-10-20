import scaled_b as sb
import json,time
from fractions import Fraction as F
st=time.time()
for face in [1,2,3]:
 rows=sb.tb.sources(6,face)
 for row in rows:
  sb.tb.worker(row['id'])
  orig=json.loads((sb.ROOT/'blocks'/row['id']/'result.json').read_text())
  new=json.loads((sb.OUT/row['id']/'result.json').read_text())
  assert orig['value']==new['value'],(row['id'],orig['value'],new['value'])
  nr=sb.ROOT/'blocks'/row['id']/'negative_replay.json'
  if nr.exists():
   old=json.loads(nr.read_text())
   assert old['dimensionless_negative_inverse_euler']==new['dimensionless_negative_inverse_euler']
  sb.tb.br.rr.clear();sb.mt.clear();sb.aword_scaled.cache_clear();sb.rparts.cache_clear()
 print('SCALED_FACE_PASS',face,time.time()-st,flush=True)
(sb.ROOT/'scaled_n6_control.json').write_text(json.dumps({'status':'exact_complete_n6_scaled_control','compared_every_block':True,'compared_all_negative_coefficients':True,'seconds':time.time()-st},indent=2))
print('SCALED_ALL_PASS',time.time()-st,flush=True)
