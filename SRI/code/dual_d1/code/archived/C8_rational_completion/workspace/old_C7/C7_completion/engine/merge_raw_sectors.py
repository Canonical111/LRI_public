"""Exactly sum disjoint first-pole contributions of a regulated kink moment."""
from pathlib import Path
import json,sys,time,hashlib
from hyperlog_core import K
ROOT=Path(__file__).resolve().parent
n,kind,der=sys.argv[1:4]
tag=f'{kind}{n}_{der}'
start=time.time();out={};inputs=[]
for i in range(4):
 fp=ROOT/f'{tag}_sector{i}_negative.json';rows=json.loads(fp.read_text())
 inputs.append({'file':fp.name,'sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'rows':len(rows)})
 for j,(w,l,c) in enumerate(rows):
  key=(tuple(w),tuple(sorted(l)))
  out[key]=out.get(key,K.zero)+K.from_expr(c)
  if j%500==0: print('sector',i,'row',j,'/',len(rows),'words',len(out),'seconds',time.time()-start,flush=True)
 out={k:c for k,c in out.items() if c}
 print('SECTOR',i,'summed rows',len(out),flush=True)
rows=[(list(w),list(l),str(c)) for (w,l),c in sorted(out.items())]
fp=ROOT/f'{tag}_negative.json';fp.write_text(json.dumps(rows))
record={'method':'exact QQ(e) sum of four disjoint first-variable Cauchy-pole sectors','inputs':inputs,'output':fp.name,'sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'rows':len(rows),'seconds':time.time()-start,'fit_or_numerical_constants_used':False}
(ROOT/f'{tag}_merge_audit.json').write_text(json.dumps(record,indent=2));print('DONE',tag,len(rows),time.time()-start,flush=True)
