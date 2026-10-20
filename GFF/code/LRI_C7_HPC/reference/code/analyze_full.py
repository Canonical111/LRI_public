from pathlib import Path
import json,numpy as np,sys
from full_assembly import affine
W=Path(__file__).resolve().parents[1]
ref=json.load(open(W/'verification/full_affine_assembly.json'));K=np.array(ref['K']);J={int(L):np.array(v['J'])for L,v in ref['loops'].items()};Adj={int(L):np.array(v['adjusted'])for L,v in ref['loops'].items()}

def campaign(tag):
 mean=K.copy();cov=np.zeros((8,8));details={}
 for L in [5,6,7]:
  fn=W/f'records/{tag}_L{L}.json'
  if not fn.exists():return None
  d=json.load(open(fn));a=np.array(d['batches']);y=a@J[L].T;m=y.mean(0);v=np.cov(y,rowvar=False,ddof=1)/len(y);mean+=m;cov+=v;details[L]=dict(mean=m.tolist(),se=np.sqrt(np.maximum(0,np.diag(v))).tolist())
 mean[7]+=-696147.4459362661;cov[7,7]+=25.3678**2
 return mean,cov,details

def power_level(mode,Nlo,Nhi):
 mean=np.zeros(8);cov=np.zeros((8,8));info={};complete=True
 for L in [5,6,7]:
  fn=W/f'records/power_{mode}_L{L}_N{Nhi}.json'
  if not fn.exists():complete=False;continue
  a=np.array(json.load(open(fn))['batches'])
  if Nlo:a-=np.array(json.load(open(W/f'records/power_{mode}_L{L}_N{Nlo}.json'))['batches'])
  y=a@Adj[L].T;m=y.mean(0);v=np.cov(y,rowvar=False,ddof=1)/len(y);mean+=m;cov+=v;info[L]=dict(mean=m.tolist(),se=np.sqrt(np.maximum(0,np.diag(v))).tolist())
 return mean,cov,info,complete
if __name__=='__main__':
 for t in ['tprodA','tprodB']:
  x=campaign(t)
  if x:print(t,'full-low+freehigh',x[0][5:],'SE',np.sqrt(np.diag(x[1]))[5:]);print(x[2]if x else '')
 for mode,nlo,nhi in [('coarseA',0,1),('refine3',1,3),('refine5',3,5)]:
  x=power_level(mode,nlo,nhi);print(mode,'complete',x[-1],'mean',x[0][5:],'SE',np.sqrt(np.diag(x[1]))[5:]);print(x[2])
