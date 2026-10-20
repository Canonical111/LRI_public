from full_runner import *
import sympy as s
from boundary_jet_functional import jet_basis
import asymptotic_gpl as ag
sys.path.insert(0,'/mnt/data/P8_final_run');import linear_boundary as lb
source=ROOT/'P8_pieces/r000000_0100/stage5.jsonl';lines=source.read_text().splitlines();indices=[0,1,2,17,52,89,139,247,601,1207,4021,17013];st=time.time();checks=[]
for i in indices:
 ww,ll,tx=json.loads(lines[i]);assert not any(ww[:-1]);w=tuple(map(int,ww[-1]));rat=rm.parseK(tx);pp,po=apart(rat,6);fast=0;ref=0
 for kin,a,p,c in [('poly',0,p,c) for p,c in pp.items()]+[('pole',int(a.as_expr()),p,c) for (a,p),c in po.items()]:
  val=s.expand(sum(s.Rational(mu.numerator,mu.denominator)*ag.Z(tuple(int(k) for k in tw)) for tw,mu in lb.functional(kin,a,p,w,7,0,True)))
  fast+=c.as_expr()*val;ref+=c.as_expr()*jet_basis(kin,a,p,w,6,7,0,0)
 diff=s.expand(fast-ref);assert diff==0,(i,diff)
 checks.append({'source_row':i,'word':w,'rational_primitive_terms':len(pp)+len(po),'exact_equal':True});print('ACTUAL_TERMINAL_EXACT',i,time.time()-st,flush=True)
(ROOT/'actual_terminal_slice_check.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':checks,'all_exact':True,'seconds':time.time()-st},indent=2))
