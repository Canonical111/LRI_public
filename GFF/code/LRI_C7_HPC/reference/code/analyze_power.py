from pathlib import Path
import json,numpy as np,sys
from assemble_coordinate import coefficients
W=Path(__file__).resolve().parents[1]
def read(file):
 return np.array(json.load(open(W/'records'/file))['batches'])
def references(N=12):
 f={2:read('coord_L2_N24.json')[0],3:read('coord_free_L3_N24.json')[0],4:read(f'low_exact_free_L4_N{N}.json')[0]}
 c5=-731.139476624539825853869126582527
 f[5]=np.zeros(14);base=coefficients(f,5)[5];f[5][4]=(base-c5)*729
 p={3:read('coord_L3_N24.json')[0]-f[3],4:read(f'low_exact_power_L4_N{N}.json')[0]}
 return f,p

def delta(f,p,n=7):
 full={L:np.asarray(f.get(L,np.zeros(14)))+np.asarray(p.get(L,np.zeros(14)))for L in range(2,n+1)}
 return coefficients(full,n)-coefficients(f,n)

def jac_delta(f,p):
 res={}
 for L in p:
  out=np.zeros((8,14))
  for j in range(14):
   pp={k:v.astype(complex)for k,v in p.items()};pp[L][j]+=1e-20j;out[:,j]=delta(f,pp).imag/1e-20
  res[L]=out
 return res

if __name__=='__main__':
 f,p=references();B={}
 for L in [5,6,7]:B[L]=read(f'power_coarse_power_L{L}_N1.json');p[L]=B[L].mean(0)
 print('base fC',coefficients(f));print('delta',delta(f,p));J=jac_delta(f,p);controls={}
 for L in [5,6,7]:
  Y=B[L]@J[L][7];Z=B[L][:,list(range(L-1))+list(range(7,7+L-1))];scale=np.sqrt((Z**2).mean(0));scale[scale==0]=1;X=Z/scale;coef=np.linalg.lstsq(X-X.mean(0),Y-Y.mean(),rcond=1e-6)[0];res=Y-X@coef
  print('L',L,'raw',Y.mean(),Y.std(ddof=1)/len(Y)**.5,'controlled',res.mean(),res.std(ddof=1)/len(Y)**.5,'rank',np.linalg.matrix_rank(X),'scale',scale)
  for train,valid in [(np.arange(16),np.arange(16,32)),(np.arange(16,32),np.arange(16))]:
   c=np.linalg.lstsq(X[train]-X[train].mean(0),Y[train]-Y[train].mean(),rcond=1e-5)[0];r=Y[valid]-X[valid]@c;print('split',r.mean(),r.std(ddof=1)/len(r)**.5)
  arr=np.zeros(14);arr[list(range(L-1))+list(range(7,7+L-1))]=coef/scale;controls[L]=dict(target=J[L][7].tolist(),control=arr.tolist(),raw_mean=Y.mean(),adjusted_mean=res.mean(),residual_standard_error=res.std(ddof=1)/len(Y)**.5)
 (W/'verification/power_control_training.json').write_text(json.dumps(controls,indent=2))
