#!/usr/bin/env python3
"""Full periodic Euclidean power-law couplings in 1, 2, or 3 dimensions.

Ewald splitting with dimensionless splitting parameter alpha^2=pi.
J_L(r)=sum_{m in Z^d}|r+Lm|^{-d-s}, excluding r=0 (constant self images).
Both real and reciprocal sums converge exponentially. No distance cutoff in H.
Arrays use x-fastest packed coordinates, identical to C++ (C ravel reverses axes,
which is immaterial for this permutation-symmetric kernel).
"""
from __future__ import annotations
import argparse, itertools, json
from pathlib import Path
import numpy as np
from scipy.special import gamma, gammaincc

def ewald_unique(u: np.ndarray, d: int, s: float, cut: int=4) -> np.ndarray:
    if not 0 < s < 2: raise ValueError('Ewald implementation requires 0<s<2')
    a=(d+s)/2; b=s/2
    z=np.zeros(len(u));
    for m in itertools.product(range(-cut,cut+1),repeat=d):
        r2=np.sum((u+np.array(m))**2,axis=1)
        use=r2>0
        z[use]+=gammaincc(a,np.pi*r2[use])*r2[use]**(-a)
    reciprocal=np.full(len(u),1/b)
    # Sign sums are products of cosines; only nonnegative reciprocal indices.
    cs=np.cos(2*np.pi*u[:,:,None]*np.arange(cut+1)[None,None,:])
    for k in itertools.product(range(cut+1),repeat=d):
        r2=sum(v*v for v in k)
        if r2==0: continue
        t=np.pi*r2
        c=(np.exp(-t)-t**b*gamma(1-b)*gammaincc(1-b,t))/b
        mult=2**sum(v>0 for v in k)
        cosine=np.ones(len(u))
        for j,v in enumerate(k):cosine*=cs[:,j,v]
        reciprocal+=mult*c*cosine
    return z+np.pi**a/gamma(a)*reciprocal

def couplings(d:int,L:int,s:float,cut:int=4) -> np.ndarray:
    if d not in (1,2,3) or L<2 or L&(L-1): raise ValueError('d in 1..3 and power-of-two L>=2 required')
    tup=np.array(list(itertools.combinations_with_replacement(range(L//2+1),d)),dtype=int)
    values=ewald_unique(tup/L,d,s,cut)*L**(-d-s)
    # J(0)=0; all self-image contributions are spin-independent constants.
    values[0]=0
    coords=np.indices((L,)*d,dtype=np.int32).reshape(d,-1).T
    coords=np.minimum(coords,L-coords);coords.sort(axis=1)
    base=L//2+1;powers=base**np.arange(d,dtype=np.int64)
    lookup=np.zeros(base**d);lookup[tup@powers]=values
    full=lookup[coords@powers]
    if np.any(full<0) or not np.all(np.isfinite(full)):raise ArithmeticError('bad Ewald kernel')
    return full

def save_kernel(path:Path,d:int,L:int,s:float,cut:int=4):
    path.parent.mkdir(parents=True,exist_ok=True)
    a=couplings(d,L,s,cut);a.astype('<f8').tofile(path)
    meta=dict(d=d,L=L,N=L**d,s=s,cut=cut,Jsum=float(a.sum()),
        model='Full periodic-image Euclidean |r|^(-d-s), J[0]=0',dtype='<f8',
        indexing='packed base-L site/displacement coordinates; x fastest')
    path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dim',type=int,required=True)
    p.add_argument('--length',type=int,required=True);p.add_argument('--s',type=float,required=True)
    p.add_argument('--cut',type=int,default=4);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(save_kernel(a.out,a.dim,a.length,a.s,a.cut),indent=2))
