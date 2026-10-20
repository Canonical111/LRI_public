#!/usr/bin/env python3
"""Normalized conformal zig-zag periods for 2<d<=4 via a spectral integral.
The spectral formula is valid on the real nu-axis only for d>2.  It must not
be evaluated below d=2 without the crossed-pole residues.
Numerics: Gauss--Legendre in nu=(n+p)/2 * u/(1-u), Euler transform of the
alternating angular sums at L=3,5. L=4 is a plain finite-spin partial sum.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.special import gammaln,loggamma,roots_legendre,zeta
import mpmath as mp

def terms(d,loops,spins=256,nodes=256):
    if not 2<d<=4:raise ValueError('This real-contour implementation requires 2<d<=4')
    p=d/2-1;xx,ww=roots_legendre(nodes);u=(xx+1)/2;ww=ww/2
    n=np.arange(spins)[:,None];x=n+p
    v=x/2*u/(1-u);jac=x/2/(1-u)**2
    lr=(gammaln(p)-gammaln(2*p)+gammaln(n+2*p)-gammaln(n+1)+np.log(x)
        -np.log(2)-(1.5*d+1)*np.log(np.pi)+np.log(x*x+4*v*v)
        +2*(loggamma(p+2j*v)-loggamma(2j*v)).real)
    lt=d/2*np.log(np.pi)+2*(loggamma(n/2+d/8+1j*v)-loggamma(n/2+3*d/8+1j*v)).real
    lh=gammaln(d/2)-d/2*np.log(np.pi)
    result={}
    for L in loops:
        result[L]=(np.exp(lr+(L+2)*lt+(L-1)*lh)*jac*ww).sum(axis=1)
    return result

def euler(a,start=12,depth=80):
    seq=np.array(a[start:start+depth],dtype=np.longdouble)
    v=np.sum(np.array(a[:start],dtype=np.longdouble)*(-1)**np.arange(start))
    tail=np.longdouble(0);factor=np.longdouble(.5)
    while len(seq):
        tail+=seq[0]*factor;seq=seq[:-1]-seq[1:];factor*=np.longdouble(.5)
    return float(v+(-1)**start*tail)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('primitive_spectral_checks.json'));args=p.parse_args()
    mp.mp.dps=50;rows=[]
    for d in [3.,4.]:
        for nodes in [192,320]:
            vals=terms(d,[3,4,5],spins=1024,nodes=nodes)
            row=dict(d=d,nodes=nodes,spins=1024,P3_euler=euler(vals[3]),P5_euler=euler(vals[5]),
                     P4_partial_sums={str(N):float(vals[4][:N].sum()) for N in [128,256,512,1024]})
            if d==4:
                row['known_graph_limits']={3:float(6*mp.zeta(3)),4:float(20*mp.zeta(5)),5:float(mp.mpf(441)/8*mp.zeta(7))}
                row['P3_error']=row['P3_euler']-row['known_graph_limits'][3]
                row['P5_error']=row['P5_euler']-row['known_graph_limits'][5]
            rows.append(row);print(row,flush=True)
    out=dict(scope='primitive periods only, not complete C4 or C5; numerical checks are not rigorous error bounds',
             L4='unextrapolated positive partial sums; omitted angular tail is not included',rows=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
