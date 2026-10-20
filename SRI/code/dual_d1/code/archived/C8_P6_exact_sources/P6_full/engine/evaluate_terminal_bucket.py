"""Exact full-period functional after canonical rational partial fractions.
Every singular and polynomial part is retained. All operations are over Q.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import json,hashlib,time,sys,gc
sys.path.insert(0,str(Path(__file__).resolve().parent))
import linear_boundary as lb

def _run(folder,i,N,kap,interval):
 folder=Path(folder);src=folder/f'b{i:03d}.tsv';base=folder/'terminal';base.mkdir(exist_ok=True);dest=base/f'b{i:03d}.jsonl';rp=base/f'b{i:03d}.report.json'
 sh=hashlib.sha256(src.read_bytes()).hexdigest()
 if dest.exists() and rp.exists():
  r=json.loads(rp.read_text());assert r['input_sha256']==sh and r['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest();return r
 st=time.time();n=0;groups={}
 for line in src.open():
  key,pid,c=line.rstrip().split('\t');pid=int(pid);c=F(c);d=groups.setdefault(key,{})
  v=d.get(pid,F(0))+c
  if v:d[pid]=v
  else:d.pop(pid,None)
  n+=1
 print('GROUPED_TERMINAL',i,n,len(groups),time.time()-st,flush=True)
 apart=json.loads((folder/'prefactor_apart.json').read_text());out={};nkey=0;nbasis=0;strictpos=0;zero=0
 @lb.lru_cache(maxsize=50000)
 def basis(pid):return tuple((k,F(a),p,tuple(zz),F(c)) for k,a,p,zz,c in apart[pid])
 while groups:
  key,terms=groups.popitem();ww,ll,zm=json.loads(key);w=tuple(ww);ll=tuple(ll);zm=tuple(zm);bs={}
  for pid,c in terms.items():
   for kind,a,p,zz,b in basis(pid):
    zsum=tuple(i+j for i,j in zip(zm,zz));ky=(kind,a,p,zsum);v=bs.get(ky,F(0))+b*c
    if v:bs[ky]=v
    else:bs.pop(ky,None)
  if 1 in ll:continue # explicit log(epsilon) has no finite log-free term
  for (kind,a,p,zsum),c in bs.items():
   for tail,b in lb.functional(kind,a,p,w,N,kap,interval):
    tw=tuple(int(t) if t.denominator==1 else str(t) for t in map(F,tail));ky=(tw,ll,zsum);v=out.get(ky,F(0))+c*b
    if v:out[ky]=v
    else:out.pop(ky,None)
   nbasis+=1
  nkey+=1
  if nkey%1000==0:print('TERMINAL',i,nkey,'out',len(out),'basis',nbasis,time.time()-st,flush=True)
 tmp=dest.with_suffix('.tmp')
 with tmp.open('w') as f:
  for (w,ll,zm),c in out.items():f.write(json.dumps([w,ll,zm,str(c)],separators=(',',':'))+'\n')
 tmp.replace(dest)
 r={'complete':True,'input_rows':n,'nonzero_word_groups':nkey,'basis_terms':nbasis,'output_terms':len(out),'kappa':kap,'offset':N,'interval':interval,'rational_projection_preliminary':str(out.get(((),(),(0,0,0,0)),F(0))),'input_sha256':sh,'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-st,'full_constant_periods_retained':True}
 rp.write_text(json.dumps(r,indent=2));print('TERMINAL_DONE',i,r,flush=True);return r
def run(folder,i,N,kap,interval):
 import fcntl
 folder=Path(folder);ld=folder/'terminal';ld.mkdir(exist_ok=True)
 with (ld/f'b{i:03d}.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  return _run(folder,i,N,kap,interval)
if __name__=='__main__':run(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),bool(int(sys.argv[5])))
