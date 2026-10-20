#!/usr/bin/env python3
"""Independent finite-cutoff epsilon expansion of the supplied LRI Hamiltonian.

Computes C_0,...,C_6 without graph data or using target C_n in the tuning.
This is the two-coupling Hamiltonian in lri_d1_epsilon_expansion_detailed.tex,
not a claim that its infinite-cutoff limit equals the field theory at high order.

Requires Python 3.10+, NumPy and SciPy. Example:
  OPENBLAS_NUM_THREADS=1 python check_lri_hamiltonian.py --cutoffs 4 8 12 16

The cutoff is P/4 + N <= Lambda at epsilon=0; it is NOT moved with epsilon.
The sphere parity projection N mod 2 is applied after each complete vertex,
never between the individual creation/annihilation factors of that vertex.
The normalized Fock basis uses u_n(epsilon)^2=((1-epsilon)/2)_n/n!.

Wavefunctions through epsilon^3 give Rayleigh quotients correct through
at least epsilon^6. Thus P<=15 suffices for references |0>,|1>,|2>,|3>:
three quartic insertions can add at most 12 particles. The additional
particle cap is exact for these perturbative coefficients, not a numerical
approximation. --validate runs an ordinary sixth-order recursion too at
small cutoffs (where the full P<=4 Lambda space is cheap).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix


def square_root_jets(nmodes: int, degree: int) -> np.ndarray:
    """Taylor coefficients, not derivatives, of sqrt(((1-eps)/2)_n/n!)."""
    out = np.zeros((degree+1, nmodes), dtype=float)
    v = np.zeros(degree+1); v[0] = 1.0
    for n in range(nmodes):
        if n:
            old = v.copy()
            v = (n-.5)/n * old
            v[1:] -= old[:-1]/(2*n)
        u = np.zeros(degree+1); u[0] = math.sqrt(v[0])
        for k in range(1, degree+1):
            u[k] = (v[k] - np.dot(u[1:k], u[k-1:0:-1]))/(2*u[0])
        out[:,n] = u
    return out


class FockSpace:
    def __init__(self, cutoff: int, pmax: int = 15, degree: int = 5):
        if cutoff < 2 or pmax < 3:
            raise ValueError('Need cutoff >=2 and pmax >=3.')
        self.cutoff, self.pmax = cutoff, pmax
        self.nmodes = cutoff
        self.bits = max(4, pmax.bit_length())
        mask = (1 << self.bits)-1
        codes, ps, ns = [], [], []
        shifts = [1 << (self.bits*n) for n in range(self.nmodes)]
        def visit(code, p, nlevel, start):
            codes.append(code); ps.append(p); ns.append(nlevel)
            if p == pmax:
                return
            upper = min(self.nmodes-1, (4*cutoff-p-4*nlevel-1)//4)
            for n in range(start, upper+1):
                visit(code+shifts[n], p+1, nlevel+n, n)
        visit(0,0,0,0)
        self.dim = len(codes)
        idx = {code:i for i,code in enumerate(codes)}
        self.refs = [idx[p] for p in range(4)]
        self.P = np.asarray(ps, dtype=np.int16)
        self.N = np.asarray(ns, dtype=np.int16)
        self.Efree = self.P*.25 + self.N
        self.F1 = -self.P*.25
        self.even = (self.N % 2 == 0)
        self.codes = codes if self.dim < 10000 else None
        self.index = idx if self.dim < 10000 else None
        # Build CSR directly column by column as a transpose (creation).
        indptr = np.zeros(self.dim+1, dtype=np.int64)
        from array import array
        parents, modes, occs = array('i'), array('B'), array('B')
        for i,c in enumerate(codes):
            rest=c
            while rest:
                low = (rest & -rest).bit_length()-1
                n = low//self.bits
                occ=(c >> (self.bits*n)) & mask
                parents.append(idx[c-shifts[n]])
                modes.append(n); occs.append(occ)
                rest &= ~(mask << (self.bits*n))
            indptr[i+1]=len(parents)
        del idx, codes, ps, ns
        parent=np.frombuffer(parents,dtype=np.int32).copy()
        mode=np.frombuffer(modes,dtype=np.uint8).copy()
        sqocc=np.sqrt(np.frombuffer(occs,dtype=np.uint8).astype(float))
        del parents,modes,occs
        u=square_root_jets(self.nmodes, degree)
        self.C=[]; self.B=[]
        for k in range(degree+1):
            # C row is parent+one particle, column parent.
            mat=csr_matrix((sqocc*u[k,mode],parent,indptr),shape=(self.dim,self.dim))
            self.C.append(mat)
            self.B.append(mat.T)  # Shares data; no duplicate ladder matrices.
        self.nnz=len(parent)

    def linear_series(self, x: np.ndarray, degree: int, creation=False) -> np.ndarray:
        mats=self.C if creation else self.B
        y=np.zeros((degree+1,self.dim))
        for k in range(degree+1):
            for j in range(min(k,len(mats)-1)+1):
                if k-j < len(x):
                    y[k] += mats[j] @ x[k-j]
        return y

    def vertices(self, psi: np.ndarray, degree: int):
        """M(eps)psi and V(eps)psi, with correct final parity projection."""
        low=[np.zeros((degree+1,self.dim))]
        low[0][:min(len(psi),degree+1)]=psi[:degree+1]
        for _ in range(4):
            low.append(self.linear_series(low[-1],degree))
        m=low[2].copy()
        t=self.linear_series(low[1],degree,True); m+=2*t
        t=self.linear_series(low[0],degree,True)
        m+=self.linear_series(t,degree,True)
        v=np.zeros_like(m)
        for j in range(5):
            term=low[4-j]
            for _ in range(j):
                term=self.linear_series(term,degree,True)
            v+=math.comb(4,j)/12*term
        m[:,~self.even]=0; v[:,~self.even]=0
        return m,v


def divide_series(a,b,degree):
    out=np.zeros(degree+1)
    if b[0] == 0: raise ZeroDivisionError('zero constant in series divisor')
    for k in range(degree+1):
        out[k]=((a[k] if k<len(a) else 0.)-
                sum(b[j]*out[k-j] for j in range(1,min(k,len(b)-1)+1)))/b[0]
    return out


def inner_series(x,y,degree,diag=None):
    out=np.zeros(degree+1)
    for i in range(min(len(x),degree+1)):
        for j in range(min(len(y),degree-i+1)):
            out[i+j]+=np.dot(x[i],y[j] if diag is None else diag*y[j])
    return out


def initial_wavefunctions(space: FockSpace, order=3):
    psi=[np.zeros((order+1,space.dim)) for _ in range(4)]
    E=np.zeros((4,order+1)); r=np.zeros(order+1); g=np.zeros(order+1)
    for p in range(4):
        psi[p][0,space.refs[p]]=1
        E[p,0]=p/4
    vref=[]; mref=[]
    for k in range(1,order+1):
        rhs=[]; raw=[]
        for p in range(4):
            m,v=space.vertices(psi[p][:k],k-1)
            if k==1:
                mref.append(m[0].copy()); vref.append(v[0].copy())
            t=space.F1*psi[p][k-1]
            for j in range(1,k):
                t+=r[j]*m[k-j]+g[j]*v[k-j]
            rhs.append(t); raw.append(t[space.refs[p]])
        r[k]=((-.25 if k==1 else 0.)-(raw[1]-raw[0]))/2
        g[k]=(( .25 if k==1 else 0.)-(raw[3]-raw[0])-6*r[k])/3
        for p in range(4):
            t=rhs[p]+r[k]*mref[p]+g[k]*vref[p]
            E[p,k]=t[space.refs[p]]
            for j in range(1,k+1):
                t-=E[p,j]*psi[p][k-j]
            den=p/4-space.Efree
            sel=space.even & (space.P%2==p%2) & (np.abs(den)>1e-12)
            psi[p][k,sel]=t[sel]/den[sel]
    return psi,E,r,g


def quotient_components(space,psi,degree=6):
    norm=inner_series(psi,psi,degree)
    f=inner_series(psi,psi,degree,space.Efree)
    f[1:]+=inner_series(psi,psi,degree-1,space.F1)
    # Both vertices are needed only through degree-1 since r(0)=g(0)=0.
    q=degree-1
    low=[np.zeros((q+1,space.dim))]
    low[0][:min(q+1,len(psi))]=psi[:q+1]
    for _ in range(4):
        low.append(space.linear_series(low[-1],q))
    m=2*inner_series(low[0],low[2],q)+2*inner_series(low[1],low[1],q)
    v=(inner_series(low[0],low[4],q)/6+
       (2/3)*inner_series(low[1],low[3],q)+
       .5*inner_series(low[2],low[2],q))
    return divide_series(f,norm,degree),divide_series(m,norm,degree),divide_series(v,norm,degree)


def compute(cutoff: int, validate=False):
    start=time.time()
    space=FockSpace(cutoff)
    psi,E3,r3,g3=initial_wavefunctions(space)
    F,M,V=(np.zeros((4,7)) for _ in range(3))
    for p in range(4):
        F[p],M[p],V[p]=quotient_components(space,psi[p])
    r=np.zeros(7);g=np.zeros(7)
    E=F.copy()
    for k in range(1,7):
        for p in range(4):
            E[p,k]+=sum(r[j]*M[p,k-j]+g[j]*V[p,k-j] for j in range(1,k))
        r[k]=((-.25 if k==1 else 0.)-(E[1,k]-E[0,k]))/2
        g[k]=(( .25 if k==1 else 0.)-(E[3,k]-E[0,k])-6*r[k])/3
        E[:,k]+=r[k]*M[:,0]+g[k]*V[:,0]
    C=E[2]-E[0]
    err_low=max(np.max(np.abs(r[:4]-r3)),np.max(np.abs(g[:4]-g3)),
                np.max(np.abs(E[:,:4]-E3)))
    target1=np.zeros(7);target1[:2]=[.25,-.25]
    target3=np.zeros(7);target3[:2]=[.75,.25]
    result={'cutoff':cutoff,'basis_dimension_including_auxiliary_parities':space.dim,
            'particle_cap':15,'ladder_nnz':space.nnz,'C':C.tolist(),
            'r':r.tolist(),'g':g.tolist(),
            'low_order_quotient_recursion_max_residual':float(err_low),
            'tuning_max_residual':float(max(np.max(np.abs(E[1]-E[0]-target1)),
                                            np.max(np.abs(E[3]-E[0]-target3)))),
            'seconds':time.time()-start,
            'scope':'Finite-cutoff coefficients of the supplied two-coupling Hamiltonian; not extrapolated physical coefficients.'}
    if validate:
        if cutoff>8:
            raise ValueError('Full-recursion validation is restricted to cutoff<=8.')
        full=FockSpace(cutoff,pmax=min(27,4*cutoff))
        psi6,E6,r6,g6=initial_wavefunctions(full,order=6)
        result['full_sixth_order_recursion_max_residual']=float(max(
            np.max(np.abs(C-(E6[2]-E6[0]))),
            np.max(np.abs(r-r6)),np.max(np.abs(g-g6))))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cutoffs',nargs='+',type=int,default=[4,8,12,16])
    parser.add_argument('--output',type=Path,default=Path('hamiltonian_cutoff_results.json'))
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    results=[]
    for cutoff in args.cutoffs:
        res=compute(cutoff,args.validate)
        results.append(res)
        print(json.dumps(res),flush=True)
        args.output.write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':
    main()
