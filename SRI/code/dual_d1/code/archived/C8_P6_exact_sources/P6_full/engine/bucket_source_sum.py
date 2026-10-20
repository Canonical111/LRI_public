"""Exact, disjoint disk-bucket summation of complete intermediate sources.
Buckets are keyed by canonical affine GPL letters and scalar logarithms, not
by coefficient values. Every original source is hashed and accounted for.
"""
from pathlib import Path
from functools import lru_cache
from fractions import Fraction as F
import ast,json,hashlib,sys,time,os
ROOT=Path(__file__).resolve().parent.parent
@lru_cache(None)
def affine(text):
 def ev(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return {'':F(n.value)}
  if isinstance(n,ast.Name):return {n.id:F(1)}
  if isinstance(n,ast.UnaryOp):return {k:(-v if isinstance(n.op,ast.USub) else v) for k,v in ev(n.operand).items()}
  if isinstance(n,ast.BinOp):
   a,b=ev(n.left),ev(n.right)
   if isinstance(n.op,(ast.Add,ast.Sub)):
    out=a.copy();sgn=-1 if isinstance(n.op,ast.Sub) else 1
    for k,v in b.items():out[k]=out.get(k,F(0))+sgn*v
    return {k:v for k,v in out.items() if v}
   if isinstance(n.op,ast.Mult):
    if set(a)<= {''}:return {k:a.get('',F(0))*v for k,v in b.items()}
    if set(b)<= {''}:return {k:b.get('',F(0))*v for k,v in a.items()}
   if isinstance(n.op,ast.Div) and set(b)<= {''}:return {k:v/b.get('',0) for k,v in a.items()}
  raise ValueError(('nonaffine letter',text,ast.dump(n)))
 return tuple(sorted((k,v.numerator,v.denominator) for k,v in ev(ast.parse(text.replace('^','**'),mode='eval').body).items() if v))
def split(specpath,folder,buckets=64):
 spec=json.loads(Path(specpath).read_text());folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 for r in spec['inputs']:assert (ROOT/r['path']).is_file(),r['path']
 files=[(folder/f'bucket{i:03}.raw.tmp').open('w') for i in range(buckets)];counts=[0]*buckets;records=[];st=time.time()
 for r in spec['inputs']:
  p=ROOT/r['path'];rows=0
  for line in p.open():
   ww,ll,c=json.loads(line);canonical=[[[list(x) for x in affine(a)] for a in w] for w in ww]
   key=json.dumps([canonical,sorted(ll)],separators=(',',':')).encode();j=int.from_bytes(hashlib.blake2b(key,digest_size=8).digest(),'little')%buckets
   files[j].write(json.dumps([r['weight'],ww,ll,c],separators=(',',':'))+'\n');counts[j]+=1;rows+=1
  records.append({**r,'rows':rows,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});print('PARTITIONED',r['path'],rows,time.time()-st,flush=True)
 for i,f in enumerate(files):f.close();(folder/f'bucket{i:03}.raw.tmp').replace(folder/f'bucket{i:03}.raw.jsonl')
 report={'inputs':records,'counts':counts,'total_rows':sum(counts),'buckets':buckets,'canonical_affine_keys':True,'all_input_sources_present':True,'seconds':time.time()-st}
 (folder/'partition.json').write_text(json.dumps(report,indent=2));print('PARTITION_COMPLETE',sum(counts),flush=True)
def reduce(folder,index):
 from full_runner import load,rm,K,ff,dump,clear,heapq
 folder=Path(folder);raw=folder/f'bucket{index:03}.raw.jsonl';groups={};rows=0;st=time.time()
 for line in raw.open():
  weight,ww,ll,c=json.loads(line);key=tuple(tuple(rm.parseK(a) for a in w) for w in ww),tuple(sorted(ll));c=rm.parseK(c)*K(weight)
  if not c:continue
  g=groups.setdefault(key,{});d=frozenset(c.denf.items());nn=g.get(d,K.ring.zero)+c.numer
  if nn:g[d]=nn
  else:g.pop(d,None)
  rows+=1
 out={};seq=0
 while groups:
  key,g=groups.popitem();heap=[]
  for den,num in g.items():
   nn,dd=ff.cancel_factors(num,dict(den))
   if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,ff.Frac(K,nn,dd)));seq+=1
  while len(heap)>1:
   _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);c=a+b
   if c:heapq.heappush(heap,(len(c.numer)+len(c.denf),seq,c));seq+=1
  if heap:out[key]=heap[0][2]
 dest=folder/f'bucket{index:03}.jsonl';dump(dest,out)
 report={'input_rows':rows,'output_rows':len(out),'input_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-st}
 (folder/f'bucket{index:03}.report.json').write_text(json.dumps(report,indent=2));print('REDUCED',index,rows,len(out),time.time()-st,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='split':split(sys.argv[2],sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 64)
 elif sys.argv[1]=='reduce':reduce(sys.argv[2],int(sys.argv[3]))
