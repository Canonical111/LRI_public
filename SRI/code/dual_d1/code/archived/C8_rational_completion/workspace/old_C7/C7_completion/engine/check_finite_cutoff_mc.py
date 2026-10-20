"""Independent finite-cutoff direct integration of original ordered kernels.
Scrambled Sobol replicates; errors are empirical, not certified enclosures.
"""
import numpy as np,json,time
from scipy.stats import qmc
from math import factorial
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out={};eps=1/8
for n,kind in [(7,'A'),(6,'Qv'),(5,'EA')]:
 for m in [16,18]:
  vals=[];t=time.time()
  for seed in range(8):
   L=1-(n-1)*eps
   x=np.sort(qmc.Sobol(n,scramble=True,seed=1024+seed).random_base2(m),axis=1)*L+np.arange(n)*eps
   logw=np.zeros(len(x))
   for i in range(n):
    for j in range(i+1,n):logw+=2*(-1)**(i+j)*np.log(x[:,j]-x[:,i])
   y=np.exp(logw)
   if kind=='Qv':y*=sum(x[:,j+1]-x[:,j] for j in range(0,n,2))*logw
   if kind=='EA':y*=sum((-1)**j*(np.log(x[:,j])+np.log1p(-x[:,j])) for j in range(n))
   vals.append(float(y.mean()*L**n/factorial(n)))
  ans={'epsilon':eps,'n':n,'kind':kind,'power':m,'replicates':vals,'mean':float(np.mean(vals)),'standard_error':float(np.std(vals,ddof=1)/np.sqrt(len(vals))),'seconds':time.time()-t}
  print(ans,flush=True);out[f'{kind}{n}_2^{m}']=ans
(ROOT/'finite_cutoff_direct.json').write_text(json.dumps(out,indent=2))
