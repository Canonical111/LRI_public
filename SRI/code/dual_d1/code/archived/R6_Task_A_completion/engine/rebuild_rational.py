"""Fresh regulated integrations in the weight-zero constant quotient.
Only explicit log(e) degrees 0 and 1 can enter the requested output.
Pure positive-weight constants are projected out, not variable GPLs.
"""
from pathlib import Path
import os,sys,json,time,gc,argparse
from fractions import Fraction as F
from functools import lru_cache
import hyperlog_core as hc
import run_moment as rm
import ordered_moments as om
from hyperlog_core import *
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'fresh';OUT.mkdir(exist_ok=True)
hc.phi=lambda w: K.one if not w else K.zero
hc.scaled_phi.cache_clear();hc.endpoint_fibrate.cache_clear()
_old_initial=rm.initial

def initial(n,kind,deriv,kernel=True):
 expr,N=_old_initial(n,kind,deriv,kernel)
 out={}
 for (words,logs),co in expr.items():
  if len(logs)>1:continue
  addto(out,(words,(1,)*len(logs)),co)
 return clean(out),N
rm.initial=initial

def dump(path,expr):
 items=expr.items() if isinstance(expr,dict) else expr
 temp=path.with_suffix('.tmp')
 with temp.open('w') as f:
  for (ww,ll),c in items:
   if c:f.write(json.dumps([[list(map(str,w)) for w in ww],len(ll),str(c)],separators=(',',':'))+'\n')
 temp.replace(path)

def load(path):
 out=[]
 for line in path.open():
  ww,ll,cs=json.loads(line)
  out.append(((tuple(tuple(rm.parseK(s) for s in w) for w in ww),(1,)*ll),rm.parseK(cs)))
 return out

def clear():
 for f in [hc.apart,hc.integrate_basis,hc._pc,hc.endpoint_fibrate,hc.fibrate,hc.local_gpl,hc.audit_basis,rm.parseK,hc.shuffle]:
  f.cache_clear()
 import factored_field as ff
 for f in [ff.lininfo,ff.modular_coeffs,ff.divide_linear_cached]:f.cache_clear()
 
 if 'native_poly' in sys.modules:
  sys.modules['native_poly'].encoded.cache_clear()
 gc.collect()
 try:
  import ctypes;ctypes.CDLL(None).malloc_trim(0)
 except Exception:pass

def run(n,kind,deriv,sector,stop,resume):
 rm.SECTOR=sector
 name=f'{kind}{n}_{deriv}_s{sector}'
 start=time.time();N=n if kind.startswith('E') else n-1
 if resume:
  expr=load(OUT/f'{name}_stage{resume}.jsonl');begin=resume+1;clear()
 else:
  expr,N=rm.factored_first(n,kind,deriv)
  out={}
  for key,co in expr:addto(out,key,co)
  expr=clean(out);dump(OUT/f'{name}_stage1.jsonl',expr);begin=2
  print('FIRST_DONE',name,'terms',len(expr),'seconds',time.time()-start,flush=True)
  if stop==1:return
 audits=0
 for idx in range(begin,min(stop,N-1)+1):
  out={};items=list(expr.items()) if isinstance(expr,dict) else expr
  for j,((words,logs),R) in enumerate(items):
   active=words[idx-1];ant=integrate_rat(R,active,idx)
   audit_primitive(ant,R,active,idx);audits+=1
   for wa,c in ant.items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
     for wf,mu in endpoint_fibrate(wb,idx+1).items():
      for wn,mv in shuffle(wf,words[idx]).items():
       keys=list(words);keys[idx-1]=();keys[idx]=wn
       addto(out,(tuple(keys),logs),cb*mu*mv)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[idx-1]=()
     addto(out,(tuple(keys),logs),-cb)
   if j%20==0:print('PROGRESS',name,'stage',idx,j+1,'/',len(items),'out',len(out),'seconds',time.time()-start,flush=True)
  expr=clean(out);dump(OUT/f'{name}_stage{idx}.jsonl',expr)
  print('STAGE_DONE',name,idx,'terms',len(expr),'seconds',time.time()-start,flush=True)
  clear()
 (OUT/f'{name}_audit.json').write_text(json.dumps({'stage':min(stop,N-1),'terms':len(expr),'audits':audits,'methods':hc.AUDIT_METHODS,'seconds':time.time()-start},indent=2))
 if stop>=N:
  import terminal_projection as tp
  demands=((0,1),(-2,0),(-2,1),(-1,0),(-1,1))
  total=[F(0)]*len(demands);items=list(expr.items()) if isinstance(expr,dict) else expr
  for j,((words,logs),c) in enumerate(items):
   assert not any(words[:-1]);w=tuple(tp.field_letter(a,N,e) for a in words[-1])
   ans=tp.apply_field(c,w,len(logs),n-1,demands,qindex=N)
   total=[a+b for a,b in zip(total,ans)]
   if j%50==0:print('TERMINAL',name,j,'/',len(items),'values',list(map(str,total)),flush=True)
  result={'values':list(map(str,total)),'demands':demands,'stage4_input':name,'seconds':time.time()-start}
  (OUT/f'{name}_result.json').write_text(json.dumps(result,indent=2));print('RESULT',result,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sector',type=int,default=-1);p.add_argument('--stop',type=int,default=3);p.add_argument('--resume',type=int,default=0);p.add_argument('--n',type=int,default=6);p.add_argument('--kind',default='Q');p.add_argument('--deriv',default='vd');a=p.parse_args();run(a.n,a.kind,a.deriv,a.sector,a.stop,a.resume)
