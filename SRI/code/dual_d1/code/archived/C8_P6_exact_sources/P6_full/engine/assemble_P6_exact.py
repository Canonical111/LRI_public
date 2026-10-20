"""Complete exact addition and canonicalization; no scalar missing value may be zero."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,sys,time,re
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT.parent/'C8_full_numerical_completion/code'))
import period_algebra as pa
start=time.time();poly={};srcs=[];raw={}
for i in range(64):
 p=ROOT/'terminal/terminal'/f'b{i:03}.jsonl';rp=p.with_suffix('.report.json');r=json.loads(rp.read_text());assert r['complete'];assert r['output_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
 for line in p.open():
  w,ll,zm,c=json.loads(line);key=(tuple(map(F,w)),tuple(ll),tuple(zm));v=raw.get(key,F(0))+F(c)
  if v:raw[key]=v
  else:raw.pop(key,None)
 srcs.append({'path':str(p.relative_to(ROOT)),'sha256':r['output_sha256'],'terms':r['output_terms']})
 print('READ_BUCKET',i,len(raw),flush=True)
rawout=ROOT/'P6_boundary_words.jsonl'
with rawout.open('w') as f:
 for (w,ll,zm),c in raw.items():f.write(json.dumps([list(map(str,w)),ll,zm,str(c)])+'\n')
for j,((w,ll,zm),c) in enumerate(raw.items()):
 p=pa.R(w)
 for k in ll:p=pa.mul(p,pa.log(k))
 mon=tuple((z,k) for z,k in zip(['Z2','Z3','Z5','Z7'],zm) if k)
 if mon:p=pa.mul(p,{mon:F(1)})
 pa.add(poly,p,-c)
 if j%20000==0:print('REDUCED_WORD',j,len(poly),time.time()-start,flush=True)
assert poly.get(())==F(399343,2),('post-integration rational check',poly.get(()))
p=ROOT/'P6.expr';p.write_text(pa.dump(poly))
for word in re.findall(r'\bR_[A-Za-z0-9_]+',p.read_text()):
 assert all(a=='0' or (a.startswith('m') and a[1:].isdigit()) for a in word.split('_')[1:]),word
report={'status':'complete_exact_period_expression','definition':'[epsilon^0 log epsilon] partial_v partial_delta Q6 at v=1,delta=0','rational_projection':'399343/2','input_buckets':srcs,'raw_word_terms':len(raw),'canonical_terms':len(poly),'expression_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rational_value_used_only_as_post_integral_check':True,'seconds':time.time()-start}
(ROOT/'P6_exact_report.json').write_text(json.dumps(report,indent=2));(ROOT/'eval_manifest.json').write_text(json.dumps({'P6':str(p)}));print(json.dumps({k:v for k,v in report.items() if k!='input_buckets'},indent=2),flush=True)
