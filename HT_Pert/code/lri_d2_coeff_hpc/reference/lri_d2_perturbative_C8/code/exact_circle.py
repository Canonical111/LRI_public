"""Independent rational-coordinate circle HT oracle.
This extends the attributed 1D exact_window recursion to distinct (a,b) modes
and the UPLOADED two-dimensional bath-level window. No symmetry reduction or
stationary quotient is used. Exact fractions apply to all exported coefficients.
"""
from fractions import Fraction as F
from pathlib import Path
from math import comb
from functools import lru_cache
import argparse,json,time
Z=F(0)

def solve(L=2,degree=8,scheme='consistent',pmax=None):
    if scheme not in ('raw','literal','consistent'):raise ValueError(scheme)
    t=time.perf_counter();states=[]
    pmax=3+4*(degree//2) if pmax is None else pmax
    qmax=4*(degree//2)
    labels=[(0,0)]+[(a,n-a) for n in range(1,L+1) for a in range(n+1)]
    levels=[a+b for a,b in labels];spins=[a-b for a,b in labels]
    def rec(st,N,minimum):
        states.append(st)
        if len(st)>=pmax:return
        for n in range(minimum,len(labels)):
            if N+levels[n]>L:break
            if n and sum(x!=0 for x in st)>=qmax:continue
            rec(st+(n,),N+levels[n],n)
    rec((),0,0);allset=set(states)
    physical=[st for st in states if sum(spins[k] for k in st)==0]
    idx={st:i for i,st in enumerate(physical)};D=len(physical)
    modelevel=[sum(levels[k] for k in st) for st in physical]
    energy2=[len(st)+2*n for st,n in zip(physical,modelevel)];par=[len(st)%2 for st in physical]
    refs=[idx[(0,)*p] for p in range(4)]
    chiral=[[F(1)]+[Z]*(degree-1)]
    for n in range(1,L+1):
        v=chiral[-1];chiral.append([F(2*n-1,2*n)*v[k]-(v[k-1]/(4*n) if k else Z) for k in range(degree)])
    weights=[[sum((chiral[a][j]*chiral[b][k-j] for j in range(k+1)),Z) for k in range(degree)] for a,b in labels]
    def ladder(poly,create):
        out={}
        for st,js in poly.items():
            for n in range(len(labels)):
                if create:
                    dest=tuple(sorted(st+(n,)))
                    if dest not in allset:continue
                    coeff=out.setdefault(dest,[Z]*degree)
                    for j,x in enumerate(js):coeff[j]+=x
                elif n in st:
                    count=st.count(n);v=list(st);v.remove(n);dest=tuple(v)
                    coeff=out.setdefault(dest,[Z]*degree)
                    for j in range(degree):
                        for a in range(j+1):coeff[j]+=count*weights[n][a]*js[j-a]
        return out
    ops={}
    for order in (2,4):
        op=[[{} for _ in range(D)] for _ in range(degree)]
        for col,st in enumerate(physical):
            low=[{st:[F(1)]+[Z]*(degree-1)}]
            for _ in range(order):low.append(ladder(low[-1],False))
            for c in range(order+1):
                val=low[order-c]
                for _ in range(c):val=ladder(val,True)
                mult=F(comb(order,c),12 if order==4 else 1)
                for dest,js in val.items():
                    if dest not in idx:continue
                    row=idx[dest]
                    for j,x in enumerate(js):
                        if x:op[j][col][row]=op[j][col].get(row,Z)+mult*x
        ops[order]=op
    def action(op,vec):
        out=[Z]*D
        for col,x in enumerate(vec):
            if x:
                for row,val in op[col].items():out[row]+=val*x
        return out
    nv=L//2+1 if scheme!='raw' else 1
    pp=[0]*nv+[0,1,2,3];cuts=list(range(nv)) if scheme!='raw' else [L//2];cuts+=[L//2]*4
    E=[[F(p,2)]+[Z]*degree for p in pp]
    psi=[[[Z]*D for _ in range(degree+1)] for p in pp]
    allowed=[]
    for j,p in enumerate(pp):
        psi[j][0][refs[p]]=F(1)
        allowed.append([i for i in range(D) if par[i]==p%2 and modelevel[i]<=2*cuts[j]])
    r=[Z]*(degree+1);g=r.copy()
    def dj(slot,row,k):
        if scheme=='raw' or (scheme=='literal' and slot<nv):return Z
        q=cuts[slot];lo=(2*q-modelevel[row])//2
        return E[q][k]-E[lo][k]
    for k in range(1,degree+1):
        rhs=[]
        for col,p in enumerate(pp):
            v=[-F(len(st),4)*psi[col][k-1][i] for i,st in enumerate(physical)]
            for j in range(1,k):
                for a in range(k-j+1):
                    for coeff,op in [(r[j],ops[2][a]),(g[j],ops[4][a])]:
                        if coeff:
                            w=action(op,psi[col][k-j-a])
                            for row in allowed[col]:v[row]+=coeff*w[row]
            for j in range(2,k):
                for row in allowed[col]:
                    if psi[col][k-j][row]:v[row]+=dj(col,row,j)*psi[col][k-j][row]
            rhs.append(v)
        for col in range(nv):E[col][k]=rhs[col][refs[0]]
        for col in range(nv,len(pp)):rhs[col][refs[pp[col]]]+=dj(col,refs[pp[col]],k)
        raw=[v[refs[p]] for v,p in zip(rhs,pp)]
        r[k]=((-F(1,4) if k==1 else Z)-(raw[nv+1]-raw[nv]))/2
        g[k]=((F(1,4) if k==1 else Z)-(raw[nv+3]-raw[nv])-6*r[k])/3
        for col,p in enumerate(pp):
            v=rhs[col]
            for coeff,op in [(r[k],ops[2][0]),(g[k],ops[4][0])]:
                for row,val in op[refs[p]].items():v[row]+=coeff*val
            E[col][k]=v[refs[p]]
            for row in allowed[col]:
                if row!=refs[p]:
                    rhs2=v[row]-sum(E[col][j]*psi[col][k-j][row] for j in range(1,k+1))
                    psi[col][k][row]=rhs2/(F(p-energy2[row],2))
    selected=[E[nv],E[nv+1],E[nv+2],E[nv+3]];C=[a-b for a,b in zip(selected[2],selected[0])]
    return dict(algorithm_revision='circle_product_cutoff_exact_fractions_v1',cutoff=L,degree=degree,scheme=scheme,rational_C=list(map(str,C)),rational_r=list(map(str,r)),rational_g=list(map(str,g)),rational_energies=[list(map(str,v)) for v in selected],C=list(map(float,C)),basis_dimension=D,full_particle_space=False,particle_cap=pmax,auxiliary_space=len(states),seconds=time.perf_counter()-t,
        scope='Exact finite-regulator formal recursion; no thermal reference coefficient used.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cutoffs',nargs='+',type=int,default=[2,4]);ap.add_argument('--degree',type=int,default=8);ap.add_argument('--schemes',nargs='+',default=['raw','consistent']);ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results/exact');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for L in a.cutoffs:
        for scheme in a.schemes:
            d=solve(L,a.degree,scheme);(a.out/f'{scheme}_L{L}_d{a.degree}.json').write_text(json.dumps(d,indent=2)+'\n');print(L,scheme,d['rational_C'],d['seconds'],flush=True)
