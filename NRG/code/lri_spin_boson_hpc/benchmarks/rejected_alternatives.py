"""One-block probe only. Alternatives here are not the production solver."""
from pathlib import Path
import argparse,json,sys,time,warnings
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh
from threadpoolctl import threadpool_limits
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from lri_spin import Config,run
from lri_spin.blocks import HamiltonianBlock
p=argparse.ArgumentParser();p.add_argument('--keep',type=int,default=32);p.add_argument('--nb',type=int,default=8);p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lri_spin.campaign import refuse_campaign_destination
refuse_campaign_destination(a.output)   # never write benchmark output into campaign state
saved=[];original=HamiltonianBlock.solve

def capture(self,*args,**kwargs):
 saved[:]=[self]
 return original(self,*args,**kwargs)

HamiltonianBlock.solve=capture
try:
 run(.43977045457263714,Config(s=.8,Lambda=3,keep=a.keep,nb=a.nb,nsites=10),backend='dense')
finally: HamiltonianBlock.solve=original
H=saved[0];k=min(a.keep,H.layout.dimension-2);rows=[[None]*a.nb for _ in range(a.nb)]
for n in range(a.nb):
 rows[n][n]=sp.diags(H.diagonal[n])
 if n+1<a.nb:rows[n][n+1]=sp.csr_matrix(H.upper[n]);rows[n+1][n]=rows[n][n+1].T
csr=sp.bmat(rows,format='csr');out={}
with threadpool_limits(limits=1):
 st=time.perf_counter();e,u=H.solve(k);out['dense']={'seconds':time.perf_counter()-st}
 st=time.perf_counter();eb,ub=H.solve(k,backend='banded');out['banded']={'seconds':time.perf_counter()-st,'max_eigenvalue_difference':float(max(abs(eb-e)))}
 st=time.perf_counter();ee,U=eigsh(csr,k=k,which='SA',tol=1e-13,ncv=min(H.layout.dimension,2*k+8),v0=np.cos(np.sqrt(2.)*np.arange(H.layout.dimension)))
 ix=np.argsort(ee);ee=ee[ix];U=U[:,ix]
 out['ARPACK']={'seconds':time.perf_counter()-st,'max_eigenvalue_difference':float(max(abs(ee-e))),'max_eigen_residual':float(max(np.linalg.norm(csr@U-U*ee,axis=0)))}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
