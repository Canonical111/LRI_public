"""Replay the complete saved 64-bucket exact scalar sum. Does not reintegrate the kernel."""
from pathlib import Path
from fractions import Fraction as F
import sys,json,hashlib
import period_algebra as pa
ROOT=Path(__file__).resolve().parent.parent
r=json.loads((ROOT/'data/P6_exact_report.json').read_text());poly={};raw={}
assert len(r['input_buckets'])==64
seen=set()
for rec in r['input_buckets']:
 name=Path(rec['path']).name;assert name not in seen;seen.add(name)
 path=ROOT/'data/P6_terminal'/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
 lines=path.read_text().splitlines();assert len(lines)==rec['terms']
 for line in lines:
  w,ll,zm,c=json.loads(line);key=(tuple(map(F,w)),tuple(ll),tuple(zm));v=raw.get(key,F(0))+F(c)
  if v:raw[key]=v
  else:raw.pop(key,None)
assert len(raw)==r['raw_word_terms']
for (w,ll,zm),c in raw.items():
 value=pa.R(w)
 for k in ll:value=pa.mul(value,pa.log(k))
 mon=tuple((z,k) for z,k in zip(['Z2','Z3','Z5','Z7'],zm) if k)
 if mon:value=pa.mul(value,{mon:F(1)})
 pa.add(poly,value,-c)
assert poly.get(())==F(399343,2)
expected=pa.parse_expr((ROOT/'data/P6.expr').read_text())
assert poly==expected
assert hashlib.sha256((ROOT/'data/P6.expr').read_bytes()).hexdigest()==r['expression_sha256']
report={'all_64_buckets_once':True,'raw_word_terms':len(raw),'all_canonical_coefficients_equal':True,'canonical_terms':len(poly),'rational_part':'399343/2','scope':'Exact saved-expression assembly, not fresh raw-kernel integration.'}
(ROOT/'verification/exact_P6_replay.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
