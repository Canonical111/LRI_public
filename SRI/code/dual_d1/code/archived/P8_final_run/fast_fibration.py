"""Integer affine-word fibration for the delivered P8 stage-four source.
A letter is a triple (q coefficient, r coefficient, constant).
At this stage every letter is either constant, q+c or r+c; no raw 0 letters.
The exceptional all-q word has regularized value zero. Empty word equals one.
"""
from functools import lru_cache
from collections import defaultdict
import re,json,hashlib,time
Q=(1,0,0);O=(0,0,0)
@lru_cache(None)
def letter(s):
 s=s.replace(' ','')
 if s.startswith('q'):return (1,0,int(s[1:] or '0'))
 if s.startswith('r'):return (0,1,int(s[1:] or '0'))
 return (0,0,int(s))
@lru_cache(maxsize=4000)
def fibrate(w):
 if not w:return {():1}
 if all(a==Q for a in w):return {}
 assert O not in w, ('raw zero letter requires a more general base convention',w)
 ext=(Q,)+w+(O,);out={}
 for i,a in enumerate(w):
  sub=fibrate(w[:i]+w[i+1:])
  if not sub:continue
  for side,sign,b in [(0,1,ext[i]),(1,-1,ext[i+2])]:
   d=tuple(x-y for x,y in zip(b,a))
   if d==O:
    if side==0 and i==0 and a==Q:root=(0,0)
    else:continue
   elif not d[0]:continue
   else:
    assert d[0] in (-1,1)
    root=(-d[1]//d[0],-d[2]//d[0])
   for ww,co in sub.items():
    key=(root,)+ww
    out[key]=out.get(key,0)+sign*co
 return {w:c for w,c in out.items() if c}
@lru_cache(maxsize=6000)
def shuffle(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 out={}
 for w,c in shuffle(a[1:],b).items():out[(a[0],)+w]=out.get((a[0],)+w,0)+c
 for w,c in shuffle(a,b[1:]).items():out[(b[0],)+w]=out.get((b[0],)+w,0)+c
 return out

def fixedletter(s):
 aq,ar,b=letter(s);assert aq==0
 return (ar,b)

def expand_row(w,tail,ll):
 out={}
 for fw,mu in fibrate(tuple(map(letter,w))).items():
  for ww,nu in shuffle(fw,tuple(map(fixedletter,tail[0]))).items():
   key=(ww,tuple(map(fixedletter,tail[1])),tuple(ll))
   out[key]=out.get(key,0)+mu*nu
 return {w:c for w,c in out.items() if c}

def encode_key(key):
 # [q word, r word, explicit logarithms]; every letter uses two small ints.
 return json.dumps(key,separators=(',',':'))

if __name__=='__main__':
 import argparse
 from pathlib import Path
 p=argparse.ArgumentParser();p.add_argument('--source',default='/mnt/data/F3_P8_checkpoint/B8_moving4_total/moving.jsonl');p.add_argument('--directory',default='/mnt/data/P8_final_run/fibration');p.add_argument('--buckets',type=int,default=256);p.add_argument('--limit',type=int)
 a=p.parse_args();root=Path(a.directory);root.mkdir(exist_ok=True,parents=True)
 files=[(root/f'b{i:03d}.tsv.tmp').open('w') for i in range(a.buckets)]
 prefactors=[];pindex={};st=time.time();nr=0;nt=0
 try:
  for nr,line in enumerate(open(a.source),1):
   if a.limit and nr>a.limit:break
   w,tail,ll,c=json.loads(line)
   if c not in pindex:pindex[c]=len(prefactors);prefactors.append(c)
   pid=pindex[c]
   out=expand_row(w,tail,ll)
   for key,mu in out.items():
    text=encode_key(key);idx=int.from_bytes(hashlib.blake2b(text.encode(),digest_size=8).digest(),'little')%a.buckets
    files[idx].write(f'{text}\t{pid}\t{mu}\n');nt+=1
   if nr%1000==0:print('FIBRATION',nr,nt,'cache',fibrate.cache_info(),time.time()-st,flush=True)
 finally:
  for f in files:f.close()
 if a.limit:nr=a.limit
 for i in range(a.buckets):(root/f'b{i:03d}.tsv.tmp').rename(root/f'b{i:03d}.tsv')
 (root/'prefactors.json').write_text(json.dumps(prefactors))
 report={'input_rows':nr,'expanded_rows':nt,'prefactors':len(prefactors),'buckets':a.buckets,'source_sha256':hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),'seconds':time.time()-st,'full_periods':True}
 (root/'report.json').write_text(json.dumps(report,indent=2));print('FINISHED',report)
