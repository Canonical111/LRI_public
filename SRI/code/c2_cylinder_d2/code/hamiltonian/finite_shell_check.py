from pathlib import Path
import inspect,json
import numpy as np
import spectral as sp
from ising_basis import Basis
from resummed import coefficients4,raw4
src=inspect.getsource(sp.evaluate)
src=src.replace('targets:list[int]):','targets:list[int],Ncut:int):')
src=src.replace('w=v/den','v=np.where(b.e[r,None,None]+me[js][None,:,None] <= 2*Ncut+spin+1e-10,v,0)\n        w=v/den')
src=src.replace('E40=np.sum(z0*z0*r0,axis=0)','z0[nsE[zero]>2*Ncut-1+spin+1e-10]=0\n    E40=np.sum(z0*z0*r0,axis=0)')
src=src.replace('E42+=np.sum(z*z/den,axis=0)','z[nsE[inds]+me[j]+me[k]>2*(15/8)+2*Ncut-1+spin+1e-10]=0\n            E42+=np.sum(z*z/den,axis=0)')
ns=dict(sp.__dict__);exec(src,ns);ev=ns['evaluate']
records=[]
for N in [2,3,4]:
 b=Basis(2*N+1);lam=.5;co,meta=coefficients4(N+1,oversample=12,radius_cost=3)
 r=raw4(co,lam,N);rs=[]
 for t in [b.vac,b.eps,b.desc]:rs+=ev(b,2*N,[lam],[t],N)['records']
 for i,name in enumerate(['vacuum','epsilon','descendant']):
  direct0=rs[i]['E4_0chi'];direct2=rs[i]['E4_2chi']
  block0=r['parts'][0][name];block2=r['parts'][1][name]+r['parts'][2][name]
  row=dict(N=N,state=name,explicit_0chi=direct0,block_0chi=block0,explicit_2chi=direct2,block_2chi=block2,
           difference_0chi=block0-direct0,difference_2chi=block2-direct2)
  print(row,flush=True);records.append(row)
Path(__file__).with_name('finite_shell_check.json').write_text(json.dumps(records,indent=2))
