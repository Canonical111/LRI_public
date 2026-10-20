from read_expression import load as load_expr
"""Coefficient-directed exact cutoff normalization.

All raw responses have lower power bound -floor(n/2). The bound follows
from disjoint neutral collision clusters; log/source derivatives do not
worsen powers. Coefficient convolution therefore needs finitely many raw
powers, even when their regular expansions are infinite.
"""
from pathlib import Path
from functools import lru_cache
import sympy as s
import assemble_C6 as ac
ROOT=Path(__file__).resolve().parent
@lru_cache(None)
def identify(atom):
 if isinstance(atom,s.Derivative):
  x=atom.expr;co=dict(atom.variable_count);iv=int(co.get(ac.v,0));idd=int(co.get(ac.d,0))
 else:x=atom;iv=idd=0
 name=str(x.func);kind=name.rstrip('0123456789');n=int(name[len(kind):])
 return n,kind,ac.DERIV[iv,idd]
@lru_cache(None)
def rawpower(atom,p):
 n,k,der=identify(atom)
 # Exact support of the uninserted two-wall radial moments and all
 # charge/tail derivatives: elementary integrals of log^j r/r^2 or /r.
 if n==2 and k=='Z' and p not in (-1,0):return s.S.Zero
 if n==2 and k=='Q' and p not in (0,1):return s.S.Zero
 return ac.ms.pol(n,k,der,p)
def lower(atom):
 n,k,der=identify(atom)
 return 0 if (n==2 and k=='Q') else -(n//2)
@lru_cache(None)
def convolution(atoms,p):
 if not atoms:return s.S.One if p==0 else s.S.Zero
 if len(atoms)==1:return rawpower(atoms[0],p)
 amin=lower(atoms[0]);rmin=sum(lower(a) for a in atoms[1:])
 out=0
 for j in range(amin,p-rmin+1):
  v=rawpower(atoms[0],j)
  if v:out+=v*convolution(atoms[1:],p-j)
 return out

def compute(name,iv=0,idd=0):
 ex=s.expand(s.diff(ac.norms[name],ac.v,iv,ac.d,idd));out=0
 for term in s.Add.make_args(ex):
  atoms=[];co=s.S.One
  for factor in s.Mul.make_args(term):
   base,exp=factor.as_base_exp()
   if isinstance(base,s.Derivative) or (base.is_Function and str(base.func) in ac.rawf):
    assert exp.is_Integer and exp>0,(base,exp)
    atoms.extend([base]*int(exp))
   else:co*=factor
  co=co.subs({ac.v:1,ac.d:0})
  out+=co*convolution(tuple(sorted(atoms,key=str)),0)
 return s.expand(s.expand_log(s.expand(out),force=True))
@lru_cache(None)
def npol(name,iv=0,idd=0):
 fp=ROOT/'series'/f'norm_{name}_{iv}_{idd}.expr'
 if fp.exists():return load_expr(fp)
 ans=compute(name,iv,idd);tmp=fp.with_suffix('.tmp');tmp.write_text(s.sstr(ans, order="none"));tmp.replace(fp)
 print('TARGETED NORM',name,iv,idd,'terms',len(s.Add.make_args(ans)),flush=True)
 return ans

def install():ac.npol=npol

if __name__=='__main__':
 import assemble_C7,json,time
 tests=[('C5',1,0),('C5',2,0),('K6',0,0),('EC3',1,0)]
 out=[]
 for name,i,j in tests:
  st=time.time();old=load_expr(ROOT/'series'/f'norm_{name}_{i}_{j}.expr')
  new=compute(name,i,j);assert s.expand(new-old)==0,(name,i,j)
  record={'normalization':name,'derivative':[i,j],'exact_residual':'0','seconds':time.time()-st};out.append(record);print(record,flush=True)
 (ROOT/'targeted_series_checks.json').write_text(json.dumps(out,indent=2))
