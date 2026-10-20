import sys,time,resource
sys.path.insert(0,'pkg')
from lri_hpc.operators import Space
L=int(sys.argv[1]);p=int(sys.argv[2]);q=int(sys.argv[3])
t=time.time();sp=Space(L,p,q,4)
print(L,p,q,'dim',sp.dim,'edges GB',sp.edges_bytes/1e9,'build',time.time()-t,'maxrss GB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e9)
