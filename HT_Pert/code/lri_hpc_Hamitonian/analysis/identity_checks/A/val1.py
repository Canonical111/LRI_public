import sys,time
from ht4 import *
from vacuum_c4_exact import fast as exact_dc4
from lri_hpc.solver import compute
L=int(sys.argv[1])
t0=time.time()
sp=Space(L,12,9,3)
print('dim',sp.dim,'build',time.time()-t0)
psi,E,r,g=calibrate(sp,4)
print('r',r);print('g',g)
for p in (0,1,3):
    e,first,spect,spc=scalar_rs(sp,p,4,r,g)
    print(p,'mine',e,'pkg',E[p],'diff',np.max(abs(e-E[p])),'first',first,'spect',spect)
e2,_,_,_=scalar_rs(sp,2,4,r,g);e0,_,_,_=scalar_rs(sp,0,4,r,g)
res=compute(L,'thermal',6)
print('C mine',e2-e0);print('C pkg ',res['C'][:5])
# g2D with retune
D=g2D_jets(sp,g,4)
r0=r.copy();g0=g.copy();r0[4]=0;g0[4]=0
Es={};F={}
for p in (0,1,2,3):
    Es[p],F[p],_,_=scalar_rs(sp,p,4,r0,g0,diag=D)
for p in (0,1,2,3): print('first',p,F[p])
r4=-(Es[1][4]-Es[0][4])/2; g4=(-(Es[3][4]-Es[0][4])-6*r4)/3
C4=(Es[2][4]+r4*F[2][0]+g4*F[2][1])-(Es[0][4]+r4*F[0][0]+g4*F[0][1])
print('g2D r4',r4,'raw r4',r[4],' g4',g4,'raw',g[4])
print('dC4 mine',C4-(e2-e0)[4],'exact',exact_dc4(L))
print('time',time.time()-t0)
