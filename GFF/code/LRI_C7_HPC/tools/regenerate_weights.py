#!/usr/bin/env python3
"""Generate portable meromorphic Chebyshev weights at arbitrary working precision.

This is the same degree/rule as the archived generator, not a different quadrature.
Use a separate inputs directory. Existing files are never overwritten. For a new
large degree, run at two precisions and compare before production.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference/code'))
from chebyshev_coefficients import chebpoly
sys.path.insert(0,str(ROOT/'tools'))
from campaign import publish

def weights(L:int,N:int,dps:int)->list[str]:
    mp.mp.dps=dps;D=L-1;M=6;nn=N+1;pol=chebpoly(N)
    cx=[[mp.cos(mp.pi*k*i/N) for k in range(nn)] for i in range(nn)];out=[]
    for axis in range(D):
        for b2 in range(2*L+1):
            a=mp.mpf(L-2-axis)-mp.mpf(b2)/2;b=mp.mpf(b2)/2
            jr=int(-a-1) if a<=-1 and int(2*a)%2==0 else -1;mom=[]
            for pp in pol:
                row=[]
                for order in range(-1,M+1):
                    if order==-1:v=mp.mpf(pp[jr])/b if 0<=jr<len(pp) and b else mp.mpf(0)
                    else:v=mp.fsum(mp.mpf(c)*(-b)**order/(mp.mpf(k)+a+1)**(order+1) for k,c in enumerate(pp) if k!=jr)
                    row.append(v)
                mom.append(row)
            for order in range(M+2):
                for i in range(nn):
                    factor=mp.mpf(2)/N*(mp.mpf('.5') if i in (0,N) else 1)
                    value=factor*mp.fsum((mp.mpf('.5') if k in (0,N) else 1)*cx[i][k]*mom[k][order] for k in range(nn))
                    if jr==0 and order==0:value=1/b if i==N else mp.mpf(0)
                    out.append(mp.nstr(value,dps))
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--L',type=int,choices=range(2,8),required=True);p.add_argument('--degrees',nargs='+',type=int,required=True);p.add_argument('--dps',type=int,default=100);a=p.parse_args()
    if a.dps<80 or any(n<1 or n>254 for n in a.degrees):raise ValueError('require >=80 digits and degrees 1..254')
    a.out.mkdir(parents=True,exist_ok=True)
    for n in sorted(set(a.degrees)):
        f=a.out/f'cw_L{a.L}_N{n}.txt'
        if f.exists():raise FileExistsError(f)
        values=weights(a.L,n,a.dps);publish(f,'C7WEIGHTS1 '+str(len(values))+'\n'+'\n'.join(values)+'\n');print(f)
    mp.mp.dps=a.dps;log=[mp.mpf(0)]*7;log[1]=a.L*mp.log(2)
    for j in range(2,7):log[j]=(a.L**j-a.L)*mp.polygamma(j-1,1)/mp.factorial(j)
    cf=[mp.mpf(1)]+[mp.mpf(0)]*6
    for j in range(1,7):cf[j]=mp.fsum(k*log[k]*cf[j-k] for k in range(1,j+1))/j
    f=a.out/f'cgamma_L{a.L}.txt'
    if not f.exists():publish(f,' '.join(mp.nstr(v,a.dps) for v in cf)+'\n')
    else:print('Retaining existing Gamma file:',f)
    publish(a.out/f'weights_L{a.L}_provenance.json',json.dumps({'loops':a.L,'degrees':a.degrees,'working_decimal_digits':a.dps,'mpmath':mp.__version__,'rule':'original meromorphic Chebyshev tensor weights; no degree/rule change'},indent=2)+'\n')
if __name__=='__main__':main()
