"""Exact rational log residue from the derivative of the hard-core boundary.
B(a)=a sum_faces int W D insertion, so pi0[a^0 log(a)^0] B = -R.
Reflection leaves faces k=1,2,3 with multiplicities 2,2,1 for n=6.
"""
from pathlib import Path
import json,time,argparse,gc,os
from fractions import Fraction as F
if os.environ.get('R6_NATIVE')=='1':
 import native_poly;native_poly.install()
import hyperlog_core as hc
if os.environ.get('R6_ACCEL')=='1':
 import exact_acceleration;exact_acceleration.install()
if os.environ.get('R6_LINEAR')=='1':
 import native_linear;native_linear.install()
if os.environ.get('R6_MOD')=='1':
 import native_mod;native_mod.install()
from hyperlog_core import *
import ordered_moments as om
import terminal_projection as tp
import rebuild_rational as rr
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'boundary';OUT.mkdir(exist_ok=True)

def init_face(n,face,deriv):
 N=n-2
 ids=[0]+[i if i<face else i-1 for i in range(1,n)]
 coords=[i*e+(GEN[j] if j else K.zero) for i,j in enumerate(ids)]
 W=e*(1-coords[-1])*sum((coords[i+1]-coords[i] for i in range(0,n,2)),K.zero)
 for i in range(n):
  for j in range(i+1,n):W*=(coords[j]-coords[i])**(2*(-1)**(i+j))
 lv={};ld={}
 for i in range(n):
  for j in range(i+1,n):
   ia,ib=ids[i],ids[j];c=(j-i)*e
   if ia==ib:continue  # only log(k*a), which has no constant rational projection
   L={};words=[()]*N
   if ia:
    words[ia-1]=(GEN[ib]+c,);L[tuple(words),()]=K.one;words[ia-1]=()
   words[ib-1]=(-c,);L[tuple(words),()]=K.one
   for key,co in L.items():addto(lv,key,2*(-1)**(i+j)*co)
   if 'd' in deriv:
    for key,co in om.multiply(L,L,N).items():addto(ld,key,(-1)**(i+j)*co)
 if deriv=='base':ins={(tuple([()]*N),()):K.one}
 elif deriv=='v':ins=clean(lv)
 elif deriv=='vv':ins=om.multiply(clean(lv),clean(lv),N)
 elif deriv=='d':ins=clean(ld)
 elif deriv=='vd':
  ins=om.multiply(clean(lv),clean(ld),N)
  for key,co in ld.items():addto(ins,key,co)
 else:raise ValueError(deriv)
 return W,clean(ins),N,ids

def first(W,ins,N):
 pp,po=apart(W,1);blocks=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
 out={};st=time.time()
 print('BOUNDARY_FIRST blocks',len(blocks),'insertion',len(ins),flush=True)
 for bi,(kind,root,power,C) in enumerate(blocks):
  local={}
  for (words,logs),co in ins.items():
   ant=integrate_basis(kind,root,power,words[0],1)
   hc.audit_basis(kind,root,power,words[0],1)
   for wa,c in ant.items():
    for wb,cb in endpoint_value(c,wa,1,GEN[2]).items():
     for wf,mu in endpoint_fibrate(wb,2).items():
      for wn,mv in shuffle(wf,words[1]).items():
       keys=list(words);keys[0]=();keys[1]=wn
       addto(local,(tuple(keys),()),cb*mu*mv*co)
    for wb,cb in endpoint_value(c,wa,1,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[0]=()
     addto(local,(tuple(keys),()),-cb*co)
  for key,c in clean(local).items():addto(out,key,c*C)
  print('FIRST_BLOCK',bi+1,len(blocks),'out',len(out),'seconds',time.time()-st,flush=True)
 return clean(out)

def run(n,face,deriv,stop=4,resume=0):
 st=time.time();N=n-2;tag=f'B{n}_{deriv}_f{face}'
 if resume:
  expr=rr.load(OUT/f'{tag}_stage{resume}.jsonl');begin=resume+1;rr.clear()
 else:
  W,ins,N,ids=init_face(n,face,deriv)
  print('INIT',tag,'seconds',time.time()-st,'terms',len(ins),'ids',ids,flush=True)
  expr=first(W,ins,N);rr.dump(OUT/f'{tag}_stage1.jsonl',expr);begin=2
  print('FIRST_DONE',tag,len(expr),'seconds',time.time()-st,flush=True);rr.clear()
 for idx in range(begin,min(stop,N-1)+1):
  out={};items=list(expr.items()) if isinstance(expr,dict) else expr
  for j,((words,logs),R) in enumerate(items):
   active=words[idx-1];ant=integrate_rat(R,active,idx)
   audit_primitive(ant,R,active,idx)
   for wa,c in ant.items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
     for wf,mu in endpoint_fibrate(wb,idx+1).items():
      for wn,mv in shuffle(wf,words[idx]).items():
       keys=list(words);keys[idx-1]=();keys[idx]=wn
       addto(out,(tuple(keys),()),cb*mu*mv)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[idx-1]=()
     addto(out,(tuple(keys),()),-cb)
   if j%20==0:print('PROGRESS',tag,'stage',idx,j+1,len(items),'out',len(out),'seconds',time.time()-st,flush=True)
  expr=clean(out);rr.dump(OUT/f'{tag}_stage{idx}.jsonl',expr);rr.clear()
  print('STAGE_DONE',tag,idx,len(expr),'seconds',time.time()-st,flush=True)
 if stop>=N:
  result=F(0);items=list(expr.items()) if isinstance(expr,dict) else expr
  for j,((words,logs),c) in enumerate(items):
   assert not any(words[:-1]);w=tuple(tp.field_letter(a,N,e) for a in words[-1])
   vals=tp.apply_field(c,w,0,n-1,((0,0),),qindex=N);result+=vals[0]
   if j%100==0:print('TERM',tag,j,len(items),str(result),flush=True)
  d={'definition':'pi0[a^0 log(a)^0] a times one hard-core face of partial_v partial_delta Qn' if deriv=='vd' else deriv,'n':n,'face':face,'boundary_constant':str(result),'residue_contribution':str(-result),'rows':len(expr),'audits':hc.AUDIT_METHODS,'seconds':time.time()-st}
  (OUT/f'{tag}_result.json').write_text(json.dumps(d,indent=2));print('RESULT',d,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=6);p.add_argument('--face',type=int,default=1);p.add_argument('--deriv',default='vd');p.add_argument('--stop',type=int,default=4);p.add_argument('--resume',type=int,default=0);a=p.parse_args();run(a.n,a.face,a.deriv,a.stop,a.resume)
