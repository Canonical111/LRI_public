"""Direct 2D phi4 thermal coefficients: exact Taylor algebra, scalar symmetries.

Parent: uploaded circle modes and total bath level N<=L. Local Gaussian Fock
support is perturbatively sufficient rather than a trained finite local basis.
Only spin/shadow gaps tune r,g. All subcutoff vacua share the outer couplings.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from array import array
import argparse, gc, hashlib, json, math, os, resource, sys, time
import numpy as np
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'upstream/lri_2d_hpc_optimized/code'))
from ht2d.basis import CircleBathBasis
LD=np.longdouble

def real_sum(x):return float(np.sum(x,dtype=LD))

class CircleSpace:
    def __init__(self,L:int,degree:int,reflection:bool=True,pmax:int|None=None,max_states:int=1800000,envelope:bool=True):
        if L<0 or L%2 or not 2<=degree<=8:raise ValueError('even L>=0, degree 2..8 required')
        self.L=L;self.degree=degree;self.pmax=3+4*(degree//2) if pmax is None else pmax
        if self.pmax<3+4*(degree//2):raise ValueError('Particle cap is below the proven closed-path support.')
        self.qmax=4*(degree//2);self.reflection=reflection;self.envelope=envelope
        b=CircleBathBasis.build(L,max_states=max_states,max_bytes=1100*1024**2)
        nB=len(b.N);canon=np.minimum(np.arange(nB),b.mirror) if reflection else np.arange(nB)
        extent=b.N+np.abs(b.J) if envelope else b.N
        valid=(canon==np.arange(nB))&(b.P<=min(self.pmax,self.qmax))&(extent<=L)
        reps=np.flatnonzero(valid);reps=reps[np.argsort(extent[reps],kind='stable')]
        counts=self.pmax-b.P[reps]+1;self.n=int(counts.sum())
        if self.n>max_states:raise MemoryError(f'Exact auxiliary dimension {self.n} exceeds guard {max_states}; no support/precision reduction allowed.')
        start=np.full(nB,-1,np.int64);start[reps]=np.r_[0,np.cumsum(counts)[:-1]]
        rb=np.repeat(reps,counts);z=np.arange(self.n)-np.repeat(start[reps],counts)
        self.extent=extent[rb].astype(np.int32)
        self.N=b.N[rb].astype(np.int32);self.P=(b.P[rb]+z).astype(np.int16)
        self.Jabs=np.abs(b.J[rb]);self.E=self.N+.5*self.P;self.scalar=self.Jabs==0
        self.refs=np.arange(start[0],start[0]+4,dtype=int)
        self.bath_full=nB;self.bath_reflection_orbits=len(reps)
        self.u=self.mode_jets(b.labels,L,degree)
        ptr=np.zeros(self.n+1,np.int64);cols=array('i');modes=array('H');amps=array('d')
        for i,(bath,zero) in enumerate(zip(rb,z)):
            if zero:
                cols.append(i-1);modes.append(0);amps.append(math.sqrt(zero))
            di=2 if reflection and b.mirror[bath]!=bath else 1
            for edge in range(b.indptr[bath],b.indptr[bath+1]):
                child=canon[b.parent[edge]];dj=2 if reflection and b.mirror[child]!=child else 1
                dest=int(start[child]+zero)
                if start[child]<0 or dest>=self.n:raise AssertionError('Missing annihilation support')
                cols.append(dest);modes.append(int(b.mode[edge])+1);amps.append(float(b.sqocc[edge])*math.sqrt(di/dj))
            ptr[i+1]=len(cols)
        cols=np.frombuffer(cols,np.int32);modes=np.frombuffer(modes,np.uint16);amps=np.frombuffer(amps,float)
        self.nnz=len(cols)
        self.C=[]
        for d in range(degree):
            c=csr_matrix((amps*self.u[d,modes],cols.copy(),ptr.copy()),shape=(self.n,self.n));c.sum_duplicates();c.sort_indices();c.eliminate_zeros();self.C.append(c)
        del b,rb,z,canon,start,counts,cols,modes,amps;gc.collect()

    @staticmethod
    def mode_jets(labels,L,degree):
        v=np.zeros((degree,L+1));v[0,0]=1
        for n in range(1,L+1):
            v[:,n]=v[:,n-1]*(n-.5)/n;v[1:,n]-=v[:-1,n-1]/(4*n)
        u=np.zeros_like(v);u[0]=np.sqrt(v[0])
        for d in range(1,degree):u[d]=(v[d]-sum(u[j]*u[d-j] for j in range(1,d)))/(2*u[0])
        out=np.zeros((degree,len(labels)+1));out[0,0]=1
        for k,(a,b) in enumerate(labels,1):out[:,k]=np.convolve(u[:,a],u[:,b])[:degree]
        return out

    def prefix(self,n):
        # The exact auxiliary envelope is annihilation-closed; its scalar endpoints are N<=ell.
        c=[csr_matrix((a.data[:a.indptr[n]],a.indices[:a.indptr[n]],a.indptr[:n+1]),shape=(n,n)) for a in self.C]
        return c,[a.T for a in c]

    def vertices(self,x,d,n,mats):
        C,B=mats
        def lin(xx,creation=False):
            y=np.zeros((d+1,n,xx.shape[2]));ls=C if creation else B
            for k in range(d+1):
                for j in range(min(k,len(ls)-1)+1):
                    if k-j<len(xx):y[k]+=ls[j]@xx[k-j]
            return y
        low=x;v=x.copy();m=x.copy()
        for j in range(1,5):
            low=lin(low);v=lin(v,True)+math.comb(4,j)*low
            if j<=2:m=lin(m,True)+math.comb(2,j)*low
        # Angular projection is AFTER complete vertices. Reflection reduction was exact.
        v/=12;m[:,~self.scalar[:n]]=0;v[:,~self.scalar[:n]]=0
        return m,v

@dataclass
class Channel:
    cutoff:int
    p:int
    ids:np.ndarray
    refpos:int
    psi:np.ndarray
    inv:np.ndarray
    lower:np.ndarray
    mm:np.ndarray|None=None
    mv:np.ndarray|None=None
    norms:np.ndarray|None=None
    mf:np.ndarray|None=None
    me:np.ndarray|None=None

class Engine:
    def __init__(self,L,degree=8,scheme='consistent',batch=1,reflection=True,full_order=False,pmax=None,max_states=1800000,envelope=True):
        if scheme not in ('raw','consistent','literal'):raise ValueError(scheme)
        self.L=L;self.d=degree;self.h=degree if full_order else degree//2;self.scheme=scheme;self.batch=batch
        self.s=CircleSpace(L,degree,reflection,pmax,max_states,envelope);s=self.s
        grids=list(range(0,L+1,2)) if scheme!='raw' else [L];self.nv=len(grids)
        self.channels=[]
        for ell,p in [(ell,0) for ell in grids]+[(L,p) for p in range(4)]:
            ids=np.flatnonzero((s.N<=ell)&s.scalar&(s.P%2==p%2));pos=int(np.searchsorted(ids,s.refs[p]));assert ids[pos]==s.refs[p]
            den=.5*p-s.E[ids]
            if np.count_nonzero(den==0)!=1:raise ValueError('Degenerate reference: requires block treatment')
            psi=np.zeros((self.h+1,len(ids)));psi[0,pos]=1
            inv=np.divide(1,den,out=np.zeros(len(den)),where=den!=0)
            lower=(ell-s.N[ids])//2
            self.channels.append(Channel(ell,p,ids,pos,psi,inv,lower))
        self.r=np.zeros(degree+1);self.g=np.zeros(degree+1)
        self.E=np.zeros((degree+1,len(self.channels)));self.E[0]=[c.p/2 for c in self.channels]
        self.channel_index={id(c):a for a,c in enumerate(self.channels)}

    def batches(self):
        bs=min(self.batch,max(1,450000//self.s.n))
        for a in range(0,len(self.channels),bs):
            ch=self.channels[a:a+bs];n=int(np.searchsorted(self.s.extent,max(c.cutoff for c in ch),side='right'))
            yield a,ch,n,self.s.prefix(n)

    def D(self,c,k):
        a=self.channel_index[id(c)]
        if self.scheme=='raw' or (self.scheme=='literal' and a<self.nv):return np.zeros(len(c.ids))
        return self.E[k,c.cutoff//2]-self.E[k,c.lower]

    def tune(self,k,bare):
        n=self.nv;self.r[k]=((-.25 if k==1 else 0)-bare[n+1]+bare[n])/2
        self.g[k]=((.25 if k==1 else 0)-bare[n+3]+bare[n]-6*self.r[k])/3

    def lower(self,verbose):
        s=self.s
        for k in range(1,self.h+1):
            rhsall=[]
            for a,ch,n,mats in self.batches():
                x=np.zeros((k,n,len(ch)))
                for b,c in enumerate(ch):x[:,c.ids,b]=c.psi[:k]
                M,V=s.vertices(x,k-1,n,mats)
                for b,c in enumerate(ch):
                    rhs=-s.P[c.ids]/4*c.psi[k-1]
                    for j in range(1,k):rhs+=self.r[j]*M[k-j,c.ids,b]+self.g[j]*V[k-j,c.ids,b]
                    for j in range(2,k):rhs+=self.D(c,j)*c.psi[k-j]
                    rhsall.append(rhs)
            bare=np.array([rhs[c.refpos] for rhs,c in zip(rhsall,self.channels)]);self.E[k,:self.nv]=bare[:self.nv]
            # Dk|reference>=0 since all references have bath level zero.
            for a,c in enumerate(self.channels):
                if a>=self.nv:rhsall[a]+=self.D(c,k)*c.psi[0]
            bare=np.array([rhs[c.refpos] for rhs,c in zip(rhsall,self.channels)]);self.tune(k,bare)
            for a,ch,n,mats in self.batches():
                z=np.zeros((1,n,len(ch)))
                for b,c in enumerate(ch):z[0,c.ids[c.refpos],b]=1
                M,V=s.vertices(z,0,n,mats)
                for b,c in enumerate(ch):
                    rhs=rhsall[a+b];rhs+=self.r[k]*M[0,c.ids,b]+self.g[k]*V[0,c.ids,b]
                    self.E[k,a+b]=rhs[c.refpos]
                    for j in range(1,k+1):rhs-=self.E[j,a+b]*c.psi[k-j]
                    c.psi[k]=rhs*c.inv
            if verbose:print('wave order',k,'L',self.L,self.scheme,flush=True)

    def moments(self):
        s=self.s;d=self.d;h=self.h
        for a,ch,n,mats in self.batches():
            x=np.zeros((h+1,n,len(ch)))
            for b,c in enumerate(ch):x[:,c.ids,b]=c.psi
            M,V=s.vertices(x,d-1,n,mats)
            for b,c in enumerate(ch):
                c.mm=np.zeros(d);c.mv=np.zeros(d);c.mf=np.zeros(d);c.me=np.zeros(d+1);c.norms=np.zeros(d+1)
                for k in range(d):
                    for j in range(min(k,h)+1):
                        c.mm[k]+=real_sum(c.psi[j]*M[k-j,c.ids,b]);c.mv[k]+=real_sum(c.psi[j]*V[k-j,c.ids,b])
                for i in range(h+1):
                    for j in range(h+1):
                        k=i+j
                        if k>d:continue
                        pr=c.psi[i]*c.psi[j];c.norms[k]+=real_sum(pr);c.me[k]+=real_sum(pr*(s.E[c.ids]-.5*c.p))
                        if k<d:c.mf[k]+=real_sum(pr*(-s.P[c.ids]/4))

    def upper(self,verbose):
        d=self.d;h=self.h
        for k in range(h+1,d+1):
            bare=[]
            for a,c in enumerate(self.channels):
                val=c.me[k]+c.mf[k-1]
                for j in range(1,k):val+=self.r[j]*c.mm[k-j]+self.g[j]*c.mv[k-j]-self.E[j,a]*c.norms[k-j]
                for j in range(2,k):
                    order=k-j;dj=self.D(c,j)
                    for i in range(max(0,order-h),min(order,h)+1):val+=real_sum(dj*c.psi[i]*c.psi[order-i])
                bare.append(val)
            bare=np.array(bare);self.E[k,:self.nv]=bare[:self.nv]
            for a,c in enumerate(self.channels):
                if a>=self.nv:bare[a]+=self.D(c,k)[c.refpos]
            self.tune(k,bare)
            for a,c in enumerate(self.channels):self.E[k,a]=bare[a]+2*c.p*self.r[k]+c.p*(c.p-1)*self.g[k]/2
            if verbose:print('quotient order',k,'L',self.L,self.scheme,flush=True)

    def solve(self,verbose=True):
        self.lower(verbose)
        if self.h<self.d:self.moments();self.upper(verbose)
        E=self.E[:,self.nv:].T;C=E[2]-E[0]
        res=max(np.max(abs(E[1]-E[0]-np.r_[.5,-.25,np.zeros(self.d-1)])),np.max(abs(E[3]-E[0]-np.r_[1.5,.25,np.zeros(self.d-1)])))
        if res>1e-7 or not np.all(np.isfinite(C)):raise ArithmeticError(('primary/finite gate',res))
        return dict(dimension=2,variable='epsilon=2s-2=2-4Delta_sigma',cutoff=self.L,cutoff_type='total positive-mode level N<=L',degree=self.d,scheme=self.scheme,C=C.tolist(),r=self.r.tolist(),g=self.g.tolist(),energies=E.tolist(),vacuum_coefficients=self.E[:,:self.nv].T.tolist(),auxiliary_states=self.s.n,auxiliary_bath_states=self.s.bath_full,scalar_reference_dimensions=[len(c.ids) for c in self.channels[self.nv:]],reflection_even_reduction=self.s.reflection,exact_angular_envelope=self.s.envelope,particle_cap=self.s.pmax,nonzero_particle_cap=self.s.qmax,wave_order=self.h,stored_wavefunction_entries=sum(c.psi.size for c in self.channels),ladder_edges=self.s.nnz,tuning_residual=float(res),scope='Direct finite-cutoff thermal Taylor coefficients, no thermal tuning, no epsilon fit. Not continuum estimates.')

def run(L,degree=8,scheme='consistent',**kw):
    t=time.perf_counter();e=Engine(L,degree,scheme,**kw);o=e.solve();o.update(seconds=time.perf_counter()-t,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);return o

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cutoffs',type=int,nargs='+',default=[2,4,6,8]);p.add_argument('--degree',type=int,default=8);p.add_argument('--scheme',choices=['raw','consistent','literal'],default='consistent');p.add_argument('--batch',type=int,default=1);p.add_argument('--full-order',action='store_true');p.add_argument('--no-reflection',action='store_true');p.add_argument('--no-envelope',action='store_true');p.add_argument('--pmax',type=int);p.add_argument('--max-states',type=int,default=1800000);p.add_argument('--out',type=Path,default=ROOT/'results/coefficients');a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    for L in a.cutoffs:
        f=a.out/f'{a.scheme}_L{L}_d{a.degree}.json'
        if f.exists():print('exists',f,flush=True);continue
        gc.collect()
        out=run(L,a.degree,a.scheme,batch=a.batch,reflection=not a.no_reflection,full_order=a.full_order,pmax=a.pmax,max_states=a.max_states,envelope=not a.no_envelope)
        tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');os.replace(tmp,f)
        print(json.dumps({k:out[k] for k in ['cutoff','scheme','C','auxiliary_states','seconds']},indent=2),flush=True)
if __name__=='__main__':main()
