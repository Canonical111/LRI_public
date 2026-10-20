"""Full F2 subtraction, with missing raw scalars left as formal symbols.
Every input is exact saved moment data; no guessed U or C8 enters.
"""
from pathlib import Path
from functools import lru_cache
import time,json,hashlib
import sympy as s
import assemble_C6 as ac
import targeted_series as ts
from read_expression import load
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[2]/'data';OUT.mkdir(exist_ok=True)
used={}
A7d,Z6d,E5d,E4d=s.symbols('A7_tail_log Z6_tail_log EA5_tail_finite EZ4_tail_finite')
oldpol=ac.ms.pol
@lru_cache(None)
def pol(n,kind,der='base',p=0):
 key=(n,kind,der,p)
 missing={(7,'A','d',0):A7d*ac.ell,(6,'Z','d',0):Z6d*ac.ell,
          (5,'EA','d',0):E5d,(4,'EZ','d',0):E4d}
 if key in missing:return missing[key]
 ans=oldpol(*key);fp=ROOT/'series'/f'{kind}{n}_{der}_p{p}.expr'
 used[str(fp.relative_to(ROOT))]=hashlib.sha256(fp.read_bytes()).hexdigest();return ans
ac.ms.pol=pol
@lru_cache(None)
def norm(name,i=0,j=0,m=0):
 st=time.time();ex=s.expand(ts.compute(name,i,j)).coeff(ac.ell,m)
 print('NORM',name,i,j,m,len(s.Add.make_args(ex)),time.time()-st,flush=True);return ex
def beta(name):
 fp=ROOT/(name+'_symbolic.expr');used[fp.name]=hashlib.sha256(fp.read_bytes()).hexdigest();return load(fp)
def rat(ex):
 mp={x:s.S.Zero for x in ex.free_symbols if str(x).startswith(('R_','Z'))}
 mp.update({x:s.S.Zero for x in ex.atoms(s.log,s.polylog,s.zeta)})
 return s.expand(ex.xreplace(mp).subs(s.pi,0))
def main():
 st=time.time();b5,b5d,p,c,q,k,P=[beta(x) for x in ['b_check','R','p_check','c_check','q_check','k_check','Pnew']]
 h4=-c/4;h4d=-q/4
 j3=-2*norm('C3',1)+norm('EC3');j3d=-2*norm('C3',1,1)+norm('EC3',0,1)
 pieces={
  'normalization':norm('C7',0,1,1)-A7d+Z6d,
  'ct_C3_b5':-3*(norm('C3',0,1)*b5+norm('C3')*b5d),
  'ct_C5_b3':-5*(norm('C5',0,1)+norm('C5')*p),
  'ct_j1_h6':k-P,
  'ct_j3_h4':-2*(j3d*h4+j3*h4d),
  'ct_j5_known':-4*norm('C5',1,1)+2*(norm('EC5',0,1)-E5d+E4d),
 }
 for n,e in pieces.items():
  e=s.expand(s.expand_log(e,force=True));pieces[n]=e;(OUT/(n+'.expr')).write_text(s.sstr(e,order='none'))
  print(n,len(s.Add.make_args(e)),rat(e),flush=True)
 shift=s.expand(sum(pieces.values()));assert not shift.has(A7d,Z6d,E5d,E4d)
 assert rat(shift)==s.Rational(205131,2),rat(shift)
 (OUT/'F2_lower_shift.expr').write_text(s.sstr(shift,order='none'))
 d={'definition':'U = A7_tail_log - Z6_tail_log + 2 EA5_tail_finite - 2 EZ4_tail_finite + F2_lower_shift','shift_rational':str(rat(shift)),
    'shift_terms':len(s.Add.make_args(shift)),'pieces':{n:{'rat':str(rat(e)),'terms':len(s.Add.make_args(e))} for n,e in pieces.items()},
    'used':used,'seconds':time.time()-st,'unknown_raw_scalar_values_used':False}
 (OUT/'F2_shift_assembly.json').write_text(json.dumps(d,indent=2));print('SHIFT_DONE',d['seconds'],flush=True)
if __name__=='__main__':main()
