import numpy as np, time
from htb import *
np.set_printoptions(precision=12, linewidth=200)
L=8;K=4
sp=Space(L,11,K)
r,g,refs=tune(sp,K)
raw,conn,sp8=vacuum_tables(L,K,r,g)
print('sp8 dim',sp8.dim)
for j in range(2*L+1):
    print(j/2, raw[j], conn[j]-raw[j])
