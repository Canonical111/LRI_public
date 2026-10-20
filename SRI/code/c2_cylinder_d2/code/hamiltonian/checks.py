"""Finite-basis and exact second-order consistency tests; no physical C2 input."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
from ising_basis import Basis,modes,spin_chiral,spin_chiral_exact,virasoro
from spectral import evaluate


def ward_checks():
    residuals=[]
    # [L_n,sigma(1)] = partial sigma(1)+(n+1) h_sigma sigma(1).
    # For <r|sigma|ns>, partial sigma = (h_r-h_ns-h_sigma) sigma.
    for r in modes(8,True):
        for ns in modes(8,False):
            for n in [-2,-1,1,2]:
                lhs=sum(v*spin_chiral(rr,ns) for rr,v in virasoro(r,-n,True).items())
                lhs-=sum(v*spin_chiral(r,nn) for nn,v in virasoro(ns,n,False).items())
                rhs=((sum(r)-sum(ns))/2+1/16+n/16)*spin_chiral(r,ns)
                residuals.append(abs(lhs-rhs))
    return max(residuals),len(residuals)


def shells():
    b=Basis(12);L=10;cc=np.ones(L+1)
    for k in range(1,L+1):cc[k]=cc[k-1]*(15/8+k-1)/k
    result=[]
    for name,t in [('vacuum',b.vac),('epsilon',b.eps),('descendant',b.desc)]:
        sums={}
        for ell in range(L+1):
            for p in range(ell+1):
                q=ell-p;de=15/8+ell;j=p-q
                inds=np.flatnonzero(b.r&(b.j+j==b.j[t])&(b.e+de<=12))
                v=2*math.pi*np.sqrt(cc[p]*cc[q])*b.spin_column(inds,t)
                for e,x in zip(b.e[inds]+de,v*v):sums[e]=sums.get(e,0)+x
        errors=[]
        for e,v in sums.items():
            if name=='vacuum':expected=math.pi**2*e**2
            elif name=='epsilon':expected=math.pi**2*(e-1)**2
            else:expected=math.pi**2*((e-2)**2+(0.25 if e==3 else 0))
            errors.append(abs(v-expected)/max(1,abs(expected)))
        result.append(dict(state=name,shells=len(sums),max_relative_error=max(errors)))
    return result


def four_spin():
    out=[];gaps=np.array([.8,.9,1.1])
    # Cylinder operators at cumulative times 0,t1,t1+t2,t1+t2+t3.
    times=np.r_[0,np.cumsum(gaps)];z=np.exp(times)
    exact=(np.prod(z)**.125)*((z[2]-z[0])*(z[3]-z[1])/
        ((z[1]-z[0])*(z[3]-z[0])*(z[2]-z[1])*(z[3]-z[2])))**.25
    for cutoff in [8,12,16,20]:
        b=Basis(cutoff);ns=np.flatnonzero(~b.r);rs=np.flatnonzero(b.r)
        S=b.spin_block(ns,rs);v=b.spin_column(rs,b.vac)
        raw=np.dot(v*np.exp(-gaps[0]*b.e[rs]),S.T@(np.exp(-gaps[1]*b.e[ns])*(S@(np.exp(-gaps[2]*b.e[rs])*v))))
        out.append(dict(cutoff=cutoff,value=float(raw),exact=float(exact),error=float(raw-exact)))
    return out


def recursion_check():
    b=Basis(4);ns=np.flatnonzero((~b.r)&(b.j==0));rs=np.flatnonzero(b.r&(b.j==0));n0=len(ns);n1=len(rs)
    ids=[(0,i) for i in ns]+[(1,i) for i in rs]+[(2,i) for i in ns]
    E=np.array([b.e[i]+15/8*n for n,i in ids]);V=np.zeros((len(E),len(E)))
    W=np.zeros_like(V);a=.75;c=np.exp(-a*15/8/2);S=2*math.pi*c*b.spin_block(ns,rs)
    V[:n0,n0:n0+n1]=S;V[n0:n0+n1,:n0]=S.T
    V[n0:n0+n1,n0+n1:]=math.sqrt(2)*S.T;V[n0+n1:,n0:n0+n1]=math.sqrt(2)*S
    for q,(n,i) in enumerate(ids):
        for p,(m,j) in enumerate(ids):
            if n==m:W[p,q]=2*math.pi*b.energy_column(np.array([j]),i)[0]
    t=.37;k=-.2
    W=t*W+k*np.diag([b.e[i] for n,i in ids])
    values=evaluate(b,0,[a],[b.vac,b.eps]);res=[]
    for target in [b.vac,b.eps]:
        ix=ids.index((0,target));u=np.zeros(len(E));u[ix]=1
        R=np.divide(1.,E[ix]-E,out=np.zeros(len(E)),where=np.abs(E[ix]-E)>1e-12)
        psi=[u];en=[E[ix]]
        for order in range(1,5):
            temp=V@psi[order-1]
            if order>=2:temp+=W@psi[order-2]
            ek=temp[ix];en.append(ek)
            for m in range(1,order):temp-=en[m]*psi[order-m]
            psi.append(R*temp)
        rr=next(r for r in values['records'] if r['target']==target)
        expected=rr['E4']+t*rr['mixed_thermal']+k*rr['mixed_D_Ising']+t*t*rr['thermal_squared']
        res.append(dict(target=target,recursive_E4=float(en[4]),resolvent_E4=expected,error=float(en[4]-expected)))
    return res

if __name__=='__main__':
    w,n=ward_checks()
    result=dict(ward_identity_max_error=w,ward_checks=n,shells=shells(),four_spin=four_spin(),recursion=recursion_check())
    assert w<1e-12
    assert max(r['max_relative_error'] for r in result['shells'])<1e-12
    assert abs(result['four_spin'][-1]['error'])<1e-8
    assert max(abs(r['error']) for r in result['recursion'])<1e-9
    Path(__file__).with_name('checks_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
