import sys,os
sys.path.insert(0,'pkg')
from lri_hpc.basis import count_tables
for (p,q) in [(7,4),(8,8),(11,8),(12,10),(9,9)]:
    out=[]
    for L in [16,32,64,80,96,118]:
        G,Z=count_tables(L,p,q); out.append(f'{L}:{Z[p,q,4*L]/1e6:.2f}M')
    print(p,q,' '.join(out))
