"""Per-level eps^4 vacuum density beyond g^2D: delta(E0)=[Dconn - g2D]^(4)(E0), E0 = 0,1/2,...;
increments per half-step = density of vacuum-sector level E=L-E0+1/2... (connected, leftover-free)."""
import sys,json
from ht4 import *
from analyze import Rclosed
L=int(sys.argv[1]);K=4
sp=Space(L,8,8,3);_,_,r,g=calibrate(sp,3);r=np.r_[r,0.];g=np.r_[g,0.]
sums=vacuum_table(L,K);gg=np.convolve(g,g)[:K+1]
def g2D(E0):
    up=max(0,int(math.floor(L-E0+1e-12)))
    return np.convolve(gg,np.array([-(sums[L,k]-sums[up,k])/6 for k in range(K+1)]))[:K+1]
Lps=[L-x/2 for x in range(0,2*int(sys.argv[2])+1)]
Ev={Lp:evac(sp,Lp,K,r,g) for Lp in Lps}
prev=0.;prevf=0.;rows=[]
print(f'L={L} g2={g[2]:.5f} g3={g[3]:.5f} r2={r[2]:.5f}')
print(' E0   level   Dfull-g2D(4)  Dconn-g2D(4)   step(Dconn)  step(Dfull)')
for Lp in Lps:
    E0=L-Lp
    df=(Ev[L]-Ev[Lp])[4]-g2D(E0)[4]
    dc=df+Rclosed(L)-Rclosed(Lp)
    print(f'{E0:4.1f}  E={Lp:5.1f}  {df:+.8f}  {dc:+.8f}  {dc-prev:+.8f}  {df-prevf:+.8f}')
    rows.append((E0,df,dc));prev=dc;prevf=df
json.dump(rows,open(f'vac_density_L{L}.json','w'))
