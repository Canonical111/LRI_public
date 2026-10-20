"""Full (not weight-zero) epsilon^-2 log^0 boundary coefficient from new source.
Only polynomial rational prefactors of degree >=1 can affect this power.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import sys,json,time,hashlib,concurrent.futures
sys.path.insert(0,'/mnt/data/P8_final_run')
import linear_boundary as lb
import period_algebra as pa
ROOT=Path('/mnt/data/P8_final_run/F3_six_kink_completion/P8_terminal_fibration')
def worker(i):
 folder=ROOT/'positive_divergence';folder.mkdir(exist_ok=True);fp=folder/f'b{i:03d}.jsonl';rp=fp.with_suffix('.report.json')
 if fp.exists() and rp.exists():return i
 start=time.time();allp=json.loads((ROOT/'prefactor_apart.json').read_text());poly=[]
 for row in allp:
  poly.append(tuple((p,tuple(z),F(c)) for kind,a,p,z,c in row if kind=='poly' and p>=1))
 groups={};src=ROOT/f'b{i:03d}.tsv';n=0
 for line in src.open():
  key,pid,cs=line.rstrip().split('\t');basis=poly[int(pid)];n+=1
  if not basis:continue
  b=groups.setdefault(key,{})
  for d,z,c in basis:
   pair=(d,z);v=b.get(pair,F(0))+c*F(cs)
   if v:b[pair]=v
   else:b.pop(pair,None)
 out={}
 for key,terms in groups.items():
  w,ll,z=json.loads(key);w=tuple(w);ll=tuple(ll)
  if 1 in ll:continue
  for (degree,zz),c in terms.items():
   zs=tuple(a+b for a,b in zip(z,zz))
   for tail,v in lb.functional('poly',0,degree,w,7,0,True,-2,0):
    tw=tuple(int(a) for a in tail);pair=tw,ll,zs;value=out.get(pair,F(0))+c*v
    if value:out[pair]=value
    else:out.pop(pair,None)
 with fp.open('w') as f:
  for (w,ll,z),c in out.items():f.write(json.dumps([w,ll,z,str(c)],separators=(',',':'))+'\n')
 report={'complete':True,'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'input_rows':n,'output_terms':len(out),'seconds':time.time()-start,'full_constants_retained':True,'definition':'[epsilon^-2 log(epsilon)^0] dimensionless boundary'}
 rp.write_text(json.dumps(report,indent=2));print('FULL_DIVERGENCE',i,len(out),time.time()-start,flush=True);return i
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=2) as p:list(p.map(worker,range(256)))
 raw={}
 for i in range(256):
  for line in (ROOT/'positive_divergence'/f'b{i:03d}.jsonl').open():
   w,ll,z,c=json.loads(line);k=tuple(w),tuple(ll),tuple(z);v=raw.get(k,F(0))+F(c)
   if v:raw[k]=v
   else:raw.pop(k,None)
 full={}
 for (w,ll,z),c in raw.items():
  term=pa.R(w)
  for a in ll:term=pa.mul(term,pa.log(a))
  for zi,power in zip(('Z2','Z3','Z5','Z7'),z):term=pa.mul(term,pa.powp(pa.atom(zi),power))
  pa.add(full,term,c)
 (ROOT/'positive_divergence/actual.expr').write_text(pa.dump(full));print('ACTUAL_FULL_POLY_TERMS',len(full),flush=True)
