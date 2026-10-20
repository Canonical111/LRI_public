#!/usr/bin/env python3
"""Independent original-SciPy full seventh-order RS validation of partial matching."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from reference_solver import FockSpace
from run_vacuum_matched import compute
from numba import set_num_threads

def independent_D(space,degree):
    # Direct omitted-shell generation, not the optimized cumulative-table code.
    import math
    coeff=np.zeros((degree+1,space.dim));a=np.zeros(degree+1);a[0]=1
    for m in range(space.cutoff):
        if m:
            a0=a.copy();a=(m+1)/m*a0;a[1:]-=2/m*a0[:-1]
        if m%2:continue
        den=np.array([(m+1.)**(-k-1) for k in range(degree+1)])
        w=np.convolve(a,den)[:degree+1]/(-6.)
        sel=m+1+space.Efree>space.cutoff
        coeff[:,sel]+=w[:,None]
    return coeff

def full(L,degree=7):
    s=FockSpace(L,pmax=min(4*L,31),degree=degree-1)
    D=independent_D(s,degree-2)
    psi=[np.zeros((degree+1,s.dim)) for _ in range(4)]
    E=np.zeros((4,degree+1));r=np.zeros(degree+1);g=np.zeros(degree+1)
    for p in range(4):psi[p][0,s.refs[p]]=1.;E[p,0]=p/4
    for k in range(1,degree+1):
        gg=np.convolve(g,g);rhs=[];raw=[];mv=[];vv=[]
        for p in range(4):
            m,v=s.vertices(psi[p][:k],k-1)
            # psi0 produces complete Taylor-jets of reference vertices.
            mv.append(m[0]);vv.append(v[0])
            t=s.F1*psi[p][k-1]
            for j in range(1,k):t+=r[j]*m[k-j]+g[j]*v[k-j]
            for a in range(2,k+1):
                for d in range(min(k-a,degree-2)+1):
                    t+=gg[a]*D[d]*psi[p][k-a-d]
            rhs.append(t);raw.append(t[s.refs[p]])
        r[k]=((-.25 if k==1 else 0.)-(raw[1]-raw[0]))/2
        g[k]=((.25 if k==1 else 0.)-(raw[3]-raw[0])-6*r[k])/3
        for p in range(4):
            t=rhs[p]+r[k]*mv[p]+g[k]*vv[p]
            E[p,k]=t[s.refs[p]]
            for j in range(1,k+1):t-=E[p,j]*psi[p][k-j]
            den=p/4-s.Efree;sel=s.even&(s.P%2==p%2)&(den!=0)
            psi[p][k,sel]=t[sel]/den[sel]
    return dict(C=E[2]-E[0],r=r,g=g)

if __name__=='__main__':
    set_num_threads(4);records=[]
    for L in (4,6,8):
        ref=full(L);new=compute(L)
        diffs={k:float(np.max(np.abs(np.array(new[k])-ref[k]))) for k in ('C','r','g')}
        assert max(diffs.values())<1e-7,(L,diffs)
        records.append(dict(cutoff=L,max_absolute_differences=diffs))
    (ROOT/'results'/'vacuum_full_recursion_validation.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))
