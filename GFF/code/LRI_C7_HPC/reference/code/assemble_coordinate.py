from pathlib import Path
import numpy as np,json,sys
W=Path(__file__).resolve().parents[1]
def coefficients(vals,order=7):
 dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()])
 N=order+1
 b={1:np.array([3.],dtype=dtype)};c={1:np.array([1.],dtype=dtype)}
 for L,a in vals.items():
  L=int(L);a=np.asarray(a);b[L]=a[L-1:7];c[L]=a[7+L-1:14]
 def mul(x,y):
  v=np.convolve(x,y)[:N];return np.pad(v,(0,N-len(v)))
 g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
 for _ in range(N):
  gp=g.copy();temp=np.zeros(N,dtype=dtype)
  for L in range(2,N):
   gp=mul(gp,g);temp+=mul(b.get(L,np.zeros(1,dtype=dtype)),gp)
  g=(e-temp)/3
 ga=np.zeros(N,dtype=dtype);gp=np.zeros(N,dtype=dtype);gp[0]=1
 for L in range(1,N):
  gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1,dtype=dtype)),gp)
 ga[0]+=.5;ga[1]-=.5
 return ga
if __name__=='__main__':
 vals={}
 for f in sys.argv[1:]:
  d=json.load(open(f)); vals[d['L']]=np.array(d['batches']).mean(0)
 print(coefficients(vals,order=max(vals)))
