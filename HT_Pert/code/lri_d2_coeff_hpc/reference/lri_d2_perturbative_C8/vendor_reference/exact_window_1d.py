"""Independent rational frozen-cutoff window recursion.
Eigenvalue calculation in the epsilon-dependent Bargmann coordinates
prod_n (u_n(epsilon) a_n^dagger)^occupancy. Creation multiplies by X_n;
annihilation is v_n(epsilon) d/dX_n. No square roots or numerical eigenvectors.
Retains the COMPLETE finite energy space, not perturbative particle caps.
"""
from fractions import Fraction as F
from pathlib import Path
from math import comb
from functools import lru_cache
import argparse,json,time
Z=F(0)

def solve(L=2,degree=7,scheme='dconn'):
    if scheme not in ('raw','literal','dconn'):raise ValueError(scheme)
    t=time.perf_counter();states=[]
    def rec(st,E,minimum):
        states.append(st)
        for n in range(minimum,L):
            if E+4*n+1>4*L:break
            rec(st+(n,),E+4*n+1,n)
    rec((),0,0);allset=set(states)
    physical=[st for st in states if sum(st)%2==0];idx={st:i for i,st in enumerate(physical)};D=len(physical)
    energy4=[len(s)+4*sum(s) for s in physical];par=[len(s)%2 for s in physical]
    refs=[idx[(0,)*p] for p in range(4)]
    weights=[[F(1)]+[Z]*(degree-1)]
    for n in range(1,L):
        v=weights[-1]
        weights.append([F(2*n-1,2*n)*v[k]-(v[k-1]/(2*n) if k else Z) for k in range(degree)])
    def ladder(poly,create):
        out={}
        for st,js in poly.items():
            for n in range(L):
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
    nv=2*L+1 if scheme!='raw' else 1
    pp=[0]*nv+[0,1,2,3];cuts=list(range(nv)) if nv>1 else [2*L];cuts+= [2*L]*4
    E=[[F(p,4)]+[Z]*degree for p in pp]
    psi=[[[Z]*D for _ in range(degree+1)] for p in pp]
    allowed=[]
    for j,p in enumerate(pp):
        psi[j][0][refs[p]]=F(1)
        allowed.append([i for i in range(D) if par[i]==p%2 and energy4[i]<=2*cuts[j]])
    r=[Z]*(degree+1);g=r.copy()
    def dj(slot,row,k):
        if scheme=='raw' or (scheme=='literal' and slot<nv):return Z
        q=cuts[slot];lo=(2*q-energy4[row])//2
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
                    psi[col][k][row]=rhs2/(F(p-energy4[row],4))
    selected=[E[nv],E[nv+1],E[nv+2],E[nv+3]];C=[a-b for a,b in zip(selected[2],selected[0])]
    return dict(algorithm_revision='main_vacuum_distinct_from_raw_table_v2',cutoff=L,degree=degree,scheme=scheme,rational_C=list(map(str,C)),rational_r=list(map(str,r)),rational_g=list(map(str,g)),rational_energies=[list(map(str,v)) for v in selected],C=list(map(float,C)),basis_dimension=D,full_space=True,seconds=time.perf_counter()-t,
        scope='Exact finite-regulator formal recursion; no thermal reference coefficient used.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cutoffs',nargs='+',type=int,default=[2,4]);ap.add_argument('--degree',type=int,default=7);ap.add_argument('--schemes',nargs='+',default=['raw','literal','dconn']);ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results/exact');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for L in a.cutoffs:
        for scheme in a.schemes:
            d=solve(L,a.degree,scheme);(a.out/f'{scheme}_L{L}_d{a.degree}.json').write_text(json.dumps(d,indent=2)+'\n');print(L,scheme,d['rational_C'],d['seconds'],flush=True)
