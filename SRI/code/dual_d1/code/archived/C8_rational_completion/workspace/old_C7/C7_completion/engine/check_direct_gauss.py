"""Independent Gauss-Jacobi cubature of original finite-cutoff kernels.
No hyperlog engine, counterterm data, or exponent values are used.
"""
from pathlib import Path
import argparse,json,time,math
import numpy as np
from scipy.special import roots_jacobi
ROOT=Path(__file__).resolve().parent

def calc(n,kind,der,a,order,batch=120000):
 m=n-1;L=1-(n-1)*a;nodes=[];weights=[]
 for j in range(1,m+1):
  x,w=roots_jacobi(order,0,j-1);nodes.append((x+1)/2);weights.append(w/2**j)
 total=0.;abs_total=0.;num=order**m
 for lo in range(0,num,batch):
  ii=np.arange(lo,min(lo+batch,num),dtype=np.int64);N=len(ii);q=ii.copy();z=np.empty((N,m));wt=np.ones(N)
  for j in range(m):
   dig=q%order;q//=order;z[:,j]=nodes[j][dig];wt*=weights[j][dig]
  xx=np.empty((N,n));xx[:,0]=0.;cum=np.ones(N)
  for j in range(m-1,-1,-1):
   cum*=z[:,j];xx[:,j+1]=(j+1)*a+L*cum
  lv=np.zeros(N);ld=np.zeros(N);ld2=np.zeros(N)
  for i in range(n):
   for j in range(i+1,n):
    log=np.log(xx[:,j]-xx[:,i]);sgn=(-1)**(i+j);lv+=2*sgn*log
    if 'd' in der:
     ld+=sgn*log**2;ld2+=(2/3)*sgn*log**3
  f=np.exp(lv)*(1-xx[:,-1])
  if kind=='Q':f*=sum(xx[:,j+1]-xx[:,j] for j in range(0,n,2))
  if der=='v':f*=lv
  elif der=='d':f*=ld
  elif der=='vv':f*=lv**2
  elif der=='vvv':f*=lv**3
  elif der=='dd':f*=ld**2+ld2
  elif der=='vd':f*=lv*ld+ld
  elif der=='vvd':f*=lv**2*ld+2*lv*ld
  elif der=='vdd':f*=lv*(ld**2+ld2)+2*ld**2+ld2
  elif der!='base':raise ValueError(der)
  vv=wt*f;total+=np.sum(vv);abs_total+=np.sum(abs(vv))
 return float(L**m*total),float(L**m*abs_total),num

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('n',type=int);ap.add_argument('kind');ap.add_argument('der');ap.add_argument('--epsilon',type=float,default=.1);ap.add_argument('--orders',default='8,10,12');args=ap.parse_args();out=[]
 for order in map(int,args.orders.split(',')):
  st=time.time();val,absval,num=calc(args.n,args.kind,args.der,args.epsilon,order)
  r={'n':args.n,'kind':args.kind,'derivative':args.der,'epsilon':args.epsilon,'order':order,'nodes':num,'value':val,'absolute_integral':absval,'seconds':time.time()-st,'qualification':'Convergence diagnostic; not a rigorous error bound.'}
  out.append(r);print(r,flush=True)
  (ROOT/f'{args.kind}{args.n}_{args.der}_direct_gauss.json').write_text(json.dumps(out,indent=2))
