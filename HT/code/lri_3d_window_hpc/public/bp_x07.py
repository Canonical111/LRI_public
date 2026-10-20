#!/usr/bin/env python3
"""Borel-Pade value of the d = 3 epsilon series at Delta_sigma = x (default 0.7), the continuum reference
of the HT note's BP-0.7 and BP-DEV numbers (macros \\HTnpDthreeBPerr, \\HTnpDthreeBPdev).

Delta_E = 3/2 - eps/6 + eps^2 f(eps), eps = 3 - 4x, f = sum_n C_{n+2} eps^n.
Borel-Leroy transform with b = 0..4, Pade [m/n] in {[2/3],[3/2],[1/4],[4/1],[2/2],[3/1],[1/3]};
approximants with a pole on the positive real axis are rejected. Quoted: the median over the accepted
approximants (29 at x = 0.7), with the half-spread (max - min)/2 as the uncertainty.

Provenance: the functions pade() and borel_pade() and the coefficient list C are copied unchanged from the
inline script that produced the quoted 1.4721437 (spread 1.4721093..1.4721664, n = 29) on 2026-10-08
(Claude Code session phi4HT3d, independent check of the 3D window HT, INDEPENDENT_CHECK.md Sec. B2).
Only this command-line wrapper is new.

C0..C7 are the d = 3 GFF coefficients of the paper (Table tab:pt); their records live in the GFF folder:
C2, C3 exact; C4(3) = 1.228063545 and C5(3) = -5.850351421 (closed forms, GFF/code/LRI_C5_d3);
C6(3) = 33.57542664 (GFF/results/C6_3, quoted 33.5754(5)); C7(3) = -220.35448 (GFF/results/C7_3, quoted -220.35(13)).
"""
import argparse, json
import numpy as np
from scipy.integrate import quad
from scipy.special import gamma

C=[1.5,-1/6,0.181221785406,-0.353581520433,1.228063545,-5.850351421,33.57542664,-220.35448]
# work with f(eps) = (Delta - 3/2 + eps/6)/eps^2 = sum_{n>=0} c_n eps^n, c_n = C_{n+2}
c=np.array(C[2:])
def pade(a,m,n):
    # [m/n] Pade of series a
    N=m+n
    A=np.zeros((n,n)); b=np.zeros(n)
    for i in range(n):
        for j in range(n):
            k=m+1+i-(j+1)
            A[i,j]=a[k] if 0<=k<len(a) else 0
        b[i]=-a[m+1+i]
    q=np.concatenate([[1],np.linalg.solve(A,b)]) if n>0 else np.array([1.])
    p=np.array([sum(q[j]*a[i-j] for j in range(0,min(i,n)+1)) for i in range(m+1)])
    return p,q
def borel_pade(eps,b,m,n):
    a=np.array([c[k]/gamma(k+b+1) for k in range(len(c))])
    p,q=pade(a,m,n)
    # reject poles on positive real axis
    roots=np.roots(q[::-1]) if n>0 else []
    if any(abs(r.imag)<1e-9 and r.real>0 for r in roots): return None
    f=lambda t: np.exp(-t)*t**b*np.polyval(p[::-1],eps*t)/np.polyval(q[::-1],eps*t)
    val,err=quad(f,0,np.inf,limit=400)
    return val

def bp(x):
    """Median, min, max and count of the accepted Borel-Pade approximants at Delta_sigma = x."""
    eps=3-4*x
    vals=[]
    for b in (0,1,2,3,4):
        for m,n in ((2,3),(3,2),(1,4),(4,1),(2,2),(3,1),(1,3)):
            v=borel_pade(eps,b,m,n)
            if v is not None and np.isfinite(v): vals.append(1.5-eps/6+eps**2*v)
    vals=np.array(vals)
    return {'x':x,'eps':eps,'median':float(np.median(vals)),'min':float(vals.min()),'max':float(vals.max()),
            'half_spread':float((vals.max()-vals.min())/2),'n':int(len(vals))}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--x',type=float,nargs='+',default=[0.7])
    ap.add_argument('--out')
    a=ap.parse_args()
    rows=[bp(x) for x in a.x]
    for r in rows:print(f"x={r['x']:<7} eps={r['eps']:.3f}  BP median {r['median']:.7f} (spread {r['min']:.7f}..{r['max']:.7f}, n={r['n']})")
    if a.out:
        with open(a.out,'w') as f:json.dump({'C':C,'rows':rows},f,indent=1)
