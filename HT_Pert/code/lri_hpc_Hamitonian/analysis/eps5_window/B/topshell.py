"""C4 shift of Dfull_c beyond g2D = -(1/3) g1^4 [Y_c + Z], eps=0 shell sums on the P<=8 vacuum space.
psi1 = R V|0> (4-particle), (V psi1) on the top unit shell: Y_raw = -sum_{E0=L}|.|^2/L (P=8),
Z = -sum_{E0=L-1/2}|.|^2/(L-1/2) (P=6); Y_c = Y_raw + (1/6) sum_b psi1_b^2 (bubble-bubble pairs restored by g2D)."""
import numpy as np, sys, time, json, math
from htb_big import BigSpace
def run(L):
    t0=time.time()
    sp=BigSpace(L,8,K=1)
    mask=(sp.N%2==0)
    s0=sp.index([])
    e0=np.zeros(sp.dim); e0[s0]=1.
    _,v0=sp.vertices(e0,0,mask)
    E0=sp.E4/4.
    psi1=np.where((sp.E4>0)&mask, -v0[:,0]/np.where(E0>0,E0,1.),0.)
    _,v1=sp.vertices(psi1,0,mask)
    v1=v1[:,0]
    top8=(sp.E4==4*L)&mask; top6=(sp.E4==4*L-2)&mask
    Yraw=-np.sum(v1[top8]**2)/L; Z=-np.sum(v1[top6]**2)/(L-0.5)
    n1=np.sum(psi1**2)
    Hodd=math.fsum(1/e for e in range(1,L,2))
    Yc=Yraw+n1/6
    shift=-(Yc+Z)/(3*81)
    out=dict(L=L,dim=sp.dim,Yraw=Yraw,Z=Z,Yc=Yc,psi1norm2=n1,Hodd_over6=Hodd/6,shift_conn=shift,shift_raw=-(Yraw+Z)/243,
             P8top=int(top8.sum()),P6top=int(top6.sum()),seconds=time.time()-t0)
    print(json.dumps(out),flush=True)
    return out
if __name__=='__main__':
    res=[run(int(a)) for a in sys.argv[1:]]
    json.dump(res,open('topshell_%s.json'%('_'.join(sys.argv[1:])),'w'),indent=1)
