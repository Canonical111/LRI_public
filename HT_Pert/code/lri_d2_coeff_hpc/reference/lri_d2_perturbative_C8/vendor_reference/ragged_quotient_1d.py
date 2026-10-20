"""Whole-coefficient frozen-cutoff Dconn recursion with exact half-order compression.
Uses Wigner stationarity, not a selected high-state graph approximation. The
Hamiltonian, cutoff phase, particle support and primary tuning are unchanged.
Thermal benchmarks are never inputs. Floating-point results are not tail bounds.
"""
from __future__ import annotations
from pathlib import Path
import sys, os, json, math, time, argparse, resource
from dataclasses import dataclass
import numpy as np
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1]

class Space:
    def __init__(self,L,degree,max_states=2300000):
        self.L=L;self.degree=degree;self.pmax=3+4*(degree//2);self.qmax=4*(degree//2)
        if not (L>=2 and L%2==0 and degree in range(2,9)):raise ValueError('even L>=2, degree 2..8 required')
        states=[]
        def visit(st,N,q,start):
            if len(states)>=max_states:raise MemoryError('State guard exceeded; no precision/support relaxation.')
            states.append(st)
            if len(st)==self.pmax:return
            for k in range(start,L):
                if 4*(N+k)+len(st)+1>4*L:break
                if q+(k>0)>self.qmax:continue
                visit(st+(k,),N+k,q+(k>0),k)
        visit((),0,0,0);states.sort(key=lambda x:4*sum(x)+len(x))
        self.n=len(states);self.N=np.array([sum(st) for st in states],dtype=np.int32)
        self.P=np.array([len(st) for st in states],dtype=np.int16);self.e4=4*self.N+self.P;self.E=self.e4/4.;self.even=(self.N%2==0)
        idx={st:j for j,st in enumerate(states)};self.refs=[idx[(0,)*p] for p in range(4)]
        self.v=np.zeros((degree,L));self.v[0,0]=1
        for k in range(1,L):
            self.v[:,k]=self.v[:,k-1]*(k-.5)/k
            self.v[1:,k]-=self.v[:-1,k-1]/(2*k)
        self.u=np.zeros_like(self.v);self.u[0]=np.sqrt(self.v[0])
        for j in range(1,degree):self.u[j]=(self.v[j]-sum(self.u[a]*self.u[j-a] for a in range(1,j)))/(2*self.u[0])
        from array import array
        col=array('i');mod=array('H');oc=array('B');ptr=np.zeros(self.n+1,np.int64)
        for j,st in enumerate(states):
            prev=-1
            for k in st:
                if k==prev:continue
                prev=k;l=list(st);l.remove(k);col.append(idx[tuple(l)]);mod.append(k);oc.append(st.count(k))
            ptr[j+1]=len(col)
        del idx,states,visit
        import gc
        gc.collect()
        col=np.frombuffer(col,dtype=np.int32);mod=np.frombuffer(mod,dtype=np.uint16);oc=np.sqrt(np.frombuffer(oc,dtype=np.uint8).astype(float))
        self.C=[csr_matrix((oc*self.u[j,mod],col,ptr),shape=(self.n,self.n)) for j in range(degree)]
        self.nnz=len(col)
    def prefix(self,n):
        # State-energy ordering means the principal block is exactly the smaller space.
        C=[csr_matrix((c.data[:c.indptr[n]],c.indices[:c.indptr[n]],c.indptr[:n+1]),shape=(n,n)) for c in self.C]
        return C,[c.T for c in C]
    def vertices(self,x,d,n,mats):
        C,B=mats
        def linear(x,create=False):
            ls=C if create else B;y=np.zeros((d+1,n,x.shape[2]))
            for k in range(d+1):
                for j in range(min(k,len(ls)-1)+1):
                    if k-j<len(x):y[k]+=ls[j]@x[k-j]
            return y
        # Horner recurrence consumes annihilation powers sequentially. Storing
        # all five powers would needlessly multiply the peak scratch storage.
        low=x;v=x.copy();m=x.copy()
        for j in range(1,5):
            low=linear(low)
            v=linear(v,True)+math.comb(4,j)*low
            if j<=2:m=linear(m,True)+math.comb(2,j)*low
        v/=12;m[:,~self.even[:n]]=0;v[:,~self.even[:n]]=0
        return m,v

@dataclass
class Channel:
    q:int
    p:int
    ids:np.ndarray
    refpos:int
    psi:np.ndarray
    inv:np.ndarray
    lower:np.ndarray
    moments_m:np.ndarray|None=None
    moments_v:np.ndarray|None=None
    moments_f:np.ndarray|None=None
    moments_e0:np.ndarray|None=None
    norms:np.ndarray|None=None

class Engine:
    def __init__(self,L,degree=8,scheme='dconn',batch=4):
        if scheme not in ['raw','dconn']:raise ValueError(scheme)
        self.L=L;self.degree=degree;self.half=degree//2;self.scheme=scheme;self.batch=batch;self.space=Space(L,degree)
        s=self.space;self.nv=2*L+1 if scheme=='dconn' else 1;self.channels=[]
        grids=list(range(2*L+1)) if scheme=='dconn' else [2*L]
        for q,p in [(q,0) for q in grids]+[(2*L,p) for p in range(4)]:
            ids=np.flatnonzero((s.e4<=2*q)&s.even&(s.P%2==p%2));pos=int(np.searchsorted(ids,s.refs[p]));assert ids[pos]==s.refs[p]
            psi=np.zeros((self.half+1,len(ids)));psi[0,pos]=1
            den=p/4-s.E[ids];inv=np.divide(1,den,out=np.zeros(len(ids)),where=den!=0)
            self.channels.append(Channel(q,p,ids,pos,psi,inv,np.maximum(0,(2*q-s.e4[ids])//2)))
        self.r=np.zeros(degree+1);self.g=np.zeros(degree+1);self.E=np.zeros((degree+1,len(self.channels)));self.E[0]=[c.p/4 for c in self.channels]
    def batch_iter(self):
        effective_batch=min(self.batch,max(1,700000//self.space.n))
        for a in range(0,len(self.channels),effective_batch):
            ch=self.channels[a:a+effective_batch];n=int(np.searchsorted(self.space.e4,2*max(c.q for c in ch),side='right'))
            yield a,ch,n,self.space.prefix(n)
    def D(self,c,k):
        if self.scheme=='raw':return np.zeros(len(c.ids))
        return self.E[k,c.q]-self.E[k,c.lower]
    def new_couplings(self,k,bare):
        n=self.nv
        self.r[k]=((-.25 if k==1 else 0)-bare[n+1]+bare[n])/2
        self.g[k]=((.25 if k==1 else 0)-bare[n+3]+bare[n]-6*self.r[k])/3
    def lower_orders(self):
        s=self.space
        for k in range(1,self.half+1):
            allrhs=[]
            for a,ch,n,mats in self.batch_iter():
                x=np.zeros((k,n,len(ch)))
                for b,c in enumerate(ch):x[:,c.ids,b]=c.psi[:k]
                M,V=s.vertices(x,k-1,n,mats)
                for b,c in enumerate(ch):
                    rhs=(-s.P[c.ids]/4)*c.psi[k-1]
                    for j in range(1,k):rhs+=self.r[j]*M[k-j,c.ids,b]+self.g[j]*V[k-j,c.ids,b]
                    for j in range(2,k):rhs+=self.D(c,j)*c.psi[k-j]
                    allrhs.append(rhs)
            bare=np.array([rhs[c.refpos] for rhs,c in zip(allrhs,self.channels)])
            self.E[k,:self.nv]=bare[:self.nv]
            for a,c in enumerate(self.channels):
                if a>=self.nv:allrhs[a]+=self.D(c,k)*c.psi[0]
            bare=np.array([rhs[c.refpos] for rhs,c in zip(allrhs,self.channels)])
            self.new_couplings(k,bare)
            # M0|p>, V0|p> need small sparse images, no stored full channel tensor.
            for a,ch,n,mats in self.batch_iter():
                z=np.zeros((1,n,len(ch)))
                for b,c in enumerate(ch):z[0,c.ids[c.refpos],b]=1
                M,V=s.vertices(z,0,n,mats)
                for b,c in enumerate(ch):
                    rhs=allrhs[a+b];rhs+=self.r[k]*M[0,c.ids,b]+self.g[k]*V[0,c.ids,b]
                    self.E[k,a+b]=rhs[c.refpos]
                    for j in range(1,k+1):rhs-=self.E[j,a+b]*c.psi[k-j]
                    c.psi[k]=rhs*c.inv
            print('wave order',k,'L',self.L,flush=True)
    def moments(self):
        d=self.degree;s=self.space;h=self.half
        for a,ch,n,mats in self.batch_iter():
            x=np.zeros((h+1,n,len(ch)))
            for b,c in enumerate(ch):x[:,c.ids,b]=c.psi
            M,V=s.vertices(x,d-1,n,mats)
            for b,c in enumerate(ch):
                c.moments_m=np.zeros(d);c.moments_v=np.zeros(d);c.norms=np.zeros(d+1);c.moments_f=np.zeros(d);c.moments_e0=np.zeros(d+1)
                for k in range(d):
                    for j in range(min(k,h)+1):
                        c.moments_m[k]+=np.dot(c.psi[j],M[k-j,c.ids,b]);c.moments_v[k]+=np.dot(c.psi[j],V[k-j,c.ids,b])
                for i in range(h+1):
                    for j in range(h+1):
                        k=i+j
                        if k>d:continue
                        prod=c.psi[i]*c.psi[j];c.norms[k]+=sum_long(prod)
                        c.moments_e0[k]+=sum_long(prod*(s.E[c.ids]-c.p/4))
                        if k<d:c.moments_f[k]+=sum_long(prod*(-s.P[c.ids]/4))
    def high_orders(self):
        d=self.degree;h=self.half
        for k in range(h+1,d+1):
            bare=[]
            for a,c in enumerate(self.channels):
                val=c.moments_e0[k]+c.moments_f[k-1]
                for j in range(1,k):val+=self.r[j]*c.moments_m[k-j]+self.g[j]*c.moments_v[k-j]-self.E[j,a]*c.norms[k-j]
                for j in range(2,k):
                    order=k-j;dj=self.D(c,j)
                    for l in range(max(0,order-h),min(order,h)+1):val+=sum_long(dj*c.psi[l]*c.psi[order-l])
                bare.append(val)
            bare=np.array(bare);self.E[k,:self.nv]=bare[:self.nv]
            for a,c in enumerate(self.channels):
                if a>=self.nv:bare[a]+=self.D(c,k)[c.refpos]
            self.new_couplings(k,bare)
            for a,c in enumerate(self.channels):self.E[k,a]=bare[a]+self.r[k]*2*c.p+self.g[k]*c.p*(c.p-1)/2
            print('quotient order',k,'L',self.L,flush=True)
    def solve(self):
        self.lower_orders();self.moments();self.high_orders()
        energy=self.E[:,self.nv:].T;C=energy[2]-energy[0]
        res=max(max(abs(energy[1]-energy[0]-np.r_[.25,-.25,np.zeros(self.degree-1)])),max(abs(energy[3]-energy[0]-np.r_[.75,.25,np.zeros(self.degree-1)])))
        if res>1e-7:raise ArithmeticError(res)
        return dict(cutoff=self.L,degree=self.degree,scheme=self.scheme,C=C.tolist(),r=self.r.tolist(),g=self.g.tolist(),energies=energy.tolist(),vacuum_grid_coefficients=self.E[:,:self.nv].T.tolist(),basis_dimension=self.space.n,particle_cap=self.space.pmax,nonzero_particle_cap=self.space.qmax,ladder_edges=self.space.nnz,stored_wavefunction_entries=sum(c.psi.size for c in self.channels),tuning_residual=float(res),algorithm='ragged half-order normalized Rayleigh quotient',scope='Full finite frozen-cutoff coefficients, no thermal targets. Not analytic continuum tail amplitudes.')

def sum_long(x):
    return float(np.sum(x,dtype=np.longdouble))

def run(L,degree=8,scheme='dconn',batch=4):
    start=time.perf_counter();e=Engine(L,degree,scheme,batch);o=e.solve();o['seconds']=time.perf_counter()-start;o['maxrss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;return o
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cutoffs',nargs='+',type=int,default=[2,4,8]);p.add_argument('--degree',type=int,default=8);p.add_argument('--scheme',choices=['raw','dconn'],default='dconn');p.add_argument('--batch',type=int,default=4);p.add_argument('--out',type=Path,default=ROOT/'results/new_coefficients');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for L in a.cutoffs:
        import gc
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL(None).malloc_trim(0)
        except AttributeError:
            pass
        file=a.out/f'{a.scheme}_L{L}_d{a.degree}.json'
        if file.exists():print('already complete',file,flush=True);continue
        o=run(L,a.degree,a.scheme,a.batch);tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n');os.replace(tmp,file);print(json.dumps(o),flush=True)
