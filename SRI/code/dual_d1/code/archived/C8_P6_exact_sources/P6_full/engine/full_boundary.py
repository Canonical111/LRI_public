"""Full-constant, dimensionless cutoff-face residues. No rational projection.
Only explicit log(epsilon) terms are omitted in the boundary constant; integer
logarithms and endpoint periods are retained. They cannot mix into log^0.
"""
from full_runner import *

def setup(n,face,deriv='v'):
 N=n-2;ids=[0]+[i if i<face else i-1 for i in range(1,n)]
 Xs=[K(i)+(GEN[j] if j else K.zero) for i,j in enumerate(ids)]
 D=sum((Xs[i+1]-Xs[i] for i in range(0,n,2)),K.zero)
 fac=[(D,1)];lv={}
 for i in range(n):
  for j in range(i+1,n):
   po=2*(-1)**(i+j);fac.append((Xs[j]-Xs[i],po))
   ia,ib=ids[i],ids[j];cc=j-i;words=[()]*N
   if ia!=ib:
    if ia:
     words[ia-1]=(GEN[ib]+cc,);addto(lv,(tuple(words),()),K(po));words[ia-1]=()
    words[ib-1]=(K(-cc),);addto(lv,(tuple(words),()),K(po))
   if cc!=1:addto(lv,(tuple([()]*N),(cc,)),K(po))
 ins=clean(lv) if deriv=='v' else {(tuple([()]*N),()):K.one}
 return fac,ins,N,ids

def principal(factors,idx=1):
 X=GEN[idx];active=[];spect=K.one
 # Merge coincident factors, as in the independent rational source constructor.
 merged={}
 for f,p in factors:merged[f]=merged.get(f,0)+p
 for f,p in merged.items():
  if not p:continue
  if not f.diff(X):spect*=f**p
  else:active.append((f,p))
 bs=[]
 if sum(p for f,p in active)>=0:
  A=K.one
  for f,p in active:A*=f**p
  pp,_=apart(A,idx);bs+=[('poly',K.zero,p,c*spect) for p,c in pp.items()]
 for i,(f,p) in enumerate(active):
  if p>=0:continue
  assert p==-2
  slope=f.diff(X);root=-sub(f,idx,K.zero)/slope
  val=spect/slope**2;dd=K.zero
  for j,(ff,power) in enumerate(active):
   if i==j:continue
   at=sub(ff,idx,root);val*=at**power;dd+=power*ff.diff(X)/at
  if val:bs.append(('pole',root,2,val))
  if dd:bs.append(('pole',root,1,val*dd))
 return bs

def sources_boundary(n,face,deriv):
 folder=ROOT/f'B{n}_{deriv}_f{face}';folder.mkdir(exist_ok=True)
 fac,ins,N,ids=setup(n,face,deriv);bs=principal(fac);records=[]
 for i,bl in enumerate(bs):
  path=folder/f'b{i:02}/stage1.jsonl'
  if not path.exists():
   expr=first(bl,ins,N);dump(path,expr);del expr
  records.append({'block':f'b{i:02}','rows':sum(1 for _ in path.open()),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'order':bl[2],'pole':str(bl[1])})
  print('BOUNDARY_SOURCE',n,face,deriv,records[-1],flush=True);clear()
 (folder/'manifest.json').write_text(json.dumps({'n':n,'face':face,'N':N,'ids':ids,'derivative':deriv,'blocks':records,'full_constants':True,'explicit_scale_log_used':False,'interval_factor_external':True},indent=2))

def last_stage(items,N,n):
 out={};st=time.time()
 for j,((words,logs),R) in enumerate(items):
  # The global interval factor is put back before the last integral.
  R=R*(1-e*((n-1)+GEN[N]))
  for word,co in integrate_rat(R,words[-1],N).items():
   for w,c in endpoint_value(co,word,N,1/e-(n-1)).items():
    assert all(a.numer.is_ground and not a.denf for a in w)
    addto(out,(tuple(w),logs),c)
   for w,c in endpoint_value(co,word,N,K.zero,lower=True).items():
    assert not w;addto(out,((),logs),-c)
  items[j]=None
  if j%100==0:print('LAST_BOUNDARY',j+1,len(items),len(out),time.time()-st,flush=True)
 return clean(out)

def full_extract(rows,N):
 from finite_extract_fast import extract_finite
 return extract_finite(rows,N)

def worker_boundary(tag,block,stop=None):
 folder=ROOT/tag/block;meta=json.loads((folder.parent/'manifest.json').read_text());N=meta['N'];n=meta['n']
 for idx in range(max(2,meta.get("starting_stage",1)+1),min(N-1,stop or N)+1):
  path=folder/f'stage{idx}.jsonl'
  if path.exists():continue
  items=load(folder/f'stage{idx-1}.jsonl');ans=one_stage(items,idx,N,n);dump(path,ans);del items,ans;clear()
 if stop and stop<N:return
 if not (folder/'negative.json').exists():
  items=load(folder/f'stage{N-1}.jsonl');ans=last_stage(items,N,n)
  rows=[[list(map(int,w)),list(ll),str(c)] for (w,ll),c in ans.items()]
  p=folder/'negative.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(rows));tmp.replace(p)
  print('BOUNDARY_NEGATIVE',tag,block,len(rows),flush=True);del rows,ans,items;clear()
 if not (folder/'result.json').exists():
  import sympy as s
  if (folder/'finite.expr').exists():
   from read_expression import load as readfull
   value=readfull(folder/'finite.expr')
  else:value=full_extract(json.loads((folder/'negative.json').read_text()),n-1)
  tmp=folder/'finite.tmp';tmp.write_text(s.sstr(value,order='none'));tmp.replace(folder/'finite.expr')
  rational=value.xreplace({**{f:s.S.Zero for f in value.atoms(s.Function)},**{a:s.S.Zero for a in value.free_symbols if str(a).startswith(('R_','Z'))},s.pi:s.S.Zero})
  (folder/'result.json').write_text(json.dumps({'complete':True,'full_constants':True,'rational_check_value':str(rational),'terms':len(s.Add.make_args(value)),'input_sha256':hashlib.sha256((folder/f"stage{meta.get('starting_stage',1)}.jsonl").read_bytes()).hexdigest()}));print('BOUNDARY_DONE',tag,block,rational,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--n',type=int);p.add_argument('--face',type=int);p.add_argument('--deriv',default='v');p.add_argument('--sources',action='store_true');p.add_argument('--tag');p.add_argument('--block');p.add_argument('--stop',type=int);a=p.parse_args()
 if a.sources:sources_boundary(a.n,a.face,a.deriv)
 else:
  import fcntl
  lock=(ROOT/a.tag/a.block/'.worker.lock').open('a')
  fcntl.flock(lock,fcntl.LOCK_EX)
  worker_boundary(a.tag,a.block,a.stop)
