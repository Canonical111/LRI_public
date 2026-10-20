"""Independent exact-rational source derivative in Bargmann coordinates."""
from pathlib import Path
from fractions import Fraction as F
from math import comb
import time,json,argparse
ROOT=Path(__file__).resolve().parents[1];Z=F(0)

def solve(L=2,degree=8,scheme='dconn',channel='phase'):
    start=time.perf_counter();states=[]
    def rec(st,E,minimum):
        states.append(st)
        for n in range(minimum,L):
            if E+4*n+1>4*L:break
            rec(st+(n,),E+4*n+1,n)
    rec((),0,0);allset=set(states);physical=[x for x in states if sum(x)%2==0];idx={x:i for i,x in enumerate(physical)};D=len(physical)
    energy4=[len(s)+4*sum(s) for s in physical];par=[len(s)%2 for s in physical];refs=[idx[(0,)*p] for p in range(4)]
    weights=[[F(1)]+[Z]*(degree-1)]
    for n in range(1,L):
        v=weights[-1];weights.append([F(2*n-1,2*n)*v[j]-(v[j-1]/(2*n) if j else Z) for j in range(degree)])
    def ladder(poly,create):
        out={}
        for st,js in poly.items():
            for n in range(L):
                if create:
                    dest=tuple(sorted(st+(n,)))
                    if dest not in allset:continue
                    val=out.setdefault(dest,[Z]*degree)
                    for j,x in enumerate(js):val[j]+=x
                elif n in st:
                    k=st.count(n);s=list(st);s.remove(n);dest=tuple(s);val=out.setdefault(dest,[Z]*degree)
                    for j in range(degree):
                        for a in range(j+1):val[j]+=k*weights[n][a]*js[j-a]
        return out
    def mult(poly,fun):return {st:[fun(st)*v for v in js] for st,js in poly.items()}
    delta=lambda m:2-2*((m+7)//8)
    def emit(op,col,poly,mul=F(1)):
        for st,js in poly.items():
            if st not in idx:continue
            row=idx[st]
            for j,x in enumerate(js):
                if x:op[j][col][row]=op[j][col].get(row,Z)+mul*x
    ops={}
    for q in (2,4,6):
        op=[[{} for _ in range(D)] for _ in range(degree)]
        for col,st in enumerate(physical):
            low=[{st:[F(1)]+[Z]*(degree-1)}]
            for _ in range(q):low.append(ladder(low[-1],False))
            for c in range(q+1):
                val=low[q-c]
                for _ in range(c):val=ladder(val,True)
                emit(op,col,val,F(comb(q,c),12 if q==4 else 1))
        ops[q]=op
    jp=[[{} for _ in range(D)] for _ in range(degree)]
    for col,st in enumerate(physical):
        p0={st:[F(1)]+[Z]*(degree-1)}
        emit(jp,col,ladder(ladder(mult(p0,lambda st:delta(len(st)+4)),True),True))
        emit(jp,col,ladder(mult(ladder(p0,False),lambda st:delta(len(st)+3)+delta(len(st)+5)),True))
        emit(jp,col,mult(ladder(ladder(p0,False),False),lambda st:delta(len(st)+4)))
    jn=[[{} for _ in range(D)] for _ in range(degree)]
    for k in range(degree):
      for c,st in enumerate(physical):
       for row,v in ops[2][k][c].items():jn[k][c][row]=-F(sum(st)+sum(physical[row]),2)*v
    if channel=='phi6':src=ops[6]
    elif channel=='phase':src=jp
    elif channel=='number':src=jn
    elif channel=='mass':src=ops[2]
    elif channel=='quartic':src=ops[4]
    elif channel=='full':
        src=[[dict(jp[k][c]) for c in range(D)] for k in range(degree)]
        for k in range(degree):
         for c in range(D):
          for row,v in jn[k][c].items():src[k][c][row]=src[k][c].get(row,Z)+v
    else:raise ValueError(channel)
    def action(op,vec):
        out=[Z]*D
        for col,x in enumerate(vec):
            if x:
                for row,v in op[col].items():out[row]+=v*x
        return out
    nv=2*L+1 if scheme=='dconn' else 1;pp=[0]*nv+[0,1,2,3];cuts=(list(range(nv)) if nv>1 else [2*L])+[2*L]*4
    E=[[F(p,4)]+[Z]*degree for p in pp];dE=[[Z]*(degree+1) for _ in pp]
    psi=[[[Z]*D for _ in range(degree+1)] for _ in pp];dpsi=[[[Z]*D for _ in range(degree+1)] for _ in pp]
    allowed=[]
    for j,p in enumerate(pp):
        psi[j][0][refs[p]]=F(1);allowed.append([i for i in range(D) if par[i]==p%2 and energy4[i]<=2*cuts[j]])
    r=[Z]*(degree+1);g=r.copy();dr=r.copy();dg=r.copy()
    def dj(A,col,row,k):
        if scheme=='raw':return Z
        return A[cuts[col]][k]-A[(2*cuts[col]-energy4[row])//2][k]
    for k in range(1,degree+1):
        rhs=[];rhs1=[];gg=[sum(g[j]*g[z-j] for j in range(z+1)) for z in range(degree+1)]
        for c,p in enumerate(pp):
            v=[-F(len(st),4)*psi[c][k-1][i] for i,st in enumerate(physical)]
            dv=[-F(len(st),4)*dpsi[c][k-1][i] for i,st in enumerate(physical)]
            for j in range(1,k):
             for a in range(k-j+1):
              for coef,dcoef,op in [(r[j],dr[j],ops[2][a]),(g[j],dg[j],ops[4][a])]:
                if coef or dcoef:
                    w=action(op,psi[c][k-j-a]);dw=action(op,dpsi[c][k-j-a])
                    for row in allowed[c]:v[row]+=coef*w[row];dv[row]+=dcoef*w[row]+coef*dw[row]
            for j in range(2,k+1):
             if gg[j]:
              for a in range(k-j+1):
                w=action(src[a],psi[c][k-j-a])
                for row in allowed[c]:dv[row]+=gg[j]*w[row]
            for j in range(2,k):
             for row in allowed[c]:
                v[row]+=dj(E,c,row,j)*psi[c][k-j][row]
                dv[row]+=dj(E,c,row,j)*dpsi[c][k-j][row]+dj(dE,c,row,j)*psi[c][k-j][row]
            rhs.append(v);rhs1.append(dv)
        for c in range(nv):E[c][k]=rhs[c][refs[0]];dE[c][k]=rhs1[c][refs[0]]
        for c in range(nv,len(pp)):
            rhs[c][refs[pp[c]]]+=dj(E,c,refs[pp[c]],k);rhs1[c][refs[pp[c]]]+=dj(dE,c,refs[pp[c]],k)
        raw=[v[refs[p]] for v,p in zip(rhs,pp)];raw1=[v[refs[p]] for v,p in zip(rhs1,pp)]
        r[k]=((-F(1,4) if k==1 else Z)-raw[nv+1]+raw[nv])/2
        g[k]=((F(1,4) if k==1 else Z)-raw[nv+3]+raw[nv]-6*r[k])/3
        dr[k]=(-raw1[nv+1]+raw1[nv])/2;dg[k]=(-raw1[nv+3]+raw1[nv]-6*dr[k])/3
        for c,p in enumerate(pp):
            v=rhs[c];dv=rhs1[c]
            for coef,dcoef,op in [(r[k],dr[k],ops[2][0]),(g[k],dg[k],ops[4][0])]:
                for row,val in op[refs[p]].items():v[row]+=coef*val;dv[row]+=dcoef*val
            E[c][k]=v[refs[p]];dE[c][k]=dv[refs[p]]
            for row in allowed[c]:
             if row!=refs[p]:
                psi[c][k][row]=(v[row]-sum(E[c][j]*psi[c][k-j][row] for j in range(1,k+1)))/F(p-energy4[row],4)
                dpsi[c][k][row]=(dv[row]-sum(E[c][j]*dpsi[c][k-j][row]+dE[c][j]*psi[c][k-j][row] for j in range(1,k+1)))/F(p-energy4[row],4)
    coeff=[a-b for a,b in zip(E[nv+2],E[nv])];resp=[a-b for a,b in zip(dE[nv+2],dE[nv])]
    return dict(cutoff=L,degree=degree,scheme=scheme,channel=channel,C=list(map(str,coeff)),response=list(map(str,resp)),seconds=time.perf_counter()-start,full_energy_space=D)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cutoffs',type=int,nargs='+',default=[2,4]);p.add_argument('--channels',nargs='+',default=['phi6','phase','number','full']);p.add_argument('--degree',type=int,default=8);a=p.parse_args()
 for L in a.cutoffs:
  for c in a.channels:
    o=solve(L,a.degree,channel=c);f=ROOT/f'results/exact_{c}_L{L}_d{a.degree}.json';f.write_text(json.dumps(o,indent=2)+'\n');print(L,c,o['response'],o['seconds'],flush=True)
