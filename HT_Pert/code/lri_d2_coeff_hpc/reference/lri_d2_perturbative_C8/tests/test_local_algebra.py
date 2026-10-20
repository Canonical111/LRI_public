"""Independent stationarity identity, complete-vertex Hermiticity, and cutoff tests."""
from pathlib import Path
from fractions import Fraction as F
import json,sys,math
import numpy as np
from scipy.sparse import diags
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from circle_jets import CircleSpace

def stationary():
    # Exact independent Hermitian three-state problem with nonlinear H jets.
    h=[[[F(0),F(0),F(0)],[F(0),F(2),F(0)],[F(0),F(0),F(5)]],
       [[F(1,3),F(2,5),F(-1,7)],[F(2,5),F(-1,2),F(1,4)],[F(-1,7),F(1,4),F(2,3)]],
       [[F(2,9),F(1,8),F(2,7)],[F(1,8),F(1,3),F(1,11)],[F(2,7),F(1,11),F(-1,6)]]]
    def mv(mat,v):return [sum((mat[i][j]*v[j] for j in range(3)),F()) for i in range(3)]
    psi=[[F(1),F(),F()]];E=[F()]
    for k in range(1,9):
        rhs=[F()]*3
        for j in range(1,min(2,k)+1):
            v=mv(h[j],psi[k-j]);rhs=[a+b for a,b in zip(rhs,v)]
        E.append(rhs[0]);rhs=[rhs[i]-sum((E[j]*psi[k-j][i] for j in range(1,k+1)),F()) for i in range(3)]
        psi.append([F(),-rhs[1]/2,-rhs[2]/5])
    def quotient(m):
        norm=[F()]*9;num=[F()]*9
        for i in range(m+1):
          for j in range(m+1):
            k=i+j
            if k<=8:norm[k]+=sum((a*b for a,b in zip(psi[i],psi[j])),F())
            for z,mat in enumerate(h):
                if k+z<=8:num[k+z]+=sum((a*b for a,b in zip(psi[i],mv(mat,psi[j]))),F())
        out=[]
        for k in range(9):out.append((num[k]-sum((norm[j]*out[k-j] for j in range(1,k+1)),F()))/norm[0])
        return out
    assert quotient(4)==E
    assert quotient(3)[:8]==E[:8] and quotient(3)[8]!=E[8]
    return dict(exact_orders=9,negative_control_eighth_difference=str(quotient(3)[8]-E[8]))

def main():
    s=CircleSpace(4,8);rng=np.random.default_rng(39021)
    X=rng.normal(size=(1,s.n,2));X[:,~s.scalar]=0
    M,V=s.vertices(X,7,s.n,s.prefix(s.n));herm=0.
    for ops in (M,V):
        for j in range(8):herm=max(herm,abs(float(X[0,:,0]@ops[j,:,1]-X[0,:,1]@ops[j,:,0])))
    assert herm<1e-10,herm
    assert np.all(s.N[s.scalar]%2==0)
    P=diags(s.scalar.astype(float),format='csr');C=[P@c@P for c in s.C]
    wrong=s.vertices(X,0,s.n,(C,[c.T for c in C]))[1]
    difference=float(np.max(abs(wrong-V[:1])))
    assert difference>1e-2
    # Complete reference diagonals are invariant under cutoff and reorganization.
    q=np.zeros((1,s.n,4));q[0,s.refs,np.arange(4)]=1
    a,b=s.vertices(q,0,s.n,s.prefix(s.n))
    for p,i in enumerate(s.refs):
        assert abs(a[0,i,p]-2*p)<1e-12
        assert abs(b[0,i,p]-p*(p-1)/2)<1e-12
    result=dict(stationary_quotient=stationary(),max_vertex_hermiticity_error=herm,incorrect_intermediate_angular_projection_difference=difference,scalar_bath_levels_even=True,scope='Exact/independent implementation checks, not conformal Ward calibration.')
    (ROOT/'results/local_algebra_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
