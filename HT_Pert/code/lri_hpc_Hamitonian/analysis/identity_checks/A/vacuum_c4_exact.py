#!/usr/bin/env python3
"""Exact fourth-order thermal shift of the isolated g^2 D correction.

No target C4 or large-cutoff fit is used. On even cutoffs:
 delta C4 = 485/8748 + sum_{n=2,4,...,L-2}[v_n A(n)+B(n)].
The sum is NOT convergent as L->infinity: delta C4 ~ log L/17496 + const.
"""
from __future__ import annotations
from fractions import Fraction as F
from pathlib import Path
import argparse,json,math

def A(n):
    return (F(7,729)/(2*n+1)+F(1,81)/(2*n+1)**2+
      F(1,2187)/(2*n-1)+F(1,2187)/(2*n-1)**2+
      F(1,4374)/(n+1)+F(1,4374)/(n+1)**2+F(1,486)/n)
def B(n):return F(8,243)/(2*n+1)**2+F(1,8748)/(n+1)
def exact(L):
    if L<2 or L%2:raise ValueError('even cutoff >=2')
    v=F(1);ans=F(485,8748)
    for n in range(1,L-1):
        v*=F(2*n-1,2*n)
        if n%2==0:ans+=v*A(n)+B(n)
    return ans

def fast(L):
    if L<2 or L%2:raise ValueError('even cutoff >=2')
    v=1.;terms=[]
    for n in range(1,L-1):
        v*=(n-.5)/n
        if n%2==0:terms.append(v*float(A(n))+float(B(n)))
    return 485/8748+math.fsum(terms)

def renormalized_constant(dps=60):
    """Compute finite part K of this isolated diagrammatic prescription.
    This is a mathematical finite part, NOT a newly fixed physical counterterm.
    """
    import mpmath as mp
    mp.mp.dps=dps
    def feven_minus_one(x):
        if x<mp.mpf('.001'):
            return mp.fsum(mp.rf(mp.mpf('.5'),2*j)/mp.factorial(2*j)*x**(2*j) for j in range(1,15))
        return (1/mp.sqrt(1-x)+1/mp.sqrt(1+x))/2-1
    def S(a,k):
        return mp.quad(lambda x:x**(a-1)*feven_minus_one(x)*(-mp.log(x))**(k-1),[0,.1,.5,.9,1])
    c=mp.mpf(485)/8748
    c+=mp.mpf(7)/1458*S(mp.mpf('.5'),1)+mp.mpf(1)/324*S(mp.mpf('.5'),2)
    c+=mp.mpf(1)/4374*S(mp.mpf('-.5'),1)+mp.mpf(1)/8748*S(mp.mpf('-.5'),2)
    c+=mp.mpf(1)/4374*(S(1,1)+S(1,2))+mp.mpf(1)/486*S(0,1)
    c+=((mp.euler+mp.log(2))/2-1)/8748+mp.polygamma(1,mp.mpf('1.25'))/486
    return str(c)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=Path('vacuum_c4_analytic.json'))
    ap.add_argument('--cutoffs',type=int,nargs='+',default=[4,8,16,24,40,50,64,80,100,118,160,1024,65536])
    a=ap.parse_args();K=renormalized_constant();kf=float(K);rows=[]
    for L in a.cutoffs:
        val=float(exact(L)) if L<=160 else fast(L)
        approx=math.log(L)/17496+kf-16/(2187*math.sqrt(math.pi*L))-1/(243*L)
        rows.append(dict(cutoff=L,delta_C4=val,asymptotic_through_inverse_L=approx,residual=val-approx))
    out=dict(log_coefficient='1/17496',finite_part=K,
        caveat='The finite part depends on subtraction convention and is not a physical continuum correction.',
        rows=rows)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
