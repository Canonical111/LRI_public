from pathlib import Path
import json,time,resource,gc,hashlib
resource.setrlimit(resource.RLIMIT_AS,(3400*1024**2,3400*1024**2))
import sympy as s
from read_expression import load
ROOT=Path(__file__).resolve().parent;start=time.time();acc={};records=[]
for j in range(61):
 fp=ROOT/f'A7_v_p0_chunk{j:03d}.expr';print('READ',j,'rss',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,flush=True);ex=load(fp)
 for mon in s.Add.make_args(ex):
  co,base=mon.as_coeff_Mul(rational=True);acc[base]=acc.get(base,s.S.Zero)+co
 records.append({'file':fp.name,'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()});del ex
 print('ADDED',j,'bases',len(acc),'rss',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,flush=True)
 s.core.cache.clear_cache();gc.collect()
print('BUILD FINAL',flush=True)
out=s.Add(*(co*base for base,co in acc.items() if co));print('BUILT',len(s.Add.make_args(out)),flush=True)
dst=ROOT/'series'/'A7_v_p0.expr';dst.write_text(s.sstr(out, order="none"));print('WRITTEN',flush=True)
(ROOT/'A7_v_p0_extraction_audit.json').write_text(json.dumps({'method':'exact linear chunk decomposition and rational monomial sum','input_sha256':hashlib.sha256((ROOT/'A7_v_negative.json').read_bytes()).hexdigest(),'chunks':records,'terms':len(s.Add.make_args(out)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'seconds':time.time()-start},indent=2))
