import numpy as np
from htb import _gen
for L in [32,40,48,56,64,80,96]:
    for Pmax in (11,8):
        dummy=np.zeros((1,1),np.int64); d1=np.zeros(1,np.int64)
        d=_gen(L,Pmax,dummy,d1,d1,False)
        print(L,Pmax,d,flush=True)
