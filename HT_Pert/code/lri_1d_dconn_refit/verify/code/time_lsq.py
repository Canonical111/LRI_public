import time
from mylsq import *
from flint import arb
Ls=list(range(16,73,2))
import numpy as np
y=[arb(float(1/L+np.log(L)/L**2)) for L in Ls]
terms=[(0,0),(0,1),(0.5,0),(1,0),(1,1),(1.5,0),(2,0),(2,1)]
t=time.time()
for _ in range(20):
    cols=[[arb(L)**(-arb(p))*arb(L).log()**j for L in Ls] for p,j in terms]
    r=solve(cols,y)
print((time.time()-t)/20)
