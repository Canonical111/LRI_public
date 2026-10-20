"""Independent volume (not cutoff-face) evaluation of the Z6 tail residue.
Integrates all five gaps. The charge finite part restores the scale logarithm.
"""
import tail_boundary as tb
from hyperlog_core import *
import json,time,hashlib,argparse
from pathlib import Path
F=tb.F;mt=tb.mt
ROOT=tb.ROOT;OUT=ROOT/'direct_Z6_d';OUT.mkdir(exist_ok=True)

def setup():
 n=6;N=5;coords=[K.zero]+[K(i)+GEN[i] for i in range(1,n)];factors=[];ins={}
 for i in range(n):
  for j in range(i+1,n):
   sign=(-1)**(i+j);factors.append((coords[j]-coords[i],2*sign));w=[()]*N;L={}
   if i:w[i-1]=(GEN[j]+K(j-i),);addto(L,(tuple(w),()),K.one);w[i-1]=()
   w[j-1]=(-K(j-i),);addto(L,(tuple(w),()),K.one)
   for key,c in tb.om.multiply(L,L,N).items():addto(ins,key,sign*c)
 return factors,clean(ins),N

def sources():
 fac,ins,N=setup();rows=[]
 for j,b in enumerate(tb.tb.pp_factored(fac)):
  folder=OUT/f'b{j:02d}';folder.mkdir(exist_ok=True);path=folder/'stage1.jsonl'
  expr=tb.tb.first_block(b,ins,N);tb.tb.br.rr.dump(path,expr)
  rows.append({'id':folder.name,'rows':len(expr),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 (OUT/'manifest.json').write_text(json.dumps(rows,indent=2));print('VOLUME_SOURCES',len(rows),flush=True)

def worker(name):
 folder=OUT/name;N=5;start=time.time()
 for idx in [2,3]:
  dest=folder/f'stage{idx}.jsonl'
  if not dest.exists():
   items=tb.tb.br.rr.load(folder/f'stage{idx-1}.jsonl');expr=tb.tb.one_stage(items,idx,N);tb.tb.br.rr.dump(dest,expr);del items,expr;tb.tb.br.rr.clear()
 items=tb.tb.br.rr.load(folder/'stage3.jsonl');value=F(0);idx=4;count=0
 def end(c,w,other,sign):
  nonlocal value,count
  scale,num,den=tb.parts(c,N)
  if not scale:return
  H=mt.canon((tb.sb.aword_scaled(w,N),tb.sb.aword_scaled(other,N)))
  value+=sign*scale*(tb.functional(num,den,H,-1,5,0,1)-5*tb.functional(num,den,H,0,5,0,1)-tb.functional((F(0),)+num,den,H,0,5,0,1));count+=1
 for j,((words,logs),R) in enumerate(items):
  assert not logs and not any(words[:3]);pp,po=apart(R,idx)
  for kind,a,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
   audit_basis(kind,a,p,words[3],idx)
   for w,c in integrate_basis(kind,a,p,words[3],idx).items():
    for ww,cc in endpoint_value(c,w,idx,GEN[5]).items():end(pref*cc,ww,words[4],1)
    for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
     assert not ww;end(pref*cc,(),words[4],-1)
  items[j]=None
  if j%200==0:print('VOLUME_FINAL',name,j,len(items),value,time.time()-start,flush=True)
 result={'source':name,'value':str(value),'meaning':'dimensionless Z6 first-tail coefficient epsilon^0 log(epsilon); scale term not yet restored','endpoint_terms':count,'seconds':time.time()-start}
 (folder/'result.json').write_text(json.dumps(result,indent=2));print('VOLUME_DONE',result,flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--sources',action='store_true');a.add_argument('--block');p=a.parse_args()
 if p.sources:sources()
 else:worker(p.block)
