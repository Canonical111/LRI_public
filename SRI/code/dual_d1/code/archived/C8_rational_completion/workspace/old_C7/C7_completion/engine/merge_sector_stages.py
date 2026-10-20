"""Exact linear recombination of disjoint Cauchy-pole sectors.
No integration or finite part is taken in this step.
"""
from pathlib import Path
import json,sys,time,hashlib
from hyperlog_core import K,addto,clean
from run_moment import parseK
ROOT=Path(__file__).resolve().parent
n,kind,der,stage=sys.argv[1:5];n=int(n);stage=int(stage);tag=f'{kind}{n}_{der}'
counts=int(sys.argv[5]) if len(sys.argv)>5 else (n+1)//2
start=time.time();out={};sources=[]
for sector in range(counts):
 f=ROOT/f'{tag}_sector{sector}_stage{stage}.json'
 data=f.read_bytes();sources.append({'file':f.name,'sha256':hashlib.sha256(data).hexdigest()})
 rows=json.loads(data);del data
 print('LOAD',f.name,'rows',len(rows),flush=True)
 for j,(words,logs,c) in enumerate(rows):
  key=(tuple(tuple(parseK(x) for x in w) for w in words),tuple(logs))
  addto(out,key,parseK(c))
  if j%200==0:print('merge',sector,j,'terms',len(out),'seconds',time.time()-start,flush=True)
 parseK.cache_clear();out=clean(out)
 print('SECTOR MERGED',sector,len(out),time.time()-start,flush=True)
rows=[([list(map(str,w)) for w in ww],list(logs),str(c)) for (ww,logs),c in out.items()]
(ROOT/f'{tag}_stage{stage}.json').write_text(json.dumps(rows))
(ROOT/f'{tag}_stage{stage}_merge.json').write_text(json.dumps({'sources':sources,'output_terms':len(out),'seconds':time.time()-start,'method':'exact addition in QQ of rational coefficient functions, before any further integration'},indent=2))
print('MERGED',tag,'terms',len(out),'seconds',time.time()-start,flush=True)
