"""Exact replayable hard-core boundary calculation, n=8 charge derivative.
All checkpoint results are partial until full source coverage is verified.
"""
from pathlib import Path
import os, json, time, argparse, hashlib, gc, sys
sys.setrecursionlimit(200000)
from fractions import Fraction as F
from functools import lru_cache
os.environ.setdefault('R6_NATIVE','1')
os.environ.setdefault('R6_ACCEL','1')
os.environ.setdefault('R6_LINEAR','1')
os.environ.setdefault('R6_MOD','1')
import boundary_residue as br
import hyperlog_core as hc
from hyperlog_core import *
import safe_parse
safe_parse.install(K)
import ordered_moments as om
import moving_terminal as mt
import terminal_projection as tp
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'blocks';OUT.mkdir(exist_ok=True)

def setup(n,face):
 N=n-2;ids=[0]+[i if i<face else i-1 for i in range(1,n)]
 coords=[i*e+(GEN[j] if j else K.zero) for i,j in enumerate(ids)]
 D=sum((coords[i+1]-coords[i] for i in range(0,n,2)),K.zero)
 factors=[(e,1),(1-coords[-1],1),(D,1)];lv={}
 for i in range(n):
  for j in range(i+1,n):
   power=2*(-1)**(i+j);factors.append((coords[j]-coords[i],power))
   ia,ib=ids[i],ids[j];c=(j-i)*e
   if ia==ib:continue
   words=[()]*N
   if ia:
    words[ia-1]=(GEN[ib]+c,);addto(lv,(tuple(words),()),K(power));words[ia-1]=()
   words[ib-1]=(-c,);addto(lv,(tuple(words),()),K(power))
 return factors,clean(lv),N,ids

def pp_factored(factors,idx=1):
 X=GEN[idx];active=[];spect=K.one
 for f,p in factors:
  if not f.diff(X):spect*=f**p
  else:active.append((f,p))
 den=[(i,f,-p) for i,(f,p) in enumerate(active) if p<0]
 degree_sum=sum(p for f,p in active);pol=[]
 if degree_sum>=0:
  A=K.one
  for f,p in active:A*=f**p
  pp,_=apart(A,idx)
  pol=[('poly',K.zero,k,c*spect) for k,c in pp.items()]
 blocks=list(pol)
 for i,f,m in den:
  assert m==2
  slope=f.diff(X);root=-sub(f,idx,K.zero)/slope
  val=spect/slope**m;logder=K.zero
  for j,(ff,p) in enumerate(active):
   if i==j:continue
   at=sub(ff,idx,root);val*=at**p;logder+=p*ff.diff(X)/at
  if val:blocks.append(('pole',root,2,val))
  if logder:blocks.append(('pole',root,1,val*logder))
 return blocks

def first_block(block,ins,N):
 kind,root,power,C=block;out={}
 for (words,logs),co in ins.items():
  ant=integrate_basis(kind,root,power,words[0],1);hc.audit_basis(kind,root,power,words[0],1)
  for wa,c in ant.items():
   for wb,cb in endpoint_value(c,wa,1,GEN[2]).items():
    for wf,mu in endpoint_fibrate(wb,2).items():
     for wn,mv in shuffle(wf,words[1]).items():
      keys=list(words);keys[0]=();keys[1]=wn;addto(out,(tuple(keys),()),cb*mu*mv*co)
   for wb,cb in endpoint_value(c,wa,1,K.zero,lower=True).items():
    assert not wb;keys=list(words);keys[0]=();addto(out,(tuple(keys),()),-cb*co)
 return {key:co*C for key,co in clean(out).items() if co*C}

def sources(n,face):
 st=time.time();factors,ins,N,ids=setup(n,face)
 print('SETUP',n,face,'insertion',len(ins),'seconds',time.time()-st,flush=True)
 blocks=pp_factored(factors)
 print('PRINCIPAL',n,face,len(blocks),'seconds',time.time()-st,flush=True)
 rows=[]
 for j,bl in enumerate(blocks):
  name=f'n{n}_f{face}_b{j:02d}';folder=OUT/name;folder.mkdir(exist_ok=True);p=folder/'stage1.jsonl'
  if not p.exists():
   expr=first_block(bl,ins,N);br.rr.dump(p,expr);nrows=len(expr);del expr
  else:nrows=sum(1 for _ in p.open())
  row={'id':name,'face':face,'n':n,'first_block':j,'kind':bl[0],'pole':str(bl[1]),'order':bl[2],'source_rows':nrows,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  (folder/'source.json').write_text(json.dumps(row,indent=2));rows.append(row)
  print('SOURCE',name,nrows,'seconds',time.time()-st,flush=True);br.rr.clear()
 (OUT/f'n{n}_face{face}_manifest.json').write_text(json.dumps({'n':n,'face':face,'ids':ids,'blocks':rows,'source_complete':True},indent=2))
 return rows

def one_stage(items,idx,N):
 out={};st=time.time()
 for j,((words,logs),R) in enumerate(items):
  assert not logs;active=words[idx-1];pp,po=apart(R,idx)
  bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
  for kind,root,power,pref in bases:
   assert not pref.diff(GEN[idx]);audit_basis(kind,root,power,active,idx)
   for wa,c in integrate_basis(kind,root,power,active,idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
     for wf,mu in endpoint_fibrate(wb,idx+1).items():
      for wn,mv in shuffle(wf,words[idx]).items():
       keys=list(words);keys[idx-1]=();keys[idx]=wn;addto(out,(tuple(keys),()),pref*cb*mu*mv)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;keys=list(words);keys[idx-1]=();addto(out,(tuple(keys),()),-pref*cb)
  if j%100==0:print('ROW',idx,j+1,len(items),'out',len(out),'seconds',time.time()-st,flush=True)
 return clean(out)

@lru_cache(maxsize=60000)
def aword(word,N):return tuple(mt.affine_letter(a,N,e,GEN) for a in word)

def last_two(items,n):
 N=n-2;idx=N-1;total=F(0);st=time.time();count=0
 import negative_moments as nm
 demands=tuple((p,r) for p in range(-(n//2-1),0) for r in (0,1))
 negatives=[F(0)]*len(demands)
 for j,((words,logs),R) in enumerate(items):
  assert not logs and not any(words[:idx-1]);active=words[idx-1];pp,po=apart(R,idx)
  bases=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
  def endpoint(c,wa,sign):
   nonlocal total,count
   H=mt.canon((aword(wa,N),aword(words[N-1],N)));total+=sign*mt.apply_field(c,H,n-1,N,((0,0),))[0];count+=1
   ev=nm.apply_field(c,H,n-1,N,demands)
   for k,v in enumerate(ev):negatives[k]+=sign*v
  for kind,root,power,pref in bases:
   audit_basis(kind,root,power,active,idx)
   for wa,c in integrate_basis(kind,root,power,active,idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[N]).items():endpoint(pref*cb,wb,1)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;endpoint(pref*cb,(),-1)
  if j%50==0:print('FINAL',j+1,len(items),'sum',str(total),'seconds',time.time()-st,flush=True)
 return total,count,negatives

def worker(name):
 folder=OUT/name;n=int(name.split('_')[0][1:]);N=n-2;st=time.time();meta=json.loads((folder/'source.json').read_text())
 if (folder/'result.json').exists():print('ALREADY_DONE',name);return
 for idx in range(2,N-1):
  p=folder/f'stage{idx}.jsonl'
  if p.exists() or any((folder/f'stage{k}.jsonl').exists() for k in range(idx+1,N-1)):continue
  items=br.rr.load(folder/f'stage{idx-1}.jsonl');print('START_STAGE',name,idx,len(items),flush=True)
  out=one_stage(items,idx,N);br.rr.dump(p,out);print('DONE_STAGE',name,idx,len(out),time.time()-st,flush=True)
  del items,out;br.rr.clear()
 items=br.rr.load(folder/f'stage{N-2}.jsonl');value,count,negatives=last_two(items,n)
 result={'status':'complete_block_not_full_integral','id':name,'value':str(value),'source_sha256':meta['source_sha256'],'dimensionless_negative_inverse_euler':list(map(str,negatives)),'terminal_rows':len(items),'terminal_terms':count,'seconds':time.time()-st,'audits':hc.AUDIT_METHODS}
 (folder/'result.json').write_text(json.dumps(result,indent=2));print('BLOCK_DONE',result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',action='store_true');p.add_argument('--n',type=int,default=8);p.add_argument('--face',type=int);p.add_argument('--block');a=p.parse_args()
 if a.sources:sources(a.n,a.face)
 else:worker(a.block)
