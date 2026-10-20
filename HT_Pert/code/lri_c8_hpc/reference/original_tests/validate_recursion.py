#!/usr/bin/env python3
"""Independent full eighth-order SciPy recursion, with the untruncated particle cap.
The production code uses order-4 wavefunctions and a quotient instead.
"""
from pathlib import Path
import sys,json,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'reference'),str(ROOT/'code')]
from check_lri_hamiltonian import FockSpace,initial_wavefunctions
from c8_solver import compute
from lri_hpc.solver import atomic_json

def independent_D(space,degree):
    # Independent polynomial recurrence for coefficients ((2-2e)_m/m!)/(m+1-e).
    import math
    sums=np.zeros((space.cutoff+1,degree+1))
    w=np.zeros(degree+1);w[0]=1
    for m in range(space.cutoff):
        if m:
            new=np.zeros_like(w)
            for k in range(degree+1):
                new[k]=(m+1)*w[k]/m
                if k:new[k]-=2*w[k-1]/m
            w=new
        sums[m+1]=sums[m]
        if m%2==0:
            for k in range(degree+1):
                sums[m+1,k]+=sum(w[j]/(m+1)**(k-j+1) for j in range(k+1))
    upper=np.maximum(0,(4*space.cutoff-4*space.N-space.P)//4)
    return -(sums[space.cutoff][None,:]-sums[upper])/6

def full(cutoff,scheme):
    n=8;space=FockSpace(cutoff,pmax=4*cutoff,degree=n-1)
    if scheme=='raw':
        _,E,r,g=initial_wavefunctions(space,order=n)
        return {'C':E[2]-E[0],'r':r,'g':g}
    D=independent_D(space,n-2)
    psi=[np.zeros((n+1,space.dim)) for _ in range(4)]
    E=np.zeros((4,n+1));r=np.zeros(n+1);g=np.zeros(n+1)
    for p in range(4):psi[p][0,space.refs[p]]=1;E[p,0]=p/4
    for k in range(1,n+1):
        raw=[];rhs=[];gg=np.convolve(g,g)
        for p in range(4):
            m,v=space.vertices(psi[p][:k],k-1)
            t=space.F1*psi[p][k-1]
            for j in range(1,k):t+=r[j]*m[k-j]+g[j]*v[k-j]
            for j in range(2,k+1):
                for l in range(k-j+1):t+=gg[j]*D[:,l]*psi[p][k-j-l]
            rhs.append(t);raw.append(t[space.refs[p]])
        r[k]=((-.25 if k==1 else 0)-(raw[1]-raw[0]))/2
        g[k]=((.25 if k==1 else 0)-(raw[3]-raw[0])-6*r[k])/3
        for p in range(4):
            m,v=space.vertices(psi[p][:1],0)
            t=rhs[p]+r[k]*m[0]+g[k]*v[0]
            E[p,k]=t[space.refs[p]]
            for j in range(1,k+1):t-=E[p,j]*psi[p][k-j]
            den=p/4-space.Efree
            sel=space.even&(space.P%2==p%2)&(den!=0)
            psi[p][k,sel]=t[sel]/den[sel]
    return {'C':E[2]-E[0],'r':r,'g':g}

if __name__=='__main__':
    import numba
    numba.set_num_threads(2)
    rows=[]
    for scheme in ('raw','vacuum_only'):
        for L in (2,4,6,8,12):
            start=time.perf_counter();a=compute(L,scheme=scheme);b=full(L,scheme)
            residuals={k:float(np.max(abs(np.array(a[k])-b[k]))) for k in ('C','r','g')}
            for k in ('C','r','g'):np.testing.assert_allclose(a[k],b[k],rtol=5e-11,atol=1e-7)
            row={'scheme':scheme,'cutoff':L,'max_abs_residuals':residuals,'C8':a['C'][8],
                 'seconds':time.perf_counter()-start,'status':'pass'}
            rows.append(row);print(row,flush=True)
    atomic_json(ROOT/'results/validation_full_recursion.json',rows)
