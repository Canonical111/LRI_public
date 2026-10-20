"""Direct Taylor recursion for raw, literal and self-consistent frozen-cutoff HT.
No diagrammatic thermal coefficient or extrapolation input enters this solver.
Dconn is the finite-regulator definition in the supplied note, not a claim of
complete connected physical matching. Uses ordinary full-order recursion.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,math,time,os
import numpy as np
from scipy.sparse import csr_matrix

class Space:
    def __init__(self,L:int,degree:int,pmax:int|None=None,qmax:int|None=None):
        if L<2 or L%2:raise ValueError('Even integer cutoff >=2 required')
        if not 2<=degree<=8:raise ValueError('Supported Taylor degree: 2..8')
        self.L=L;self.degree=degree
        self.pmax=3+4*(degree//2) if pmax is None else pmax
        self.qmax=4*(degree//2) if qmax is None else qmax
        if self.pmax<3 or self.qmax<0:raise ValueError('Need pmax>=3, qmax>=0')
        states=[];N=[];P=[]
        def visit(st,level,minimum,q):
            if len(states)>=400000:raise MemoryError('Reference-pilot state guard reached; use a separately validated HPC implementation.')
            states.append(st);N.append(level);P.append(len(st))
            if len(st)>=self.pmax:return
            for mode in range(minimum,L):
                if 4*(level+mode)+len(st)+1>4*L:break
                if q+(mode>0)>self.qmax:continue
                visit(st+(mode,),level+mode,mode,q+(mode>0))
        visit((),0,0,0);self.states=states;self.n=len(states);self.N=np.array(N);self.P=np.array(P)
        self.E0=self.N+self.P/4;self.F1=-self.P/4;self.energy4=4*self.N+self.P
        self.even=self.N%2==0;idx={st:i for i,st in enumerate(states)}
        self.refs=[idx[(0,)*p] for p in range(4)]
        v=np.zeros((degree,L));v[0,0]=1
        for m in range(1,L):
            v[:,m]=v[:,m-1]*(m-.5)/m
            v[1:,m]-=v[:-1,m-1]/(2*m)
        u=np.zeros_like(v);u[0]=np.sqrt(v[0])
        for k in range(1,degree):
            u[k]=(v[k]-sum(u[j]*u[k-j] for j in range(1,k)))/(2*u[0])
        ptr=[0];col=[];mode=[];occ=[]
        for st in states:
            for m in sorted(set(st)):
                t=list(st);t.remove(m);col.append(idx[tuple(t)]);mode.append(m);occ.append(math.sqrt(st.count(m)))
            ptr.append(len(col))
        mode=np.asarray(mode);occ=np.asarray(occ);col=np.asarray(col,dtype=np.int32);ptr=np.asarray(ptr,dtype=np.int64)
        self.C=[csr_matrix((occ*u[k,mode],col,ptr),shape=(self.n,self.n)) for k in range(degree)]
        self.B=[C.T for C in self.C];self.nnz=len(col)
    def linear(self,x,d,creation=False):
        mats=self.C if creation else self.B;y=np.zeros((d+1,)+x.shape[1:])
        for k in range(d+1):
            for j in range(min(k,len(mats)-1)+1):
                if k-j<len(x):y[k]+=mats[j]@x[k-j]
        return y
    def vertices(self,x,d):
        low=[x.copy()]
        for _ in range(4):low.append(self.linear(low[-1],d))
        m=self.linear(self.linear(low[0],d,True)+2*low[1],d,True)+low[2]
        v=low[0].copy()
        for j in range(1,5):v=self.linear(v,d,True)+math.comb(4,j)*low[j]
        v/=12;m[:,~self.even]=0;v[:,~self.even]=0
        return m,v

def solve(L=4,degree=7,scheme='dconn',pmax=None,qmax=None,batch=8):
    if scheme not in ['raw','literal','dconn']:raise ValueError(scheme)
    start=time.perf_counter();s=Space(L,degree,pmax,qmax)
    nq=2*L+1
    if scheme=='raw':
        nv=1;grid=np.array([2*L]);refp=np.r_[0,0,1,2,3];cut2=np.repeat(2*L,5)
    else:
        nv=nq;grid=np.arange(nq);refp=np.r_[np.zeros(nv,dtype=int),0,1,2,3];cut2=np.r_[grid,np.repeat(2*L,4)]
    nc=len(refp);refi=np.array([s.refs[p] for p in refp]);refe=refp/4
    psi=np.zeros((degree+1,s.n,nc));psi[0,refi,np.arange(nc)]=1
    E=np.zeros((degree+1,nc));E[0]=refe;r=np.zeros(degree+1);g=np.zeros(degree+1)
    allow=(s.energy4[:,None]<=2*cut2[None,:]) & s.even[:,None] & ((s.P[:,None]%2)==(refp[None,:]%2))
    den=refe[None,:]-s.E0[:,None];inv=np.divide(1,den,out=np.zeros_like(den),where=allow & (den!=0))
    lower=np.maximum(0,(2*cut2[None,:]-s.energy4[:,None])//2)
    if scheme!='raw':lower=np.minimum(lower,2*L)
    def diagonal(k):
        a=E[k,cut2][None,:]-E[k,lower]
        a*=allow
        if scheme=='literal':a[:,:nv]=0
        return a
    mref,vref=s.vertices(psi[:1],0);mref=mref[0];vref=vref[0]
    selected=[nv,nv+1,nv+2,nv+3]
    for k in range(1,degree+1):
        rhs=s.F1[:,None]*psi[k-1]
        # Batch independent vacuum subproblems to avoid replicating every ladder
        # polynomial across the full cutoff grid at once.
        for a in range(0,nc,batch):
            b=min(nc,a+batch)
            m,v=s.vertices(psi[:k,:,a:b],k-1)
            for j in range(1,k):rhs[:,a:b]+=r[j]*m[k-j]+g[j]*v[k-j]
            del m,v
        if scheme!='raw':
            for j in range(2,k):rhs+=diagonal(j)*psi[k-j]
        # At a vacuum reference M0,V0 and its own window have zero diagonal.
        # Hence the order-k vacuum energies require only already known couplings.
        E[k,:nv]=rhs[s.refs[0],:nv]
        if scheme!='raw':rhs+=diagonal(k)*psi[0]
        bare=rhs[refi,np.arange(nc)]
        r[k]=((-.25 if k==1 else 0)-(bare[nv+1]-bare[nv]))/2
        g[k]=((.25 if k==1 else 0)-(bare[nv+3]-bare[nv])-6*r[k])/3
        rhs+=r[k]*mref+g[k]*vref
        E[k]=rhs[refi,np.arange(nc)]
        for j in range(1,k+1):rhs-=psi[k-j]*E[j][None,:]
        psi[k]=rhs*inv
    energy=E[:,selected].T;C=energy[2]-energy[0]
    t1=np.zeros(degree+1);t1[:2]=[.25,-.25];t3=np.zeros(degree+1);t3[:2]=[.75,.25]
    residual=float(max(np.max(abs(energy[1]-energy[0]-t1)),np.max(abs(energy[3]-energy[0]-t3))))
    if residual>1e-7:raise ArithmeticError(f'Primary tuning residual {residual}')
    return dict(algorithm_revision='main_vacuum_distinct_from_raw_table_v2',cutoff=L,degree=degree,scheme=scheme,C=C.tolist(),r=r.tolist(),g=g.tolist(),energies=energy.tolist(),vacuum_grid_coefficients=E[:,:nv].T.tolist(),basis_dimension=s.n,ladder_edges=s.nnz,particle_cap=s.pmax,nonzero_particle_cap=s.qmax,tuning_residual=residual,seconds=time.perf_counter()-start,
                vacuum_batch=batch,scope='Coefficients of the specified finite frozen-cutoff Hamiltonian. No thermal targets. No continuum extrapolation or complete connected matching claimed.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cutoffs',type=int,nargs='+',default=[2,4,6,8]);p.add_argument('--degree',type=int,default=7);p.add_argument('--schemes',nargs='+',choices=['raw','literal','dconn'],default=['raw','dconn']);p.add_argument('--pmax',type=int);p.add_argument('--qmax',type=int);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results/direct');a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    for L in a.cutoffs:
        for scheme in a.schemes:
            out=solve(L,a.degree,scheme,a.pmax,a.qmax);path=a.out/f'{scheme}_L{L}_d{a.degree}.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)
            print(L,scheme,'C',out['C'],'sec',out['seconds'],flush=True)
