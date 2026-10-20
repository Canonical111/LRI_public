#!/usr/bin/env python3
"""Independent exact-rational epsilon expansion in the nonorthogonal basis
prod_n (u_n(epsilon) a_n^dagger)^k |0>. Creation has coefficient 1;
annihilation has coefficient k*u_n(epsilon)^2. No square roots or floating
point enter this calculation, and every state under the free-energy bound
is retained. It supplies exact finite-Lambda checks, not continuum results.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse,json,math,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
Z=F(0)

def basis(L):
    b=[]
    def rec(occ,p,N,start):
        b.append(tuple(occ))
        for n in range(start,L):
            if 4*N+p+4*n+1>4*L:break
            occ[n]+=1;rec(occ,p+1,N+n,n);occ[n]-=1
    rec([0]*L,0,0,0)
    return b

def exact(L,degree=8):
    start=time.perf_counter()
    full=basis(L);idx={t:i for i,t in enumerate(full)}
    v=[[F(1)]+[Z]*degree]
    for n in range(1,L):
        prev=v[-1];v.append([F(2*n-1,2*n)*prev[k]-(prev[k-1]/(2*n) if k else 0) for k in range(degree+1)])
    physical=[t for t in full if sum(n*a for n,a in enumerate(t))%2==0]
    idp={t:i for i,t in enumerate(physical)};D=len(physical)
    def apply(src,creation=False):
        out={}
        for state,poly in src.items():
            for n in range(L):
                if not creation and not state[n]:continue
                target=list(state);target[n]+=1 if creation else -1;target=tuple(target)
                if target not in idx:continue
                q=out.setdefault(target,[Z]*(degree+1))
                if creation:
                    for k in range(degree+1):q[k]+=poly[k]
                else:
                    for k in range(degree+1):
                        q[k]+=state[n]*sum(v[n][j]*poly[k-j] for j in range(k+1))
        return out
    ops=[]
    for power,norm in ((2,F(1)),(4,F(1,12))):
        mats=[[{} for _ in range(D)] for _ in range(degree)]
        for i,state in enumerate(physical):
            low=[{state:[F(1)]+[Z]*degree}]
            for j in range(power):low.append(apply(low[-1]))
            for creates in range(power+1):
                term=low[power-creates]
                for j in range(creates):term=apply(term,True)
                fac=norm*math.comb(power,creates)
                for tar,poly in term.items():
                    if tar not in idp:continue
                    k=idp[tar]
                    for order in range(degree):
                        if poly[order]:mats[order][i][k]=mats[order][i].get(k,Z)+fac*poly[order]
        ops.append(mats)
    def action(mats,x):
        y=[Z]*D
        for i,xi in enumerate(x):
            if xi:
                for k,a in mats[i].items():y[k]+=a*xi
        return y
    refs=[idp[tuple([p]+[0]*(L-1))] for p in range(4)]
    Es=[F(sum((4*n+1)*q for n,q in enumerate(t)),4) for t in physical]
    F1=[-F(sum(t),4) for t in physical]
    psi=[[[Z]*D for _ in range(degree+1)] for p in range(4)]
    E=[[F(p,4)]+[Z]*degree for p in range(4)];r=[Z]*(degree+1);g=r.copy()
    for p in range(4):psi[p][0][refs[p]]=F(1)
    for k in range(1,degree+1):
        raw=[];rhs=[]
        for p in range(4):
            t=[F1[i]*psi[p][k-1][i] for i in range(D)]
            for j in range(1,k):
                for l in range(k-j+1):
                    for coeff,op in ((r[j],ops[0]),(g[j],ops[1])):
                        if coeff:
                            a=action(op[l],psi[p][k-j-l])
                            for i in range(D):t[i]+=coeff*a[i]
            rhs.append(t);raw.append(t[refs[p]])
        r[k]=((-F(1,4) if k==1 else Z)-(raw[1]-raw[0]))/2
        g[k]=((F(1,4) if k==1 else Z)-(raw[3]-raw[0])-6*r[k])/3
        for p in range(4):
            t=rhs[p]
            for coeff,op in ((r[k],ops[0]),(g[k],ops[1])):
                if coeff:
                    for i,val in op[0][refs[p]].items():t[i]+=coeff*val
            E[p][k]=t[refs[p]]
            for i in range(D):
                if i!=refs[p] and sum(physical[i])%2==p%2:
                    psi[p][k][i]=(t[i]-sum(E[p][j]*psi[p][k-j][i] for j in range(1,k+1)))/(F(p,4)-Es[i])
    C=[E[2][k]-E[0][k] for k in range(degree+1)]
    out={'cutoff':L,'degree':degree,'rational_C':[str(a) for a in C],
         'C':[float(a) for a in C],'rational_r':[str(a) for a in r],
         'rational_g':[str(a) for a in g],
         'basis_dimension':D,'seconds':time.perf_counter()-start,
         'arithmetic':'exact fractions in nonorthogonal oscillator basis'}
    rawpath=ROOT/'results/raw'/f'raw_L{L}_d8.json'
    if rawpath.exists():
        old=json.loads(rawpath.read_text());out['comparison_max_absolute_error']=max(abs(a-b) for a,b in zip(out['C'],old['C']))
        np.testing.assert_allclose(out['C'],old['C'],rtol=5e-11,atol=1e-7)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cutoffs',nargs='+',type=int,default=[2,4]);args=ap.parse_args()
    rows=[]
    for L in args.cutoffs:
        a=exact(L);rows.append(a);print(L,a['C'][8],a.get('comparison_max_absolute_error'),a['seconds'],flush=True)
    (ROOT/'results/exact_rational_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
