import numpy as np,json
from scipy.stats import qmc
from math import factorial
out={};eps=1/8
for n in [3,4,5]:
 vals=[]
 for seed in range(8):
  x=np.sort(qmc.Sobol(n,scramble=True,seed=5408+seed).random_base2(20),axis=1)*(1-(n-1)*eps)+np.arange(n)*eps
  lw=np.zeros(len(x));ld=np.zeros(len(x))
  for i in range(n):
   for j in range(i+1,n):
    rr=np.log(x[:,j]-x[:,i]);qq=(-1)**(i+j);lw+=2*qq*rr;ld+=qq*rr**2
  vals.append(float(np.mean(np.exp(lw)*ld)*(1-(n-1)*eps)**n/factorial(n)))
 out[str(n)]={'vals':vals,'mean':float(np.mean(vals)),'se':float(np.std(vals,ddof=1)/np.sqrt(len(vals)))}
 print(n,out[str(n)],flush=True)
open('finite_tail_direct.json','w').write(json.dumps(out,indent=2))
