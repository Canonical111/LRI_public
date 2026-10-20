"""Full-period cutoff coefficients of a boundary response (constant and poles).
These are extracted from exact primitives BEFORE substituting the cutoff.
This routine does not assume that divergent coefficients have weight zero.
"""
from boundary_terminal_fast import *
from math import comb
@lru_cache(None)
def jet_weight(r,k,kappa,N,power,log):
 d=power-kappa+r
 if d<0 or k<log:return s.S.Zero
 if k-log>d:return s.S.Zero
 a=s.Symbol('a');poly=s.prod(a-j for j in range(d))/s.Integer(factorial(d))
 return s.expand(s.Integer(-N)**d*comb(k,log)*(-1)**log*s.diff(poly,a,k-log).subs(a,r))
@lru_cache(maxsize=150000)
def jet_word(word,p,kappa,N,power,log):
 return s.expand(sum(jet_weight(p-n,k,kappa,N,power,log)*big_coefficient(word,n,k)
  for n in range(max(0,power-kappa+p+1)) for k in range(log,len(word)+1) if jet_weight(p-n,k,kappa,N,power,log)))
def jet_ant(ant,kappa,idx,N,power,log):
 out=0
 for w,c in ant.items():
  word=tuple(int(a) for a in w)
  for p,co in polynomial_part(c,idx).items():
   if p>=kappa-power:out+=scalar(str(co))*jet_word(word,p,kappa,N,power,log)
 return s.expand(out)
@lru_cache(maxsize=20000)
def jet_basis(kin,a,p,ints,idx,N,power,log):
 root=K(a);w=tuple(K(x) for x in ints);audit_basis(kin,root,p,w,idx);ant=integrate_basis(kin,root,p,w,idx)
 val=jet_ant(ant,0,idx,N,power,log)-N*jet_ant(ant,1,idx,N,power,log)
 if kin=='poly':extra=integrate_basis('poly',K.zero,p+1,w,idx)
 else:
  extra={}
  aa=integrate_basis('poly',K.zero,0,w,idx) if p==1 else integrate_basis('pole',root,p-1,w,idx)
  for ww,c in aa.items():addto(extra,ww,c)
  for ww,c in ant.items():addto(extra,ww,root*c)
 val-=jet_ant(extra,1,idx,N,power,log)
 if power==0 and log==0:
  for ww,c in ant.items():
   for w0,c0 in endpoint_value(c,ww,idx,K.zero,lower=True).items():assert not w0;val-=scalar(str(c0))
 return s.expand(val)
if __name__=='__main__':
 # Exact equivalence to the separately derived scalar functional on a nontrivial
 # selection of actual source primitives, plus a fresh polynomial-log check.
 fp=ROOT/'B8_v_f1/b00/stage5.jsonl';count=0
 for line in fp.open():
  ww,ll,tx=json.loads(line);w=tuple(int(rm.parseK(x)) for x in ww[-1]);rr=rm.parseK(tx);pol,po=apart(rr,6)
  for p,c in pol.items():assert s.expand(jet_basis('poly',0,p,w,6,7,0,0)-basis('poly',0,p,w,6,7))==0;count+=1
  for (a,p),c in po.items():assert s.expand(jet_basis('pole',int(a),p,w,6,7,0,0)-basis('pole',int(a),p,w,6,7))==0;count+=1
  if count>=60:break
 print('JET SCALAR CHECK',count,flush=True)
 x=s.Symbol('x',positive=True);l=s.Symbol('ell');checks=0
 for m in range(4):
  for k in range(4):
   expression=(1/x-7)**m*s.log(1/x-7)**k
   series=s.expand(s.series(expression,x,0,2).removeO().expand(log=True,force=True)).subs(s.log(x),l)
   for p in range(-3,1):
    for j in range(4):assert s.simplify(series.coeff(x,p).coeff(l,j)-jet_weight(m,k,0,7,p,j))==0;checks+=1
 report={'primitive_scalar_equal':count,'polynomial_log_coefficients':checks,'all_exact':True}
 (ROOT/'data/boundary_jet_unit_checks.json').write_text(json.dumps(report,indent=2));print('JET UNIT CHECKS',report,flush=True)
