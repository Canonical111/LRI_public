"""Full finite constants via dimensionless coordinates, retaining log integers.
Explicit powers of log(epsilon) cannot contribute to epsilon^0 log^0.
All period constants from endpoint fibration are retained.
"""
from full_boundary import *

def scaled_sources(n,kind,deriv):
 absolute=kind.startswith('E');dip=kind.endswith('Q');N=n if absolute else n-1
 Xs=[K(i)+GEN[i+1] for i in range(n)] if absolute else [K.zero]+[K(i)+GEN[i] for i in range(1,n)]
 fac=[(Xs[j]-Xs[i],2*(-1)**(i+j)) for i in range(n) for j in range(i+1,n)]
 if dip:fac.append((sum((Xs[i+1]-Xs[i] for i in range(0,n,2)),K.zero),1))
 ins0,N0=rm.initial(n,kind,deriv,kernel=False);assert N==N0
 ins={}
 for (ww,ll),c in ins0.items():
  if 1 in ll:continue
  ws=tuple(tuple(sub(a,0,K.one) for a in w) for w in ww)
  addto(ins,(ws,ll),sub(c,0,K.one))
 ins=clean(ins);bs=principal(fac);folder=ROOT/f'S{kind}{n}_{deriv}';folder.mkdir(exist_ok=True);records=[]
 for i,bl in enumerate(bs):
  p=folder/f'b{i:02}/stage1.jsonl'
  if not p.exists():
   expr=first(bl,ins,N);dump(p,expr);del expr
  records.append({'block':f'b{i:02}','rows':sum(1 for _ in p.open()),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  print('SCALED_SOURCE',n,kind,deriv,records[-1],flush=True);clear()
 kap=(n%2)+(1 if dip else 0)-(0 if absolute else 1)
 (folder/'manifest.json').write_text(json.dumps({'n':n,'kind':kind,'deriv':deriv,'N':N,'kappa':kap,'absolute':absolute,'blocks':records,'full_constants':True,'target':'epsilon^0 log^0'},indent=2))

def scaled_last(items,N,n,kap,absolute):
 out={};st=time.time()
 for j,((words,logs),R) in enumerate(items):
  R=R*e**kap
  if not absolute:R=R*(1-e*((n-1)+GEN[N]))
  for word,co in integrate_rat(R,words[-1],N).items():
   for w,c in endpoint_value(co,word,N,1/e-(n-1)).items():
    assert all(a.numer.is_ground and not a.denf for a in w)
    addto(out,(tuple(w),logs),c)
   for w,c in endpoint_value(co,word,N,K.zero,lower=True).items():
    assert not w;addto(out,((),logs),-c)
  items[j]=None
  if j%500==0:print('SCALED_LAST',j+1,len(items),len(out),time.time()-st,flush=True)
 return clean(out)

def scaled_worker(tag,block,stop=None):
 folder=ROOT/tag/block;meta=json.loads((folder.parent/'manifest.json').read_text());N=meta['N'];n=meta['n']
 for idx in range(max(2,meta.get("starting_stage",1)+1),min(N-1,stop or N)+1):
  path=folder/f'stage{idx}.jsonl'
  if path.exists():continue
  items=load(folder/f'stage{idx-1}.jsonl');ans=one_stage(items,idx,N,n);dump(path,ans);del items,ans;clear()
 if stop and stop<N:return
 if not (folder/'negative.json').exists():
  items=load(folder/f'stage{N-1}.jsonl');ans=scaled_last(items,N,n,meta['kappa'],meta['absolute']);rows=[[list(map(int,w)),list(ll),str(c)] for (w,ll),c in ans.items()]
  pp=folder/'negative.json';temp=pp.with_suffix('.tmp');temp.write_text(json.dumps(rows));temp.replace(pp)
  print('SCALED_NEGATIVE',tag,block,len(rows),flush=True);del rows,ans,items;clear()
 if not (folder/'finite.expr').exists():
  import sympy as s
  value=full_extract(json.loads((folder/'negative.json').read_text()),n-1)
  pp=folder/'finite.expr';tmp=pp.with_suffix('.tmp');tmp.write_text(s.sstr(value,order='none'));tmp.replace(pp)
  (folder/'result.json').write_text(json.dumps({'complete':True,'full_constants':True,'terms':len(s.Add.make_args(value)),'source_sha256':hashlib.sha256((folder/f"stage{meta.get('starting_stage',1)}.jsonl").read_bytes()).hexdigest(),'rational_projection_check':str(s.expand(value).as_coeff_Add()[0])}));print('SCALED_DONE',tag,block,flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--n',type=int);p.add_argument('--kind');p.add_argument('--deriv');p.add_argument('--sources',action='store_true');p.add_argument('--tag');p.add_argument('--block');p.add_argument('--stop',type=int);a=p.parse_args()
 if a.sources:scaled_sources(a.n,a.kind,a.deriv)
 else:scaled_worker(a.tag,a.block,a.stop)
