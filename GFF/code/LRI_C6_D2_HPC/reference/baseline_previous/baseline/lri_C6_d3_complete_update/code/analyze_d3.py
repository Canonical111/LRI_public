import json,sys
import numpy as np
from pathlib import Path
W=Path(__file__).resolve().parents[1]/"records"
ref=json.load(open(W/'two_loop_d3.json'))['records'][-1]['b2_jets']
B2=np.array([float(x) for x in ref])

def coefficients(vals):
 dtype=np.result_type(*[v.dtype for v in vals.values()])
 N=7
 b={1:np.array([3.],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1.],dtype=dtype),2:B2.astype(dtype)/6}
 for L,a in vals.items():
  k=7-L;b[L]=a[:k];c[L]=a[k:]
 def mul(x,y):return np.convolve(x,y)[:N]
 g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
 for _ in range(7):
  gp=g.copy();temp=np.zeros(N,dtype=dtype)
  for L in range(2,7):
   gp=mul(gp,g);temp[:len(gp)]+=mul(b.get(L,np.zeros(1)),gp)
  g=(e-temp)/3
 ga=np.zeros(N,dtype=dtype);gp=np.zeros(N,dtype=dtype);gp[0]=1
 for L in range(1,7):
  gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
 ga[0]+=1.5;ga[1]-=.5
 return ga

def main(prefix):
 data={L:json.load(open(W/f'{prefix}{L}.json'))for L in range(3,7)}
 arrays={L:np.array(d['batches'])for L,d in data.items()};means={L:a.mean(0)for L,a in arrays.items()};mu=coefficients(means);var=np.zeros(7)
 jac={}
 for L,a in means.items():
  mat=[]
  for j in range(len(a)):
   v={k:x.astype(complex)for k,x in means.items()};v[L][j]+=1e-20j;mat.append(coefficients(v).imag/1e-20)
  J=np.array(mat).T;jac[L]=J
  cov=np.cov(arrays[L],rowvar=False,ddof=1)/len(arrays[L]);var+=np.diag(J@cov@J.T)
 print('b2',B2)
 print('C',mu,'SE',np.sqrt(var))
 for L,J in jac.items():print('L',L,'C6grad',J[6]);print('SE_C6',np.std(arrays[L]@J[6],ddof=1)/np.sqrt(len(arrays[L])))
 return mu,var,jac,data
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else 'pilot_L')
