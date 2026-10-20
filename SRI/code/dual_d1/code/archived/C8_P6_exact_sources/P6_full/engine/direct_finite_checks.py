"""Independent finite-cutoff cubature of Q6_vv and EQ6_v.
Translation and its endpoint logarithm are integrated analytically.
The remaining endpoint log is integrated with interpolatory log moments.
No hyperlogarithm source expressions or fitted finite coefficients are read.
"""
from pathlib import Path
import numpy as np,mpmath as mp
from scipy.special import roots_jacobi
import json,time,argparse

def rule(N,m):
 nodes=[];weights=[]
 for j in range(1,m+1):
  alpha=1 if j==m else 0
  x,w=roots_jacobi(N,alpha,j-1);nodes.append((x+1)/2);weights.append(w/2**(j+alpha))
 mp.mp.dps=100
 xx=list(map(lambda x:mp.mpf(float(x)),nodes[-1]))
 V=mp.matrix([[x**k for x in xx] for k in range(N)])
 moments=mp.matrix([mp.beta(m+k,2)*(mp.digamma(2)-mp.digamma(m+k+2)) for k in range(N)])
 sol=mp.lu_solve(V,moments)
 assert max(abs(z) for z in V*sol-moments)<mp.mpf('1e-80')
 wlog=np.array([float(z) for z in sol])
 return nodes,weights,wlog

def calc(n,eps,N,batch=80000):
 m=n-1;L=1-m*eps;nodes,weights,wlog=rule(N,m);total=N**m
 vvv=0.;ee=0.;st=time.time()
 for lo in range(0,total,batch):
  inds=np.arange(lo,min(total,lo+batch));M=len(inds);qq=inds.copy();zz=np.empty((M,m));weight=np.ones(M);logweight=np.ones(M)
  for j in range(m):
   dig=qq%N;qq//=N;zz[:,j]=nodes[j][dig];weight*=weights[j][dig];logweight*=wlog[dig] if j==m-1 else weights[j][dig]
  xx=np.zeros((M,n));cum=np.ones(M)
  for j in range(m-1,-1,-1):cum*=zz[:,j];xx[:,j+1]=(j+1)*eps+L*cum
  lv=np.zeros(M)
  for i in range(n):
   for j in range(i+1,n):lv+=2*(-1)**(i+j)*np.log(xx[:,j]-xx[:,i])
  D=sum(xx[:,j+1]-xx[:,j] for j in range(0,n,2));common=np.exp(lv)*D
  h=1-xx[:,-1];smooth=np.full(M,np.log(L))
  for i in range(1,n):
   r=xx[:,i];smooth+=(-1)**i*(np.log(r+h)+(r/h)*np.log1p(h/r))
  vvv+=np.sum(weight*common*lv**2)
  ee+=np.sum((weight*smooth+logweight)*2*common*lv)
 return {'n':n,'epsilon':eps,'order':N,'nodes':total,'Q_vv':float(vvv*L**(m+1)),'EQ_v':float(ee*L**(m+1)),'seconds':time.time()-st,'endpoint_log_moment_residual_less_than':'1e-80','no_raw_period_values_used':True,'interval_bound':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=6);p.add_argument('--epsilon',type=float,default=.1);p.add_argument('--orders',default='8,12,16');p.add_argument('--out',default='../data/direct_finite.json');a=p.parse_args();res=[]
 for N in map(int,a.orders.split(',')):
  r=calc(a.n,a.epsilon,N);res.append(r);Path(a.out).write_text(json.dumps(res,indent=2));print(r,flush=True)
