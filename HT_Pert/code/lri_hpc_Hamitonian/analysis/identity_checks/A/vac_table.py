"""E_vac(L') through eps^4 for all half-integer L' in [0,L] (same r,g tuned at L);
checks Dfull(E0)=E_vac(L)-E_vac(L-E0) against g^2 D (eps^2), g^2 D + g1^3 W (eps^3)."""
import sys,time,json
from ht4 import *
L=int(sys.argv[1]); pm=int(sys.argv[2]) if len(sys.argv)>2 else 8
t0=time.time()
sp=Space(L,pm,8,3)
_,_,r,g=calibrate(sp,3)
r=np.r_[r,0.];g=np.r_[g,0.]
Lps=[x/2 for x in range(0,2*L+1)]
tab={}
for Lp in Lps:
    tab[Lp]=evac(sp,Lp,4,r,g)
K=4;sums=vacuum_table(L,K);gg=np.convolve(g,g)[:K+1]
def g2D(E0):
    up=max(0,int(math.floor(L-E0+1e-12)))
    D=np.array([-(sums[L,k]-sums[up,k])/6 for k in range(K+1)])
    return np.convolve(gg,D)[:K+1]
print(f'L={L} dim={sp.dim} r={r[:4]} g={g[:4]} ({time.time()-t0:.1f}s)')
print(' Lp     Evac2        Evac3        Evac4    | E0  W  Dfull2-g2D2  Dfull3-g2D3-g1^3W  Dfull4   g2D4  Dfull4-g2D4')
for Lp in Lps:
    E0=L-Lp;W=window_W(L,E0);Df=tab[L]-tab[Lp];G=g2D(E0)
    print(f'{Lp:5.1f} {tab[Lp][2]:+.8f} {tab[Lp][3]:+.8f} {tab[Lp][4]:+.8f} | {E0:4.1f} {W:2d} {Df[2]-G[2]:+.1e} {Df[3]-G[3]-W/27:+.1e} {Df[4]:+.8f} {G[4]:+.8f} {Df[4]-G[4]:+.8f}')
json.dump({'L':L,'r':r.tolist(),'g':g.tolist(),'tab':{str(k):v.tolist() for k,v in tab.items()}},open(f'vac_table_L{L}.json','w'))
print('time',time.time()-t0)
