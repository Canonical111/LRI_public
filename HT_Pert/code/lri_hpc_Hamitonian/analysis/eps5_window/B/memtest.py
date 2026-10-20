import resource, sys, numpy as np, time
from htb5 import Space
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e9
L=int(sys.argv[1])
print('start', rss())
sp=Space(4*L,8,None,5,keep_modes=False)
print('space', rss(), sp.dim, sp.nedges, sp.nedges/sp.dim)
mask=(sp.N%2==0)
e0=np.zeros(sp.dim); e0[0]=1
M0,V0=sp.vertices(e0,3,mask); print('vert0', rss())
x=np.random.rand(sp.dim)
M1,V1=sp.vertices(x,2,mask); print('vert1', rss())
