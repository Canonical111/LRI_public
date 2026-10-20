#!/usr/bin/env python3
"""Withheld-cutoff prediction, alternative tails, and numerical sensitivity."""
from pathlib import Path
import json,math
import numpy as np
from extrapolate import data,fit,eval_basis,ls,OMEGA,C2,C3,ROOT

def predict(r,L,C):
    ell=np.log(L+r['shift']); e=[np.ones(len(L))]
    for n in range(1,7):e.append(ell/n*sum(j*OMEGA[j]*e[n-j] for j in range(1,n+1)))
    out=np.zeros_like(C);out[:,:4]=C[:,:4]
    for n in range(4,9):
        b=np.array(r['details'][n-4]['coefficients'])
        out[:,n]=eval_basis(L,C[:,2]-C2,r['model'],r['shift'],n==8)@b
        for j in range(1,n-1):out[:,n]-=e[j]*(out[:,n-j]-r['limits'][n-j])
    return out


def direct_fit(L,C,lo=16,hi=50,extra='none'):
    mask=(L>=lo)&(L<=hi);z=L[mask];ell=np.log(z)
    leading=-117649/(93312*np.sqrt(np.pi))
    y=C[mask,8]-leading*z**-.5*ell**6
    X=[np.ones(len(z))]+[z**-.5*ell**k for k in range(6)]
    if extra in ('L1','L1_L15'):X+=[z**-1]
    if extra=='L1_L15':X+=[z**-1.5]
    X=np.array(X).T
    if len(z)<=X.shape[1]:return None
    b,cond=ls(X,y,70)
    return dict(lo=lo,hi=hi,extra=extra,C8=float(b[0]),residual=float(np.max(abs(X@b-y))),condition=cond,
                scope='Standalone eighth-order highest-log-constrained fit; no lower-order tail linking')


def main():
    L,C=data();held=[]
    for m in ('A','B','C'):
        r=fit(L,C,16,40,m,mp_dps=70)
        mask=L>40;p=predict(r,L[mask],C[mask])
        err=np.max(abs(p-C[mask]),axis=0)
        held.append(dict(model=m,train=[16,40],test=[42,50],max_absolute_errors=err.tolist(),
                         limits=r['limits'],fixed_inputs='Only C2,C3 at withheld cutoffs; higher orders recursively predicted'))
    alternatives=[direct_fit(L,C,lo,50,e) for lo in (8,12,16,20,24) for e in ('none','L1','L1_L15')]
    # Numerical perturbations probe conditioning, not a rigorous arithmetic bound.
    rng=np.random.default_rng(20261003);sens=[]
    bounds=np.array([0.,0.,2e-14,2e-13,3e-12,5e-11,5e-10,5e-9,5e-8])
    for m in ('A','B','C'):
        ref=fit(L,C,16,50,m)['limits'][8]
        errors=[]
        for _ in range(128):
            noise=rng.uniform(-1,1,C.shape)*bounds
            errors.append(fit(L,C+noise,16,50,m)['limits'][8]-ref)
        sens.append(dict(model=m,max_change=float(np.max(abs(np.array(errors)))),
                         sample_min=float(np.min(errors)),sample_max=float(np.max(errors)),
                         amplitudes=bounds.tolist(),trials=128))
    result=dict(withheld=held,standalone_fits=alternatives,arithmetic_sensitivity=sens)
    (ROOT/'results/extrapolation_diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
