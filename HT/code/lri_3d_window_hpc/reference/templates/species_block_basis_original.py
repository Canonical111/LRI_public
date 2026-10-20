"""Complete S^2 bath: modes (radial n, ell, m), level 2n+ell > 0.

The cutoff preserves full SO(3) multiplets. There is no extra particle cap.
Rotational sectors are highest-weight nullspaces of J_+, not merely m=0.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.linalg import null_space
from scipy.special import poch,lpmv,gammaln


def dimension(cutoff):
    dp=[0]*(cutoff+1);dp[0]=1
    for k in range(1,cutoff+1):
        for _ in range((k+1)*(k+2)//2):
            for n in range(k,cutoff+1):dp[n]+=dp[n-k]
    return sum(dp)

@dataclass
class SphereBathBasis:
    cutoff:int
    labels:tuple
    states:list
    N:np.ndarray
    P:np.ndarray
    M:np.ndarray
    ptr:np.ndarray
    parents:np.ndarray
    modes:np.ndarray
    sqocc:np.ndarray
    index:dict

    @classmethod
    def build(cls,cutoff,max_states=400000):
        cutoff=int(cutoff);size=dimension(cutoff)
        if size>max_states:raise MemoryError(f'{size} bath states exceeds guard {max_states}')
        labels=tuple((n,k-2*n,m) for k in range(1,cutoff+1) for n in range(k//2+1) for m in range(-(k-2*n),k-2*n+1))
        levels=[2*n+l for n,l,m in labels];spins=[m for n,l,m in labels]
        states=[];ns=[];ps=[];ms=[]
        def rec(s,left,start,m):
            states.append(s);ns.append(cutoff-left);ps.append(len(s));ms.append(m)
            for k in range(start,len(labels)):
                lev=levels[k]
                if lev>left:break
                rec(s+(k,),left-lev,k,m+spins[k])
        rec((),cutoff,0,0)
        if len(states)!=size:raise AssertionError('Enumeration vs dimension mismatch')
        index={s:i for i,s in enumerate(states)}
        parents=[];modes=[];amps=[];ptr=[0]
        for s in states:
            for k,count in Counter(s).items():
                tmp=list(s);tmp.remove(k);parents.append(index[tuple(tmp)])
                modes.append(k);amps.append(math.sqrt(count))
            ptr.append(len(parents))
        return cls(cutoff,labels,states,np.array(ns,np.int32),np.array(ps,np.int16),np.array(ms,np.int32),
                   np.array(ptr,np.int64),np.array(parents,np.int32),np.array(modes,np.int32),np.array(amps),index)

    def weights(self,x):
        if x<=.5:raise ValueError('Positive GFF norms require x > 1/2')
        return np.array([math.sqrt(poch(x,n+l)*poch(x-.5,n)/(math.factorial(n)*poch(1.5,n+l))) for n,l,m in self.labels])

    def angular_values(self,z):
        # sqrt(4 pi) Y_lm(theta,phi=0); spherical average is dOmega/(4pi).
        out=[]
        for n,l,m in self.labels:
            k=abs(m)
            v=math.sqrt(2*l+1)*math.exp(.5*(gammaln(l-k+1)-gammaln(l+k+1)))*lpmv(k,l,z)
            if m<0:v*=(-1)**k
            out.append(v)
        return np.array(out)

    def ladders(self,x,z):
        amp=self.weights(x)*self.angular_values(z)
        C=csr_matrix((self.sqocc*amp[self.modes],self.parents.copy(),self.ptr.copy()),shape=(len(self.N),len(self.N)))
        return C.T.tocsr(),C

    def highest_weight(self,spin=0,inversion=None):
        if inversion is None:inversion=spin%2
        key=(spin,inversion)
        if hasattr(self,'_projectors') and key in self._projectors:return self._projectors[key]
        if spin<0:raise ValueError('Spin is nonnegative')
        # J_+ preserves the occupation count in each radial/angular species
        # (n,ell). Resolving these exact blocks avoids huge disconnected SVDs.
        signatures=[]
        for state in self.states:
            signatures.append(tuple(sorted(Counter(self.labels[k][:2] for k in state).items())))
        groups=defaultdict(list);target_groups=defaultdict(list)
        for i in np.flatnonzero((self.M==spin)&(self.N%2==inversion)):
            groups[(int(self.N[i]),int(self.P[i]),signatures[i])].append(int(i))
        for i in np.flatnonzero((self.M==spin+1)&(self.N%2==inversion)):
            target_groups[(int(self.N[i]),int(self.P[i]),signatures[i])].append(int(i))
        lookup={key:k for k,key in enumerate(self.labels)}
        rows=[];cols=[];data=[];sn=[];sp=[];rep=[];offset=0;maxres=0.;maxorth=0.
        for (N,P,sig),inds in sorted(groups.items()):
            targets=target_groups.get((N,P,sig),[])
            tid={int(i):j for j,i in enumerate(targets)}
            jp=np.zeros((len(targets),len(inds)))
            for j,i in enumerate(inds):
                occ=Counter(self.states[i])
                for k,count in occ.items():
                    n,l,m=self.labels[k]
                    if m==l:continue
                    kp=lookup[(n,l,m+1)]
                    ss=list(self.states[i]);ss.remove(k);ss.append(kp);ss.sort()
                    ip=self.index[tuple(ss)]
                    jp[tid[ip],j]+=math.sqrt((l-m)*(l+m+1)*count*(occ.get(kp,0)+1))
            Q=np.eye(len(inds)) if not len(targets) else null_space(jp,rcond=5e-13)
            if Q.shape[1]==0:continue
            for j in range(Q.shape[1]):
                im=int(np.argmax(abs(Q[:,j])))
                if Q[im,j]<0:Q[:,j]*=-1
            maxres=max(maxres,float(np.max(abs(jp@Q),initial=0.)))
            maxorth=max(maxorth,float(np.max(abs(Q.T@Q-np.eye(Q.shape[1])),initial=0.)))
            ii,jj=np.nonzero(Q)
            rows.extend(np.array(inds)[ii]);cols.extend(offset+jj);data.extend(Q[ii,jj])
            sn.extend([N]*Q.shape[1]);sp.extend([P]*Q.shape[1]);rep.extend([inds[0]]*Q.shape[1])
            offset+=Q.shape[1]
        S=csr_matrix((data,(rows,cols)),shape=(len(self.N),offset))
        if maxres>1e-10 or maxorth>1e-10:raise RuntimeError('Highest-weight projection failed')
        ans=(S,np.array(sn,np.int32),np.array(sp,np.int16),np.array(rep,np.int64),dict(Jplus_residual=maxres,orthogonality=maxorth))
        if not hasattr(self,'_projectors'):self._projectors={}
        self._projectors[key]=ans
        return ans

    @property
    def nbytes(self):
        return sum(a.nbytes for a in (self.N,self.P,self.M,self.ptr,self.parents,self.modes,self.sqocc))
