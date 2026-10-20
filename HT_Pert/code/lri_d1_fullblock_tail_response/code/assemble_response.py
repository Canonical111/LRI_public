"""Two-vertex high kernel times complete finite-low-space susceptibilities.
This is deliberately NOT named the complete C6/C7/C8 tail. It leaves all higher
hard matching, high/low coupling conversion and overlap cancellations explicit.
"""
from pathlib import Path
import argparse,json
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]

def exponential(a,n):
    out=[mp.mpf(1)]
    for k in range(1,n+1):out.append(sum(j*a[j]*out[k-j] for j in range(1,k+1))/k)
    return out

def evaluate(mu,Lambda):
    if mu<2 or mu%2 or Lambda<=mu:raise ValueError('Need even mu>=2 and outer Lambda>mu; reliable high asymptotics require mu << Lambda.')
    mp.mp.dps=40
    s6=json.loads((ROOT/f'results/dconn_phi6_L{mu}_d8.json').read_text())['response']
    sj=json.loads((ROOT/f'results/dconn_full_L{mu}_d8.json').read_text())['response']
    ell=mp.log(Lambda);a=[mp.mpf(0),-ell/2-1-mp.euler/2-mp.log(2)]
    b=[mp.mpf(0),-3*ell/2+3-3*mp.euler/2-3*mp.log(2)]
    for j in range(2,7):
        a.append(((-1)**j-(1-mp.power(2,-j))*mp.zeta(j))/j)
        b.append(mp.power(3,j)*(1-(1-mp.power(2,-j))*mp.zeta(j))/j)
    ea=exponential(a,6);eb=exponential(b,6)
    rows=[]
    for n in range(2,9):
        first=-sum(ea[n-j]*mp.mpf(str(s6[j])) for j in range(2,n+1))/(9*mp.sqrt(mp.pi*Lambda))
        second=2*sum(eb[n-j]*mp.mpf(str(sj[j])) for j in range(2,n+1))/(3*mp.sqrt(mp.pi*Lambda))
        rows.append(dict(order=n,phi6_component=str(first),bath_phase_component=str(second),sum=str(first+second)))
    return dict(low_mu=mu,outer_Lambda=Lambda,rows=rows,scope='Partial two-high-vertex leading kernel in the declared low-coupling convention. Not a physical Cn prediction or complete renormalized cutoff tail.')
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--mu',type=int,default=8);a.add_argument('--Lambda',type=float,default=1024);x=a.parse_args();print(json.dumps(evaluate(x.mu,x.Lambda),indent=2))
