"""Exact final-variable fibration with full endpoint constants.
Coefficients are rational polynomials in Z2,Z3,Z5,Z7, recorded as monomials.
For the P8 source there are no coalescing zero letters, hence all coefficients
are integers. The general path also handles zero/moving endpoint words.
"""
from functools import lru_cache
from fractions import Fraction as F
from collections import defaultdict
from pathlib import Path
import json,re,time,hashlib,sys
ZERO=(0,0);X=(1,0);unit=(0,0,0,0)
@lru_cache(None)
def let(s):
 s=s.replace(' ','')
 if s.startswith('r'):return (1,int(s[1:] or '0'))
 return (0,int(s))
@lru_cache(maxsize=40000)
def shuffle(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 out={}
 for w,c in shuffle(a[1:],b).items():out[(a[0],)+w]=out.get((a[0],)+w,0)+c
 for w,c in shuffle(a,b[1:]).items():out[(b[0],)+w]=out.get((b[0],)+w,0)+c
 return out

def plus(out,key,c):
 if c:
  x=out.get(key,F(0))+c
  if x:out[key]=x
  else:out.pop(key,None)
TABLE=None

def gettab():
 global TABLE
 if TABLE is None:
  import sympy as s
  zz=s.symbols('Z2 Z3 Z5 Z7');data=json.loads((Path(__file__).resolve().parent/'binary_table7.json').read_text());TABLE={}
  for k,v in data['table'].items():
   pol=s.Poly(s.sympify(v),*zz);TABLE[tuple(map(int,k.split(',')))]=tuple((m,F(int(c.p),int(c.q))) for m,c in pol.terms())
 return TABLE
@lru_cache(None)
def phi(w):
 if not w:return ((unit,F(1)),)
 if all(a==w[0] for a in w):return ()
 if w[0]==1 or w[-1]==0:
  head=w[0]==1;sh=shuffle((1,) if head else (0,),w[1:] if head else w[:-1]).copy();mu=sh.pop(w);out={}
  for ww,c in sh.items():
   for z,a in phi(ww):plus(out,z,-F(c,mu)*a)
  return tuple(out.items())
 idx=[];n=0
 for b in w:
  n+=1
  if b:idx.append(n);n=0
 assert n==0
 return tuple((z,(-1)**len(idx)*c) for z,c in gettab()[tuple(idx)])
@lru_cache(None)
def scaled_phi(w):
 if not w:return {((),unit):F(1)}
 if not any(w):return {((0,)*len(w),unit):F(1)}
 if w[-1]!=0:return {((),z):c for z,c in phi(w)}
 sh=shuffle((0,),w[:-1]).copy();mu=sh.pop(w);out={}
 for (ww,z),c in scaled_phi(w[:-1]).items():plus(out,((0,)+ww,z),c*(len(ww)+1))
 for other,n in sh.items():
  for key,c in scaled_phi(other).items():plus(out,key,-n*c)
 return {key:c/mu for key,c in out.items() if c}
@lru_cache(maxsize=15000)
def fibrate(w):
 if not w:return {((),unit):F(1)}
 if all(a in (ZERO,X) for a in w):return scaled_phi(tuple(int(a==X) for a in w))
 ext=(X,)+w+(ZERO,);out={}
 for i,a in enumerate(w):
  low=fibrate(w[:i]+w[i+1:])
  for side,sg,b in [(0,1,ext[i]),(1,-1,ext[i+2])]:
   d=(b[0]-a[0],b[1]-a[1])
   if d==ZERO:
    if side==0 and i==0 and a==X:root=0
    else:continue
   elif not d[0]:continue
   else:
    assert d[0] in (-1,1);root=-d[1]//d[0]
   for (ww,z),c in low.items():plus(out,((root,)+ww,z),sg*c)
 return out

@lru_cache(maxsize=18000)
def fibrate_int(w):
 if not w:return {():1}
 if all(a==X for a in w):return {}
 assert ZERO not in w
 ext=(X,)+w+(ZERO,);out={}
 for i,a in enumerate(w):
  low=fibrate_int(w[:i]+w[i+1:])
  for side,sg,b in [(0,1,ext[i]),(1,-1,ext[i+2])]:
   d=(b[0]-a[0],b[1]-a[1])
   if d==ZERO:
    if side==0 and i==0 and a==X:root=0
    else:continue
   elif not d[0]:continue
   else:
    assert d[0] in (-1,1);root=-d[1]//d[0]
   for ww,c in low.items():
    key=(root,)+ww;out[key]=out.get(key,0)+sg*c
 return {key:c for key,c in out.items() if c}

def expand(w,tail,ll):
 assert len(tail)==1
 tw=tuple(int(a) for a in tail[0]);out={}
 aw=tuple(map(let,w))
 if ZERO not in aw:
  for fw,c in fibrate_int(aw).items():
   for sw,m in shuffle(fw,tw).items():
    key=(sw,tuple(ll),unit);out[key]=out.get(key,0)+c*m
  return {key:c for key,c in out.items() if c}
 for (fw,z),c in fibrate(aw).items():
  for sw,m in shuffle(fw,tw).items():plus(out,(sw,tuple(ll),z),c*m)
 return out

def run(source,dest,nb=128):
 source=Path(source);dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
 fs=[(dest/f'b{i:03d}.tsv.tmp').open('w') for i in range(nb)]
 prefs=[];pid={};nr=0;nt=0;zeros=0;st=time.time()
 for line in source.open():
  w,tail,ll,ct=json.loads(line);nr+=1
  if ct not in pid:pid[ct]=len(prefs);prefs.append(ct)
  if '0' in w:zeros+=1
  for key,c in expand(w,tail,ll).items():
   text=json.dumps(key,separators=(',',':'));h=int.from_bytes(hashlib.blake2b(text.encode(),digest_size=8).digest(),'little')%nb
   fs[h].write(f'{text}\t{pid[ct]}\t{c}\n');nt+=1
  if nr%2000==0:print('TERMINAL_FIBRATE',source.name,nr,nt,len(prefs),time.time()-st,flush=True)
 for f in fs:f.close()
 for i in range(nb):(dest/f'b{i:03d}.tsv.tmp').rename(dest/f'b{i:03d}.tsv')
 (dest/'prefactors.json').write_text(json.dumps(prefs))
 rep={'complete':True,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_rows':nr,'expanded_rows':nt,'prefactors':len(prefs),'coalescing_zero_source_rows':zeros,'sum_buckets':nb,'full_constants':True,'seconds':time.time()-st}
 (dest/'report.json').write_text(json.dumps(rep,indent=2));print('TERMINAL_FIBRATE_DONE',rep,flush=True)
if __name__=='__main__':run(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 128)
