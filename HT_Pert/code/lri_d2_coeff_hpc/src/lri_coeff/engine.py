"""Optimized 2D Taylor engine. Algebraic conventions inherited unchanged."""
from dataclasses import dataclass
import time
import numpy as np
from .basis import Graph,plan
from .operators import Operators
from .kernels import vector_moments
LD=np.longdouble
def real_sum(x):return float(np.sum(x,dtype=LD))
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
    def __init__(self,L,degree=8,scheme='consistent',batch=1,reflection=True,full_order=False,pmax=None,max_states=3000000,envelope=True,max_bytes=3*1024**3,backend="native",graph=None):
        if scheme not in ('raw','consistent','literal'):raise ValueError(scheme)
        if not reflection or not envelope:raise ValueError('Use the preserved reference engine for symmetry-ablation runs.')
        if batch!=1:raise ValueError('This engine streams one vacuum channel at a time; batch must be one.')
        if backend not in ('native','numba'):raise ValueError('Unknown backend')
        if np.finfo(np.longdouble).nmant<63:raise RuntimeError('Extended longdouble scalar accumulation required; no silent float64 fallback.')
        self.plan=plan(L,degree,pmax)
        if full_order:
            added_wave=self.plan['wave_bytes_estimate']*(degree-degree//2)/(degree//2+1)
            added_scratch=self.plan['auxiliary_states']*8*max(0,5*degree-max(3*degree,5*(degree//2)))
            self.plan['recommended_memory_bytes']+=int(1.35*(added_wave+added_scratch))
        if self.plan['recommended_memory_bytes']>max_bytes:raise MemoryError(f"Conservative memory plan {self.plan['recommended_memory_bytes']/2**30:.3f} GiB exceeds requested budget {max_bytes/2**30:.3f} GiB; do not reduce physics support to fit.")
        self.L=L;self.d=degree;self.h=degree if full_order else degree//2;self.scheme=scheme;self.batch=batch
        self.s=Graph.build(L,degree,pmax,max_states,max_bytes) if graph is None else graph;s=self.s
        if (s.L,s.degree,s.pmax)!=(L,degree,self.plan['pmax']):raise ValueError('Graph/model configuration mismatch')
        self.ops=Operators(s,backend=backend);self.stats={};self.stage='lower';self.completed_order=0;self.moments_done=0;self.upper_done=self.h;self.progress=None
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
        # The top vacuum is exactly the p=0 primary in raw/consistent models.
        # Literal mode has distinct vacuum and primary Hamiltonians and is NOT aliased.
        self.alias={self.nv:self.nv-1} if scheme!='literal' else {}
        for dst,src in self.alias.items():self.channels[dst].psi=self.channels[src].psi
        self.r=np.zeros(degree+1);self.g=np.zeros(degree+1)
        self.E=np.zeros((degree+1,len(self.channels)));self.E[0]=[c.p/2 for c in self.channels]
        self.channel_index={id(c):a for a,c in enumerate(self.channels)}

    def D(self,c,k):
        a=self.channel_index[id(c)]
        if self.scheme=='raw' or (self.scheme=='literal' and a<self.nv):return np.zeros(len(c.ids))
        return self.E[k,c.cutoff//2]-self.E[k,c.lower]

    def tune(self,k,bare):
        n=self.nv;self.r[k]=((-.25 if k==1 else 0)-bare[n+1]+bare[n])/2
        self.g[k]=((.25 if k==1 else 0)-bare[n+3]+bare[n]-6*self.r[k])/3

    def lower(self,verbose=False):
        s=self.s
        if self.completed_order>=self.h:return
        # Cache complete degree-zero reference images; high-order coefficients
        # are NOT cached at obsolete r,g or obsolete vacuum energies.
        seeds={}
        n=s.n
        for p in range(4):
            x=np.zeros((n,1));x[s.refs[p],0]=1
            m,v=self.ops.vertices(x,0,n)
            ids=np.flatnonzero(s.scalar&(s.P%2==p%2))
            seeds[p]=(ids,m[ids,0],v[ids,0])
        self.seed=[]
        for c in self.channels:
            ids,m,v=seeds[c.p];loc=np.searchsorted(ids,c.ids)
            self.seed.append((m[loc],v[loc]))
        del seeds,x,m,v
        for k in range(self.completed_order+1,self.h+1):
            rhsall=[]
            for ci,c in enumerate(self.channels):
                if ci in self.alias:
                    rhsall.append(rhsall[self.alias[ci]].copy());continue
                n=s.prefix_size(c.cutoff)
                if k>1:
                    x=np.zeros((n,k));x[c.ids]=c.psi[:k].T
                    M,V=self.ops.vertices(x,k-1,n)
                rhs=-s.P[c.ids]/4*c.psi[k-1]
                for j in range(1,k):rhs+=self.r[j]*M[c.ids,k-j]+self.g[j]*V[c.ids,k-j]
                for j in range(2,k):rhs+=self.D(c,j)*c.psi[k-j]
                rhsall.append(rhs)
                if k>1:del x,M,V
            bare=np.array([rhs[c.refpos] for rhs,c in zip(rhsall,self.channels)]);self.E[k,:self.nv]=bare[:self.nv]
            for a,c in enumerate(self.channels):
                if a>=self.nv:rhsall[a]+=self.D(c,k)*c.psi[0]
            bare=np.array([rhs[c.refpos] for rhs,c in zip(rhsall,self.channels)]);self.tune(k,bare)
            for a,c in enumerate(self.channels):
                if a in self.alias:
                    self.E[k,a]=self.E[k,self.alias[a]];continue
                m,v=self.seed[a];rhs=rhsall[a];rhs+=self.r[k]*m+self.g[k]*v
                self.E[k,a]=rhs[c.refpos]
                for j in range(1,k+1):rhs-=self.E[j,a]*c.psi[k-j]
                c.psi[k]=rhs*c.inv
            self.completed_order=k
            if verbose:print('wave order',k,'L',self.L,self.scheme,flush=True)
            if self.progress:self.progress(self,'wave',k)

    def moments(self):
        s=self.s
        for i in range(self.moments_done,len(self.channels)):
            c=self.channels[i]
            if i in self.alias:
                src=self.channels[self.alias[i]]
                c.mm,c.mv,c.norms,c.me,c.mf=src.mm,src.mv,src.norms,src.me,src.mf
            else:
                n=s.prefix_size(c.cutoff)
                c.mm,c.mv=self.ops.moments(c.psi,c.ids,n,self.d-1)
                c.norms,c.me,c.mf=vector_moments(c.psi,s.E[c.ids]-.5*c.p,s.P[c.ids],self.d)
            self.moments_done=i+1
            if self.progress:self.progress(self,'moments',i+1)

    def upper(self,verbose):
        d=self.d;h=self.h
        for k in range(self.upper_done+1,d+1):
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
            self.upper_done=k
            if verbose:print('quotient order',k,'L',self.L,self.scheme,flush=True)
            if self.progress:self.progress(self,'quotient',k)

    def solve(self,verbose=True):
        t=time.perf_counter();self.lower(verbose);self.stats['lower']=time.perf_counter()-t
        if self.h<self.d:
            t=time.perf_counter();self.moments();self.stats['moments']=time.perf_counter()-t
            t=time.perf_counter();self.upper(verbose);self.stats['upper']=time.perf_counter()-t
        E=self.E[:,self.nv:].T;C=E[2]-E[0]
        res=max(np.max(abs(E[1]-E[0]-np.r_[.5,-.25,np.zeros(self.d-1)])),np.max(abs(E[3]-E[0]-np.r_[1.5,.25,np.zeros(self.d-1)])))
        if res>1e-7 or not all(np.all(np.isfinite(v)) for v in (C,self.r,self.g,self.E)):raise ArithmeticError(('primary/finite gate',res))
        return dict(timings=self.stats,planning=self.plan,backend=self.ops.backend,graph_bytes=self.s.nbytes,dimension=2,variable='epsilon=2s-2=2-4Delta_sigma',cutoff=self.L,cutoff_type='total positive-mode level N<=L',degree=self.d,scheme=self.scheme,C=C.tolist(),r=self.r.tolist(),g=self.g.tolist(),energies=E.tolist(),vacuum_coefficients=self.E[:,:self.nv].T.tolist(),auxiliary_states=self.s.n,auxiliary_bath_states=self.s.bath_size,scalar_reference_dimensions=[len(c.ids) for c in self.channels[self.nv:]],reflection_even_reduction=True,exact_angular_envelope=True,particle_cap=self.s.pmax,nonzero_particle_cap=self.s.qmax,wave_order=self.h,stored_wavefunction_entries=sum(c.psi.size for c in self.channels),ladder_edges=self.s.nnz,tuning_residual=float(res),scope='Direct finite-cutoff thermal Taylor coefficients, no thermal tuning, no epsilon fit. Not continuum estimates.')

