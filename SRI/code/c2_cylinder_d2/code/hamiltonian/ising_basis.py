"""Orthonormal Majorana representation of the diagonal Ising CFT.

NS/R spin form factors use a real chiral gauge, unit plane two-point functions.
No LRI coefficient or integral from the supplied study is used.
"""
from __future__ import annotations
from functools import lru_cache
from math import comb, floor, sqrt
from fractions import Fraction
import numpy as np

@lru_cache(None)
def modes(budget2:int, ramond:bool):
    out=[]
    def rec(prefix,least,budget):
        out.append(prefix)
        for m in range(least,budget+1,2): rec(prefix+(m,),m+2,budget-m)
    rec((),2 if ramond else 1,budget2)
    return tuple(sorted(out,key=lambda x:(sum(x),x)))

@lru_cache(None)
def spin_chiral(r:tuple,ns:tuple)->float:
    x=(-1.)**((len(ns)%2)*len(r))
    for m in r:
        n=m//2; x*=comb(2*n,n)/(4.**n)
    for m in ns:
        n=(m-1)//2; x*=comb(2*n,n)/(4.**n)
    for occ in (r,ns):
        for i,m in enumerate(occ):
            for k in occ[i+1:]: x*=(m-k)/(m+k)
    for m in r:
        for k in ns: x*=(m+k)/(m-k)
    return x*2**(-.5*(len(r)+len(ns)))

@lru_cache(None)
def spin_chiral_exact(r:tuple,ns:tuple):
    x=Fraction((-1)**((len(ns)%2)*len(r)))
    for m in r:
        n=m//2;x*=Fraction(comb(2*n,n),4**n)
    for m in ns:
        n=(m-1)//2;x*=Fraction(comb(2*n,n),4**n)
    for occ in (r,ns):
        for i,m in enumerate(occ):
            for k in occ[i+1:]:x*=Fraction(m-k,m+k)
    for m in r:
        for k in ns:x*=Fraction(m+k,m-k)
    x/=2**((len(r)+len(ns))//2)
    return x,(len(r)+len(ns))%2

@lru_cache(None)
def fermion(bra:tuple,ket:tuple,ramond:bool)->float:
    if bra==ket:return (-1.)**len(ket)/sqrt(2) if ramond else 0.
    remove=set(ket)-set(bra);add=set(bra)-set(ket)
    if len(remove)+len(add)!=1:return 0.
    p=next(iter(remove or add))
    return (-1.)**sum(m<p for m in ket)

class Basis:
    def __init__(self,cutoff:float):
        self.cutoff=cutoff;states=[]
        for r in (False,True):
            shift=.125 if r else 0
            occ=modes(floor(2*(cutoff-shift)+1e-10),r)
            for l in occ:
                for k in occ:
                    e=(sum(l)+sum(k))/2+shift
                    if e>cutoff+1e-10:break
                    if not r and (len(l)-len(k))%2:continue
                    states.append((e,(sum(l)-sum(k))//2,r,l,k))
        states.sort()
        self.states=states;self.e=np.array([s[0] for s in states])
        self.j=np.array([s[1] for s in states]);self.r=np.array([s[2] for s in states])
        self.lookup={s[2:]:i for i,s in enumerate(states)}
        self.vac=self.lookup[(False,(),())]
        self.eps=self.lookup[(False,(1,),(1,))]
        self.desc=self.lookup.get((False,(3,),(1,)))
        self.sig=self.lookup[(True,(),())]
        self.nsocc=sorted(set(s[3] for s in states if not s[2]),key=lambda x:(sum(x),x))
        self.rocc=sorted(set(s[3] for s in states if s[2]),key=lambda x:(sum(x),x))
        ni={v:i for i,v in enumerate(self.nsocc)};ri={v:i for i,v in enumerate(self.rocc)}
        self.li=np.array([(ri if s[2] else ni)[s[3]] for s in states])
        self.ri=np.array([(ri if s[2] else ni)[s[4]] for s in states])
        self.chiral=np.array([[spin_chiral(r,n) for r in self.rocc] for n in self.nsocc])
    def spin_block(self,ns,rs):
        return self.chiral[self.li[ns,None],self.li[rs][None,:]]*self.chiral[self.ri[ns,None],self.ri[rs][None,:]]
    def spin_column(self,bra,ket):
        if self.r[ket]:return self.spin_block(bra,np.array([ket]))[:,0]
        return self.spin_block(np.array([ket]),bra)[0,:]
    def energy_column(self,bra,ket):
        s=self.states[ket]
        return np.array([fermion(self.states[i][3],s[3],s[2])*fermion(self.states[i][4],s[4],s[2]) if self.r[i]==s[2] else 0 for i in bra])
    def energy_sparse(self,indices):
        """Angular-integrated epsilon without 2*pi; indices have fixed spin.

        Momentum conservation forces left/right fermion modes to have the
        same signed energy change. Only pair creation/annihilation and the
        Ramond zero-mode diagonal survive.
        """
        from scipy.sparse import csr_matrix
        where={i:k for k,i in enumerate(indices)};row=[];col=[];val=[]
        assert len(set(self.j[indices]))==1
        for c,i in enumerate(indices):
            e,j,r,l,k=self.states[i]
            if r:
                row.append(c);col.append(c);val.append((-1.)**(len(l)+len(k))/2)
            for m in range(2 if r else 1,floor(2*self.cutoff)+1,2):
                if (m in l)!=(m in k):continue
                if m in l:
                    l2=tuple(v for v in l if v!=m);k2=tuple(v for v in k if v!=m)
                else:
                    if e+m>self.cutoff+1e-12:continue
                    l2=tuple(sorted(l+(m,)));k2=tuple(sorted(k+(m,)))
                ix=self.lookup.get((r,l2,k2));pos=where.get(ix)
                if pos is not None:
                    row.append(pos);col.append(c)
                    val.append((-1.)**(sum(v<m for v in l)+sum(v<m for v in k)))
        return csr_matrix((val,(row,col)),shape=(len(indices),len(indices)))

def virasoro(occ,n,ramond):
    def act(o,m):
        if m==0:return (o,(-1.)**len(o)/sqrt(2)) if ramond else (None,0)
        p=abs(m);sg=(-1.)**sum(k<p for k in o)
        if m>0:return (tuple(k for k in o if k!=p),sg) if p in o else (None,0)
        return (tuple(sorted(o+(p,))),sg) if p not in o else (None,0)
    if n==0:return {occ:sum(occ)/2+(1/16 if ramond else 0)}
    out={};bound=max(occ,default=0)+2*abs(n)+4
    for r2 in range(-bound,bound+1):
        if r2%2!=(0 if ramond else 1):continue
        mid,v=act(occ,2*n-r2)
        if not v:continue
        dst,w=act(mid,r2)
        if not w:continue
        out[dst]=out.get(dst,0)+(n-r2)/4*v*w
    return {k:v for k,v in out.items() if abs(v)>1e-14}
