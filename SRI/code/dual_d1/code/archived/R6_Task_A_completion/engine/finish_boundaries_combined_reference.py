"""Memory-bounded exact completion of the three cutoff faces.
The last two integrations use the moving-letter rational functional; a
separate full-fibration implementation checks representative source rows.
"""
from pathlib import Path
import os,sys,json,time,hashlib,argparse,gc
from fractions import Fraction as F
from functools import lru_cache
os.environ.setdefault('R6_ACCEL','1')
os.environ.setdefault('R6_NATIVE','1')
import boundary_residue as br
import moving_terminal as mt
import terminal_projection as tp
import hyperlog_core as hc
from hyperlog_core import *
ROOT=Path(__file__).resolve().parent
DEMANDS=((0,0),(-2,0),(-1,0))
LAST_NEGATIVE=None
@lru_cache(maxsize=60000)
def aword(word):return tuple(mt.affine_letter(a,4,e,GEN) for a in word)

def integrate_second(items):
 out={};idx=2
 for ((words,logs),R) in items:
  assert not logs
  ant=integrate_rat(R,words[idx-1],idx);audit_primitive(ant,R,words[idx-1],idx)
  for wa,c in ant.items():
   for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
    for wf,mu in endpoint_fibrate(wb,idx+1).items():
     for wn,mv in shuffle(wf,words[idx]).items():
      keys=list(words);keys[idx-1]=();keys[idx]=wn
      addto(out,(tuple(keys),()),cb*mu*mv)
   for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
    assert not wb;keys=list(words);keys[idx-1]=()
    addto(out,(tuple(keys),()),-cb)
 return list(clean(out).items())

def integrate_last_two(items,reference=False):
 global LAST_NEGATIVE
 extras=[F(0)]*4
 save_negative=os.environ.get("R6_SAVE_NEGATIVE")=="1" and not reference
 if save_negative:import negative_moments as nm
 total=[F(0)]*len(DEMANDS);idx=3;count=0
 for ((words,logs),R) in items:
  assert not logs and not any(words[:2])
  active=words[idx-1];ant=integrate_rat(R,active,idx)
  audit_primitive(ant,R,active,idx)
  def add(c,wa,sign):
   nonlocal count
   if not reference:
    H=mt.canon((aword(wa),aword(words[3])))
    vals=mt.apply_field(c,H,5,4,DEMANDS)
    if save_negative:
     ev=nm.apply_field(c,H,5,4)
     for ii,vv in enumerate(ev):extras[ii]+=sign*vv
   else:
    vals=[F(0)]*len(DEMANDS)
    for wf,mu in endpoint_fibrate(wa,4).items():
     for w,m in shuffle(wf,words[3]).items():
      ww=tuple(tp.field_letter(a,4,e) for a in w)
      vv=tp.apply_field(c*mu*m,ww,0,5,DEMANDS,qindex=4)
      vals=[a+b for a,b in zip(vals,vv)]
   for i,v in enumerate(vals):total[i]+=sign*v
   count+=1
  for wa,c in ant.items():
   for wb,cb in endpoint_value(c,wa,idx,GEN[4]).items():add(cb,wb,1)
   for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
    assert not wb;add(cb,(),-1)
 LAST_NEGATIVE=extras if save_negative else None
 return total,count

def worker(path,source_stage):
 path=Path(path);dest=path.with_suffix('.result.json')
 if dest.exists():
  d=json.loads(dest.read_text())
  if d.get('input_sha256')==hashlib.sha256(path.read_bytes()).hexdigest():return d
 st=time.time();items=br.rr.load(path);ninput=len(items)
 if source_stage==1:
  mid=path.with_suffix('.stage2.jsonl')
  if mid.exists():items=br.rr.load(mid)
  else:
   items=integrate_second(items);br.rr.dump(mid,items)
  br.rr.clear()
 ninter=len(items);vals,count=integrate_last_two(items)
 d={'status':'complete disjoint batch','input':path.name,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_stage':source_stage,'source_rows':ninput,'intermediate_rows':ninter,'terminal_terms':count,'values':list(map(str,vals)),'demands':DEMANDS,'primitive_audit_counts':hc.AUDIT_METHODS,'seconds':time.time()-st}
 if LAST_NEGATIVE is not None:
  src=path.with_suffix('.stage2.jsonl') if source_stage==1 else path
  nd={'source':src.name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'demands':((-2,0),(-2,1),(-1,0),(-1,1)),'meaning':'dimensionless boundary inverse-Euler moment, explicit scale insertions not yet restored','values':list(map(str,LAST_NEGATIVE)),'rows':ninter,'terminal_terms':count,'computed_alongside_main_residue':True}
  path.with_suffix('.negative_moments.json').write_text(json.dumps(nd,indent=2))
  d['negative_moment_values']=list(map(str,LAST_NEGATIVE))
 dest.write_text(json.dumps(d,indent=2));print('BATCH_DONE',path.name,ninput,ninter,list(map(str,vals)),time.time()-st,flush=True)
 mt.clear();aword.cache_clear();br.rr.clear()
 return d

def check():
 src=ROOT.parent/'boundary/B6_vd_f1_stage2.jsonl'
 items=br.rr.load(src);inds=[0,1,2,17,83,261,500,1500,3500,7500,10795]
 outputs=[]
 for i in inds:
  if i>=len(items):continue
  a,c=integrate_last_two([items[i]]);b,cc=integrate_last_two([items[i]],reference=True)
  assert a==b,(i,a,b)
  outputs.append({'index':i,'values':list(map(str,a)),'moving_terms':c,'full_fibration_exact_equal':True})
 d={'test':'new mixed six-kink complete last-two-integration terms','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'checks':outputs}
 (ROOT.parent/'double_terminal_checks.json').write_text(json.dumps(d,indent=2));print('DOUBLE_TERMINAL_CHECKS',len(outputs),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--path');p.add_argument('--source-stage',type=int,default=2);a=p.parse_args()
 if a.check:check()
 else:worker(a.path,a.source_stage)
