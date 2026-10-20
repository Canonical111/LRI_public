"""Check closed form R(L') = -(g1^4/36) sum_{E odd<=L'} n_L'(E)/E  (n = #odd k in (L'-E, L'])
against an explicit RS of the vacuum at cutoff L' WITH the g^2 D operator whose windows are
measured from L' (self-consistent 'corrected vacuum')."""
import sys
from ht4 import *
def Rclosed(Lp,g1=1/3):
    s=0.
    for E in range(1,int(math.floor(Lp))+1,2):
        n=sum(1 for k in range(1,int(math.floor(Lp))+1) if k%2==1 and Lp-E<k<=Lp)
        s+=n/E
    return -(g1**4/36)*s
for L in [int(a) for a in sys.argv[1:]]:
    sp=Space(L,8,8,3);_,_,r,g=calibrate(sp,3);r=np.r_[r,0.];g=np.r_[g,0.]
    gg=np.convolve(g,g)[:5]
    for Lp in [L,L-.5,L-1,L-1.5,L-2,L-2.5,L/2+.5]:
        # D window relative to Lp, eps^0 shell weights (exact jets of vacuum_table not needed at eps^4)
        q=np.floor(4*Lp+1e-9).astype(int)
        sums=vacuum_table(L,4)
        up=np.maximum(0,(q-4*sp.N.astype(np.int64)-sp.P.astype(np.int64))//4)
        top=int(math.floor(Lp))
        D=np.stack([-(sums[min(top,L),k]-sums[np.minimum(up,top),k])/6 for k in range(5)],1)
        diag=np.zeros((sp.dim,5))
        for a in range(5):
            for b in range(5-a): diag[:,a+b]+=gg[a]*D[:,b]
        mask=(sp.N%2==0)&(sp.P%2==0)&((4*sp.N+sp.P)<=q)
        e_corr=block_rs(sp,[0],4,r,g,mask,diag=diag)[0][:,0,0]
        e_raw=evac(sp,Lp,4,r,g)
        print(f'L={L} Lp={Lp:5.1f}  Ecorr-Eraw = {np.round(e_corr-e_raw,12).tolist()}  closed R={Rclosed(Lp):+.12f}')
