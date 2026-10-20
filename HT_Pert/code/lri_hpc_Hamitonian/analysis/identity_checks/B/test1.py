import numpy as np, time, sys
from htb import *
for L in [8,12]:
    t=time.time()
    sp=Space(L,11,4)
    r,g,refs=tune(sp,4)
    print('L',L,'dim',sp.dim,'edges',sp.nedges,'build %.2fs'%sp.build_seconds)
    print(' r',r); print(' g',g)
    st2=run_state(sp,sp.index([0,0]),4,r,g)
    print(' C',np.array(st2.E)-np.array(refs[0].E))
    print(' E1-E0',np.array(refs[1].E)-np.array(refs[0].E),' E3-E0',np.array(refs[3].E)-np.array(refs[0].E))
    X=g2D_diag(sp,g,4*L)
    for name,(pr,de) in {'dphi':([0],[1]),'dphi2':([0,0],[0,1]),'dphi3':([0,0,0],[0,0,1])}.items():
        a=run_state(sp,sp.index(pr),4,r,g); b=run_state(sp,sp.index(de),4,r,g)
        ac=run_state(sp,sp.index(pr),4,r,g,X); bc=run_state(sp,sp.index(de),4,r,g,X)
        print(' ',name,'raw',np.array(b.E)-np.array(a.E),'corr(no retune)',np.array(bc.E)-np.array(ac.E))
    print(' time %.1f'%(time.time()-t))
