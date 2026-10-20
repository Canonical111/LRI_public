"""Formal finite constant of the endpoint response EA_n, n odd.
All n ordered coordinates are integrated. Under X=eps(i+T_i),
EA_n carries a single factor eps; the explicit 2 log(eps) A_n
has no finite log-free coefficient and is not used in this projection.
"""
import tail_boundary as tb
from hyperlog_core import *
from pathlib import Path
import json,time,hashlib,argparse
F=tb.F;mt=tb.mt
ROOT=tb.ROOT;OUT=ROOT/'endpoint_odd';OUT.mkdir(exist_ok=True)

def source(n):
 assert n%2==1
 N=n;X=[K(i)+GEN[i+1] for i in range(n)];factors=[];ins={}
 for i in range(n):
  for j in range(i+1,n):factors.append((X[j]-X[i],2*(-1)**(i+j)))
 for i in range(n):
  ww=[()]*N;ww[i]=(-K(i),);addto(ins,(tuple(ww),()),K(2*(-1)**i))
 rows=[]
 for j,b in enumerate(tb.tb.pp_factored(factors)):
  path=OUT/f'EA{n}_b{j:02d}';path.mkdir(exist_ok=True);src=path/'stage1.jsonl';expr=tb.tb.first_block(b,ins,N);tb.tb.br.rr.dump(src,expr)
  rows.append({'id':path.name,'kind':b[0],'pole':str(b[1]),'pole_order':b[2],'source_rows':len(expr),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
  print('EA_SOURCE',n,j,len(expr),flush=True)
 (OUT/f'EA{n}_manifest.json').write_text(json.dumps({'n':n,'blocks':rows,'complete_source':True},indent=2))

def worker(name):
 n=int(name.split('_')[0][2:]);N=n;idx=N-1;folder=OUT/name;start=time.time()
 meta=next(x for x in json.loads((OUT/f'EA{n}_manifest.json').read_text())['blocks'] if x['id']==name)
 if (folder/'result.json').exists():
  r=json.loads((folder/'result.json').read_text());assert r['source_sha256']==meta['source_sha256'];print('REUSED',name);return
 for j in range(2,N-1):
  dest=folder/f'stage{j}.jsonl'
  if dest.exists():continue
  items=tb.tb.br.rr.load(folder/f'stage{j-1}.jsonl');ans=tb.tb.one_stage(items,j,N);tb.tb.br.rr.dump(dest,ans)
  print('EA_STAGE',name,j,len(ans),time.time()-start,flush=True);del items,ans;tb.tb.br.rr.clear()
 items=tb.tb.br.rr.load(folder/f'stage{N-2}.jsonl');value=F(0);count=0
 def endpoint(co,w,other,sgn):
  nonlocal value,count
  scale,num,den=tb.parts(co,N)
  if not scale:return
  H=mt.canon((tb.sb.aword_scaled(w,N),tb.sb.aword_scaled(other,N)))
  value+=sgn*scale*tb.functional(num,den,H,1,n-1,0,0);count+=1
 for j,((words,logs),R) in enumerate(items):
  assert not logs and not any(words[:idx-1]);pp,po=apart(R,idx)
  for kind,root,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
   audit_basis(kind,root,p,words[idx-1],idx)
   for w,c in integrate_basis(kind,root,p,words[idx-1],idx).items():
    for ww,cc in endpoint_value(c,w,idx,GEN[N]).items():endpoint(pref*cc,ww,words[N-1],1)
    for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
     assert not ww;endpoint(pref*cc,(),words[N-1],-1)
  items[j]=None
  if j%200==0:print('EA_TERMINAL',name,j,len(items),value,time.time()-start,flush=True)
 d={'status':'complete_block_not_full_moment','id':name,'source_sha256':meta['source_sha256'],'finite_rational_constant':str(value),'endpoint_terms':count,'seconds':time.time()-start,'raw_integrand':'2 sum_i (-1)^i log(X_i) W_n; endpoints not cut off','degree_of_epsilon_prefactor':1}
 (folder/'result.json').write_text(json.dumps(d,indent=2));print('EA_COMPLETE',d,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int);p.add_argument('--sources',action='store_true');p.add_argument('--block');a=p.parse_args()
 if a.sources:source(a.n)
 else:worker(a.block)
