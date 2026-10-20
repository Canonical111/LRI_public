#!/usr/bin/env python3
"""Independent normalization, symmetry, quadrature and local-basis tests."""
from pathlib import Path
import sys,json,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
import numpy as np
from scipy.special import eval_gegenbauer,eval_legendre
from scipy.sparse import csr_matrix
from numpy.polynomial.legendre import leggauss
from d3dressed.basis import SphereBathBasis
from d3dressed.operators import ProductOperator
from d3dressed.local import LocalProblem
from check_second_order import C2


def direct_C2(op):
    """Second-order RS in free zero-mode occupation basis, not dressed eigenstates."""
    x=.75;n0=10
    a=np.zeros((n0+4,n0+4));a[np.arange(n0+3),np.arange(1,n0+4)]=np.sqrt(np.arange(1,n0+4))
    q=a+a.T;Iq=np.eye(len(a));q2=q@q;q3=q2@q;q4=q2@q2
    R=[Iq,q,q2-Iq,q3-3*q,q4-6*q2+3*Iq]
    nB=op.nB;vac=int(np.flatnonzero((op.N==0)&(op.P==0))[0]);F=[]
    vv=np.eye(nB)[:,vac]
    for p in range(4):
        v=np.outer(vv,R[4][:n0,p])/12
        for k in range(1,5):v+=math.comb(4,k)/12*np.outer(op.W[k-1]@vv,R[4-k][:n0,p])
        den=x*p-op.N[:,None]-x*(op.P[:,None]+np.arange(n0)[None,:])
        mask=abs(den)>1e-10
        F.append(float(np.sum(v[mask]**2/den[mask]))/9)
    return F[2]-F[1]-F[3]/3+F[0]/3


def projected_vertices(basis,S,x,nodes):
    z,w=leggauss(nodes);out=[np.zeros((S.shape[1],S.shape[1])) for _ in range(4)]
    for zz,ww in zip(z,w/2):
        B,C=basis.ladders(x,zz);As=[S]
        for k in range(4):As.append(B@As[-1])
        for k in range(1,5):
            for j in range(k+1):out[k-1]+=ww*math.comb(k,j)*(As[j].T@As[k-j]).toarray()
    return out

def main():
    report={}
    # Scalar two-point spherical harmonic expansion, independently Gegenbauer.
    err=0.
    for x in (.5182,.6,.749):
        b=SphereBathBasis.build(6);u=b.weights(x)
        for k in range(7):
            for z in (-.77,-.1,.32,.9):
                s=1. if k==0 else sum((2*l+1)*u[j]**2*eval_legendre(l,z) for j,(n,l,m) in enumerate(b.labels) if 2*n+l==k and m==0)
                err=max(err,abs(s-eval_gegenbauer(k,x,z)))
    report['gegenbauer_addition_max_abs']=err;assert err<3e-13
    qerr=0.;cerr=0.;rot=0.;herm=0.
    for L in (2,4,6):
        b=SphereBathBasis.build(L);op=ProductOperator(b,.75,8)
        cerr=max(cerr,abs(direct_C2(op)-C2(L)))
        for x in (.53,.7):
            a=ProductOperator(b,x,8);extra=ProductOperator(b,x,8,nodes=2*L+5)
            qerr=max(qerr,max(np.max(abs((aa-bb).toarray()),initial=0) for aa,bb in zip(a.W,extra.W)))
            herm=max(herm,a.hermiticity_residual)
        # Lower a true spin-one highest-weight basis to M=0 and compare all
        # sphere-integrated operators. No spin-zero identification is assumed.
        S1,N,P,rep,meta=b.highest_weight(1,1)
        lookup={label:k for k,label in enumerate(b.labels)}
        from collections import Counter
        rows=[];cols=[];vals=[]
        for i,ss in enumerate(b.states):
            for k,count in Counter(ss).items():
                n,l,m=b.labels[k]
                if m<=-l:continue
                dest=lookup[n,l,m-1];occ=Counter(ss);t=list(ss);t.remove(k);t.append(dest);t.sort()
                rows.append(b.index[tuple(t)]);cols.append(i);vals.append(math.sqrt((l+m)*(l-m+1)*count*(occ.get(dest,0)+1)))
        Jm=csr_matrix((vals,(rows,cols)),shape=(len(b.N),len(b.N)))
        S0=Jm@S1/math.sqrt(2)
        W1=projected_vertices(b,S1,.63,L+1);W0=projected_vertices(b,S0,.63,L+1)
        rot=max(rot,max(np.max(abs(aa-bb),initial=0) for aa,bb in zip(W1,W0)))
    report.update(sphere_quadrature_refinement_max_abs=float(qerr),second_order_matrix_vs_rational_shell_max_abs=float(cerr),rotation_M1_vs_M0_max_abs=float(rot),vertex_hermiticity_max_abs=float(herm))
    assert qerr<5e-11 and cerr<1e-12 and rot<1e-10 and herm<1e-12
    # Product Hamiltonian: independent original-coordinate normal ordering.
    b=SphereBathBasis.build(2);op=ProductOperator(b,.65,6)
    loc=LocalProblem(6,64);theta=np.array([1.2,-2.])
    w,Lmat,U,info=loc.evaluate(.65,theta);r=info['r'];g=info['g'];t=info['local_scale']
    I=np.eye(64);q=[I]+[t**j*loc.q[j] for j in range(1,5)];R=[I,q[1],q[2]-I,q[3]-3*q[1],q[4]-6*q[2]+3*I]
    full=.65/4*(loc.pp/t**2+q[2]-2*I)+r*R[2]+g*R[4]/12
    normal=[2*r*R[1]+g*R[3]/3,r*I+g*R[2]/2,g*R[1]/3,g*I/12]
    le=U.T@full@U;shift=le[0,0];le-=np.eye(len(w))*shift
    mats=np.array([U.T@a@U for a in normal]);diff=max(np.max(abs(le-np.diag(w))),np.max(abs(mats-Lmat)))
    report['original_coordinate_normal_ordering_max_abs']=float(diff);assert diff<1e-11
    # Matrix-free hermiticity independent of explicitly symmetrized W.
    rng=np.random.default_rng(9);HH=0.
    for f in (0,1):
        H=op.linear_operator(w,Lmat,f);u=rng.normal(size=op.dim);v=rng.normal(size=op.dim)
        HH=max(HH,abs(u@(H@v)-v@(H@u)))
    report['product_hermiticity_bilinear_max_abs']=float(HH);assert HH<1e-10
    out=ROOT/'reproduced/validation.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));print('PASS')
if __name__=='__main__':main()
