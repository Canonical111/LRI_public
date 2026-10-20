"""Single-particle descendants a_n|0> (level n, W=ceil(n/2)) through eps^4, three operator
prescriptions; r4 retuning is applied later from the main run at the same L (first-order
diag of a_n is r4*2u_n(0)^2, V0=0)."""
import sys,time,json
from ht4 import *
L=int(sys.argv[1]);nmax=int(sys.argv[2]) if len(sys.argv)>2 else 6
K=4;t0=time.time()
sp=Space(L,9,9,3)
_,_,r,g=calibrate(sp,3);r0=np.r_[r,0.];g0=np.r_[g,0.]
g2=g2D_jets(sp,g0,K)
out={'L':L,'r':r0.tolist(),'g':g0.tolist(),'states':{}}
Ev={}
for n in range(0,nmax+1):
    s=find(sp,1,n);assert len(s)==1;s=s[0]
    E0=float(sp.Efree[s]);Lp=math.floor(2*(L-E0)+1e-9)/2
    for x in (float(L),Lp):
        if x not in Ev:Ev[x]=evac(sp,x,K,r0,g0)
    dd=Ev[float(L)]-Ev[Lp]
    mask=sector_mask(sp,s)
    h_raw,first,spect,spc=block_rs(sp,[s],K,r0,g0,mask)
    h_g2,_,_,_=block_rs(sp,[s],K,r0,g0,mask,diag=g2)
    rec=dict(E0=E0,W=window_W(L,E0),h_raw=h_raw[:,0,0].tolist(),h_g2D=h_g2[:,0,0].tolist(),
             M0=float(first[0,0,0]),V0=float(first[0,0,1]),Dfull_s=dd.tolist(),g2D_s=g2[s].tolist(),
             spectators=[(int(j),int(sp.P[j]),int(sp.N[j])) for j in spect],
             spect_coupling_max=[float(np.max(np.abs(spc[k]))) if len(spect) else 0. for k in range(K+1)])
    out['states'][f'a{n}']=rec
json.dump(out,open(f'sp_L{L}.json','w'))
print(f'L={L} dim={sp.dim} {time.time()-t0:.1f}s',{k:(v['W'],v['spectators'],['%.0e'%x for x in v['spect_coupling_max']]) for k,v in out['states'].items()})
