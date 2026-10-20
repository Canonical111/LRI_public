"""Exact finite/log coefficient convolutions with explicit scalar coverage.
Unlike a partial logarithmic polynomial, an absent scalar is never zero.
"""
from pathlib import Path
from functools import lru_cache
import json,sympy as s,hashlib,time
import assemble_C8 as a8
ac=a8.ac
from read_expression import load
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'scalar_norms';CACHE.mkdir(exist_ok=True)
class MissingScalar(FileNotFoundError):pass
@lru_cache(None)
def identify(atom):
 if isinstance(atom,s.Derivative):
  f=atom.expr;ct=dict(atom.variable_count);iv=int(ct.get(ac.v,0));dd=int(ct.get(ac.d,0))
 else:f=atom;iv=dd=0
 name=str(f.func);kind=name.rstrip('0123456789');n=int(name[len(kind):]);return n,kind,ac.DERIV[iv,dd]
def lower(atom):
 n,k,d=identify(atom);return 0 if n==2 and k=='Q' else -(n//2)
@lru_cache(None)
def raw(atom,p,m):
 n,k,der=identify(atom);tag=f'{k}{n}_{der}'
 if n==2 and k=='Z' and p not in (-1,0):return s.S.Zero
 if n==2 and k=='Q' and p not in (0,1):return s.S.Zero
 key=f'{tag}|{p}|{m}';indexfile=ROOT/'raw_scalar_index.json';index=json.loads(indexfile.read_text()) if indexfile.exists() else {}
 if key in index:
  rec=index[key];fp=Path(rec['expression']);assert hashlib.sha256(fp.read_bytes()).hexdigest()==rec['expression_sha256'];return load(fp)
 fp=ROOT/'raw_scalars'/f'{tag}_p{p}_l{m}.expr'
 if fp.exists():return load(fp)
 whole=ROOT/'series'/f'{tag}_p{p}.expr'
 if whole.exists():ans=s.expand(load(whole)).coeff(ac.ell,m)
 else:
  if not (ROOT/f'{tag}_negative.json').exists():raise MissingScalar(key)
  ans=ac.ms.val(n,k,der,p,m)
 fp.parent.mkdir(exist_ok=True);fp.write_text(s.sstr(ans,order='none'));return ans
@lru_cache(None)
def conv(atoms,p,m):
 if not atoms:return s.S.One if p==0 and m==0 else s.S.Zero
 if len(atoms)==1:return raw(atoms[0],p,m)
 lo=lower(atoms[0]);rem=sum(map(lower,atoms[1:]));out=0
 for pp in range(lo,p-rem+1):
  for mm in range(m+1):
   x=raw(atoms[0],pp,mm)
   if x:
    y=conv(atoms[1:],p-pp,m-mm)
    if y:out+=x*y
 return out
@lru_cache(None)
def norm(stem,iv,dd,m):
 fp=CACHE/f'{stem}_v{iv}_d{dd}_l{m}.expr'
 if fp.exists():return load(fp)
 start=time.time();ex=s.expand(s.diff(ac.norms[stem],ac.v,iv,ac.d,dd));out=0
 for term in s.Add.make_args(ex):
  atoms=[];co=s.S.One
  for factor in s.Mul.make_args(term):
   base,exp=factor.as_base_exp()
   if isinstance(base,s.Derivative) or (base.is_Function and str(base.func) in ac.rawf):
    assert exp.is_Integer and exp>0;atoms.extend([base]*int(exp))
   else:co*=factor
  out+=co.subs({ac.v:1,ac.d:0})*conv(tuple(sorted(atoms,key=str)),0,m)
 ans=s.expand(s.expand_log(out,force=True));fp.write_text(s.sstr(ans,order='none'));print('SCALAR_NORM',stem,iv,dd,m,len(s.Add.make_args(ans)),time.time()-start,flush=True);return ans
@lru_cache(None)
def evalnormf(ex):
 if isinstance(ex,s.Derivative):
  ff=ex.expr;co=dict(ex.variable_count);iv=int(co.get(ac.v,0));dd=int(co.get(ac.d,0))
 else:ff=ex;iv=dd=0
 stem,which=str(ff.func).rsplit('_',1);return norm(stem,iv,dd,0 if which=='f' else 1)
def install():ac.evalnormf=evalnormf
if __name__=='__main__':
 import sys
 install()
 for name in sys.argv[1:]:
  try:ac.betaexpr(a8.needed[name],name)
  except MissingScalar as e:print('MISSING_FULL_SCALAR',name,str(e),flush=True)
