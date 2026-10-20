"""C4 shift of Dfull relative to g^2 D:  dC4 = -B/3,  B = E_vac^(4)(L)-E_vac^(4)(L-1)
= -g1^4 sum_{j: E_j in {L-1/2, L}} |<j|V0|chi>|^2/E_j,  chi = sum_b V0_b0|b>/E_b (4-particle).
Also A = E_vac^(4)(L)-E_vac^(4)(L-1/2) (E_j = L only), split by P (6 vs 8)."""
import sys,time,json
from ht4 import *
res={}
for L in [int(a) for a in sys.argv[1:]]:
    t0=time.time()
    sp=Space(L,8,8,0)
    x=np.zeros((sp.dim,1));x[0,0]=1.
    m,v=vertices_nomask(sp,x,0,0)
    ok=(sp.N%2==0)&(sp.P==4)
    chi=np.where(ok,v[:,0]/np.where(ok,sp.Efree,1.),0.)[:,None]
    m2,v2=vertices_nomask(sp,np.ascontiguousarray(chi),0,0)
    y=v2[:,0]
    E4=4*sp.N+sp.P
    g1=1/3
    top8=(sp.N%2==0)&(E4==4*L)
    top6=(sp.N%2==0)&(E4==4*L-2)
    assert np.all(sp.P[top8]==8) or True
    c8=-g1**4*np.sum(y[top8]**2/sp.Efree[top8])
    c6=-g1**4*np.sum(y[top6]**2/sp.Efree[top6])
    P8=np.unique(sp.P[top8]);P6=np.unique(sp.P[top6])
    A=c8;B=c8+c6
    res[L]=dict(A=A,B=B,c6=c6,c8=c8,dC4=-B/3)
    print(f'L={L:4d} dim={sp.dim:>10,d} A={A:+.10f} B={B:+.10f} (P6 part {c6:+.10f}, P8 part {c8:+.10f}; P sets {P6.tolist()},{P8.tolist()}) dC4(Dfull-g2D)={-B/3:+.10f} ({time.time()-t0:.1f}s)',flush=True)
json.dump(res,open('c4shift_'+sys.argv[1]+'_'+sys.argv[-1]+'.json','w'))
