"""Direct finite-cutoff ordered boundary cubature, with no GPL input.
Computes the physical charge derivative and its dimensionless/log-scale split.
"""
import numpy as np
from scipy.special import roots_jacobi
from pathlib import Path
import json,time,argparse

def calc(n,eps,N,batch=80000):
 m=n-2;L=1/eps-(n-1);assert L>0
 xw=[]
 for j in range(1,m+1):
  alpha=1 if j==m else 0
  x,w=roots_jacobi(N,alpha,j-1);xw.append(((x+1)/2,w/2**(j+alpha)))
 total=N**m;faces=[];st=time.time()
 for face in range(1,n//2+1):
  ids=[0]+[i if i<face else i-1 for i in range(1,n)]
  vb=0.;vc=0.
  for lo in range(0,total,batch):
   code=np.arange(lo,min(total,lo+batch));num=len(code);z=np.empty((num,m));wt=np.ones(num)
   for j,(xx,ww) in enumerate(xw):digit=code%N;code//=N;z[:,j]=xx[digit];wt*=ww[digit]
   ts=np.zeros((num,m+1));cum=np.ones(num)
   for j in range(m-1,-1,-1):cum*=z[:,j];ts[:,j+1]=L*cum
   X=np.empty((num,n))
   for i,j in enumerate(ids):X[:,i]=i+ts[:,j]
   lv=np.zeros(num)
   for i in range(n):
    for j in range(i+1,n):lv+=2*(-1)**(i+j)*np.log(X[:,j]-X[:,i])
   dip=sum(X[:,j+1]-X[:,j] for j in range(0,n,2));ww=np.exp(lv)*dip
   vb+=np.sum(wt*ww);vc+=np.sum(wt*ww*lv)
  factor=eps*L**(m+1);vb*=factor;vc*=factor
  faces.append({'face':face,'weight':1 if face==n//2 else 2,'base':vb,'dimensionless_charge':vc,'physical_charge':vc-n*np.log(eps)*vb})
 return {'n':n,'epsilon':eps,'gaussian_order':N,'nodes_per_face':total,'faces':faces,'B0':sum(r['weight']*r['base'] for r in faces),'Bv_dimensionless':sum(r['weight']*r['dimensionless_charge'] for r in faces),'Bv_physical':sum(r['weight']*r['physical_charge'] for r in faces),'seconds':time.time()-st,'independent_original_kernel':True,'interval_bound':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=8);p.add_argument('--orders',default='6,8,10,12');p.add_argument('--epsilon',type=float,default=.1);p.add_argument('--out',default='../data/direct_B8_finite.json');a=p.parse_args();runs=[]
 for N in map(int,a.orders.split(',')):
  r=calc(a.n,a.epsilon,N);runs.append(r);Path(a.out).write_text(json.dumps(runs,indent=2));print(r,flush=True)
