#!/usr/bin/env python3
"""Fifth-order phi^6 gap in the user-supplied two-coupling oscillator Hamiltonian.

Computes RAW and isolated-vacuum-subtracted prescriptions. Neither is claimed to
be a completely matched dilatation operator. Tuning uses only the phi and phi^3
gaps, never physical C4,... or phi6 target values. Requires NumPy/SciPy and the
bundled check_lri_hamiltonian.py. Frozen even energy cutoff N+P/4<=Lambda.

A second-order trial state determines energy through eps^5. The P<=14 and
nonzero-mode-particle count<=8 caps are exact for this order. Optional --validate
compares with full fifth-order Rayleigh-Schrodinger recursion at small cutoffs.
"""
from __future__ import annotations
import argparse,json,math,time,gc
from pathlib import Path
from array import array
import numpy as np
from scipy.sparse import csr_matrix
from check_lri_hamiltonian import FockSpace,square_root_jets,quotient_components,inner_series,divide_series

class GapSpace(FockSpace):
    def __init__(self,cutoff:int,degree:int=4,pmax:int=14,qmax:int=8):
        if cutoff<2 or cutoff%2: raise ValueError('Cutoff must be even and >=2.')
        self.cutoff=cutoff;self.pmax=pmax;self.nmodes=cutoff
        self.bits=max(4,pmax.bit_length());mask=(1<<self.bits)-1
        codes=[];ps=[];ns=[];shifts=[1<<(self.bits*n) for n in range(cutoff)]
        def visit(code,p,N,start,q):
            codes.append(code);ps.append(p);ns.append(N)
            if p==pmax:return
            upper=min(cutoff-1,(4*cutoff-p-4*N-1)//4)
            if q==qmax:upper=min(upper,0)
            for n in range(start,upper+1):visit(code+shifts[n],p+1,N+n,n,q+(n!=0))
        visit(0,0,0,0,0)
        self.dim=len(codes);idx={c:i for i,c in enumerate(codes)}
        self.refp={p:idx[p] for p in (0,1,2,3,6)}
        self.refs=[idx[p] for p in range(4)]
        self.P=np.asarray(ps,dtype=np.int16);self.N=np.asarray(ns,dtype=np.int16)
        self.Efree=self.P*.25+self.N;self.F1=-self.P*.25;self.even=self.N%2==0
        indptr=np.zeros(self.dim+1,dtype=np.int64)
        parents=array('i');modes=array('H');occs=array('B')
        for i,c in enumerate(codes):
            rest=c
            while rest:
                n=((rest&-rest).bit_length()-1)//self.bits
                occ=(c>>(self.bits*n))&mask
                parents.append(idx[c-shifts[n]]);modes.append(n);occs.append(occ)
                rest &= ~(mask<<(self.bits*n))
            indptr[i+1]=len(parents)
        del idx,codes,ps,ns
        parent=np.frombuffer(parents,dtype=np.int32).copy()
        mode=np.frombuffer(modes,dtype=np.uint16).copy()
        sqocc=np.sqrt(np.frombuffer(occs,dtype=np.uint8).astype(float))
        del parents,modes,occs
        self.C=[];self.B=[];u=square_root_jets(cutoff,degree)
        for k in range(degree+1):
            mat=csr_matrix((sqocc*u[k,mode],parent,indptr),shape=(self.dim,self.dim))
            self.C.append(mat);self.B.append(mat.T)
        self.nnz=len(parent)

def vacuum_diagonal_jets(space,degree=3):
    """Isolated g^2 D(eps) correction: restore missing spectator vacuum shells.
    D_i=-1/6 sum_{m even, m+1<=Lambda < m+1+E_i^0} (2-2eps)_m/[m!(m+1-eps)].
    Thresholds frozen at eps=0; includes each shell m once. Not full matching.
    """
    L=space.cutoff
    w=np.zeros(degree+1);w[0]=1.;sums=np.zeros((L+1,degree+1))
    running=np.zeros(degree+1)
    for m in range(L):
        if m:
            old=w.copy();w=(m+1.)/m*old;w[1:]-=2./m*old[:-1]
        if not m%2:
            den=np.array([(m+1.)**(-j-1) for j in range(degree+1)])
            running += np.convolve(w,den)[:degree+1]
        sums[m+1]=running
    upper=np.floor(L-1-space.Efree+1e-10).astype(int)+1
    upper=np.maximum(0,upper)
    return -(sums[L]-sums[upper]).T/6

def initial_all(space,order=2,corrected=False,D=None):
    refs=(0,1,2,3,6);s=len(refs)
    psi=[np.zeros((order+1,space.dim)) for _ in refs]
    E=np.zeros((s,order+1));r=np.zeros(order+1);g=np.zeros(order+1)
    for ip,p in enumerate(refs):psi[ip][0,space.refp[p]]=1;E[ip,0]=p/4
    mref=[];vref=[]
    for k in range(1,order+1):
        rhs=[];raw=[]
        gg=np.convolve(g,g)
        for ip,p in enumerate(refs):
            m,v=space.vertices(psi[ip][:k],k-1)
            if k==1:mref.append(m[0].copy());vref.append(v[0].copy())
            t=space.F1*psi[ip][k-1]
            for j in range(1,k):t+=r[j]*m[k-j]+g[j]*v[k-j]
            if corrected:
                for j in range(2,k+1):
                    for h in range(k-j+1):t+=gg[j]*D[h]*psi[ip][k-j-h]
            rhs.append(t);raw.append(t[space.refp[p]])
        r[k]=((-.25 if k==1 else 0.)-(raw[1]-raw[0]))/2
        g[k]=((.25 if k==1 else 0.)-(raw[3]-raw[0])-6*r[k])/3
        for ip,p in enumerate(refs):
            t=rhs[ip]+r[k]*mref[ip]+g[k]*vref[ip]
            E[ip,k]=t[space.refp[p]]
            for j in range(1,k+1):t-=E[ip,j]*psi[ip][k-j]
            den=p/4-space.Efree
            sel=space.even&(space.P%2==p%2)&(abs(den)>1e-12)
            # Same-energy states in the selected sector are unique for these refs.
            deg=space.even&(space.P%2==p%2)&(abs(den)<=1e-12)
            if deg.sum()!=1:raise RuntimeError('Unresolved degenerate reference.')
            psi[ip][k,sel]=t[sel]/den[sel]
    return psi,E,r,g

def d_quotient(psi,D,degree):
    norm=inner_series(psi,psi,degree)
    coeff=np.zeros(degree+1)
    for k in range(min(len(D),degree+1)):
        coeff[k:]+=inner_series(psi,psi,degree-k,diag=D[k])
    return divide_series(coeff,norm,degree)

def extract(F,M,V,K,corrected=False):
    d=F.shape[1]-1;r=np.zeros(d+1);g=np.zeros(d+1);E=F.copy()
    for k in range(1,d+1):
        gg=np.convolve(g,g)
        for p in range(len(F)):
            E[p,k]+=sum(r[j]*M[p,k-j]+g[j]*V[p,k-j] for j in range(1,k))
            if corrected:E[p,k]+=sum(gg[j]*K[p,k-j] for j in range(2,k+1))
        r[k]=((-.25 if k==1 else 0.)-(E[1,k]-E[0,k]))/2
        g[k]=(( .25 if k==1 else 0.)-(E[3,k]-E[0,k])-6*r[k])/3
        E[:,k]+=r[k]*M[:,0]+g[k]*V[:,0]
    return E,r,g

def compute(L,validate=False,degree=5):
    d=degree;order=(degree-1)//2
    t=time.perf_counter();space=GapSpace(L,degree=d-1,pmax=6+4*order,qmax=4*order);psi,E2,r2,g2=initial_all(space,order=order)
    F,M,V=(np.zeros((5,d+1)) for _ in range(3));K=np.zeros((5,d-1))
    D=vacuum_diagonal_jets(space,d-2)
    for ip in range(5):
        F[ip],M[ip],V[ip]=quotient_components(space,psi[ip],d)
        K[ip]=d_quotient(psi[ip],D,d-2)
    result=dict(cutoff=L,basis_dimension=space.dim,particle_cap=6+4*order,nonzero_particle_cap=4*order,degree=d)
    for prescription in ('raw','vacuum_subtracted'):
        corr=prescription!='raw';E,r,g=extract(F,M,V,K,corr)
        target1=np.zeros(d+1);target1[:2]=[.25,-.25]
        target3=np.zeros(d+1);target3[:2]=[.75,.25]
        rec=dict(D6=(E[4]-E[0]).tolist(),C=(E[2]-E[0]).tolist(),r=r.tolist(),g=g.tolist(),
                 tuning_residual=float(max(max(abs(E[1]-E[0]-target1)),max(abs(E[3]-E[0]-target3)))))
        if validate:
            full=GapSpace(L,degree=d-1,pmax=min(6+4*d,4*L),qmax=4*d)
            Dfull=vacuum_diagonal_jets(full,d-2)
            _,Ef,rf,gf=initial_all(full,order=d,corrected=corr,D=Dfull)
            rec['full_recursion_residual']=float(max(np.max(abs(E-Ef)),max(abs(r-rf)),max(abs(g-gf))))
            del full,Dfull;gc.collect()
        result[prescription]=rec
    m=L-2;vm=math.exp(math.lgamma(m+.5)-math.lgamma(.5)-math.lgamma(m+1))
    target=((48*m+104)*vm+m+91)/(54*(m+1))
    result['second_order_exact_identity_residual']=result['raw']['D6'][2]+45*result['raw']['C'][2]-target
    result['vacuum_shift_identity_residual']=result['vacuum_subtracted']['D6'][2]-result['raw']['D6'][2]+1/54
    result['seconds']=time.perf_counter()-t
    result['scope']=f'Finite-cutoff phi6 gap through epsilon^{d}. Vacuum subtraction is partial, not full matching.'
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cutoffs',type=int,nargs='+',default=[4,8,12,16,24,32])
    ap.add_argument('--degree',type=int,choices=[3,5],default=5);ap.add_argument('--validate',action='store_true');ap.add_argument('--output',type=Path,default=Path('phi6_runs.json'))
    a=ap.parse_args();rows=[]
    for L in a.cutoffs:
        row=compute(L,a.validate,a.degree);rows.append(row);print(json.dumps(row),flush=True)
        a.output.write_text(json.dumps(rows,indent=2)+'\n');gc.collect()
