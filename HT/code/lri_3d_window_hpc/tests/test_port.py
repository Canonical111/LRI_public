from pathlib import Path
import sys,math,json
import numpy as np
import pytest
from scipy.linalg import eigh
from scipy.optimize import brentq
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'code'),str(R/'reference/d3original/code')]
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.local import LocalProblem
from ht3d.solver import DressedSolver
from ht3d.density import DensitySolver,select_density_basis
from d3dressed.basis import SphereBathBasis as OriginalBasis
from d3dressed.operators import ProductOperator as OriginalOperator

@pytest.mark.parametrize('L',[0,2,4,6,8])
def test_ranked(L):
    b=SphereBathBasis.build(L);old=OriginalBasis.build(L)
    assert b.labels==old.labels
    assert list(b.states)==old.states
    for new,ref in [(b.N,old.N),(b.P,old.P),(b.M,old.M),(b.ptr,old.ptr),(b.parents,old.parents),(b.modes,old.modes),(b.sqocc,old.sqocc)]:
        np.testing.assert_array_equal(new,ref)
    for i in range(len(b.N)):assert b.rank(b.states[i])==i

@pytest.mark.parametrize('J',[0,1,2])
@pytest.mark.parametrize('x',[.55,.745])
def test_projected_operators(J,x):
    b=SphereBathBasis.build(4);old=OriginalBasis.build(4)
    a=ProductOperator(b,x,6,J,'tensor');g=ProductOperator(b,x,6,J,'gram');r=OriginalOperator(old,x,6,J)
    # Work in the same physical angular basis, allowing a gauge rotation.
    gauge=r.S.T@a.S
    for aa,rr in zip(a.W,r.W):np.testing.assert_allclose(aa.toarray(),(gauge.T@rr@gauge).toarray(),atol=2e-13,rtol=2e-13)
    w,V,U,info=LocalProblem(6,64).evaluate(x,[.2,-2.2])
    for f in [0,1]:
        X=np.random.default_rng(78+f).normal(size=(a.dim,3))
        np.testing.assert_allclose(a.linear_operator(w,V,f)@X,g.linear_operator(w,V,f)@X,atol=2e-12,rtol=2e-13)
        np.testing.assert_allclose(a.apply(X[:,0],w,V,f),a.linear_operator(w,V,f)@X[:,0],atol=1e-13)
    # more angular nodes should not alter any retained normal-ordered matrix element.
    extra=ProductOperator(b,x,6,J,'tensor',nodes=8)
    for aa,bb in zip(a.W,extra.W):np.testing.assert_allclose(aa.toarray(),bb.toarray(),atol=3e-13,rtol=2e-13)

def test_free_normalization():
    from ht3d.diagnostics import projected_translation,zero_m_projector
    b=SphereBathBasis.build(4);x=.6;a=ProductOperator(b,x,6,0);c=ProductOperator(b,x,6,1)
    W,Z=projected_translation(c,a)
    z=Z[:,0].toarray().ravel();assert abs(z@z-2*x)<1e-13
    S=zero_m_projector(c);np.testing.assert_allclose((S.T@S).toarray(),np.eye(c.nB),atol=2e-14)
    w,V,U,info=LocalProblem(6,64).evaluate(x,[.2,-2.2])
    # all spherical vertex diagonals for a bath vacuum are zero
    for v in a.W:assert abs(v[0,0])<1e-14

def teacher(x=.6):
    old=json.loads((R/f'reference/d3original/results/L4/L4_z16_o128_x{x:.8f}.json').read_text())
    s=DressedSolver(4,12,96,window='vacuum',eig_tol=1e-12,residual_tol=1e-8,ncv=32)
    s.set_delta(x);row=s.solve(old['theta'],tol=2e-11);return s,row

def test_dense_fixed_point_and_derivative():
    s,row=teacher();theta=np.array(row['theta']);f,info,out,U=s.spectrum(theta,k=3)
    w,V,_,_=s.local_problem.evaluate(s.delta,theta)
    # independent direct dense eigenvalues, root bracketing instead of Newton.
    E={0:0.}
    for ell,op in [(2,s.win.ops[2]),(4,s.op)]:
        op.set_bath_shift(None);H=op.linear_operator(w,V,0)@np.eye(op.dim)
        def F(z):
            D=np.array([0. if n==0 else z-E[(ell-int(n))//2*2] for n in op.levels])
            A=H.copy();A.flat[::len(A)+1]+=np.repeat(D,op.nz)
            return eigh(A,subset_by_index=(0,0),eigvals_only=True,check_finite=False)[0]-z
        lo,hi=-10.,10.
        for _ in range(20):
            if F(lo)*F(hi)<0:break
            lo*=2;hi*=2
        E[ell]=brentq(F,lo,hi,xtol=1e-13)
        assert abs(E[ell]-out['window']['Ev'][ell])<2e-11
    # restore main window by forcing a fresh spectrum
    s._window_cache=None
    f,info,out,U=s.spectrum(theta,k=3)
    J=s.response_jacobian(theta,out,U)
    for j in range(2):
        d=np.zeros(2);d[j]=1e-5
        num=(s.spectrum(theta+d,k=3)[0]-s.spectrum(theta-d,k=3)[0])/(2e-5)
        np.testing.assert_allclose(J[:,j],num,atol=2e-7,rtol=2e-7)

def test_density_jacobian_training_holdout():
    s,row=teacher();u,t,meta=select_density_basis(s,row['theta'],8)
    assert not meta['thermal_target'];assert all('thermal' not in e['name'] for e in meta['targets'])
    d=DensitySolver(4,u,t,window='vacuum',eig_tol=1e-12,residual_tol=1e-8,ncv=32);d.set_delta(.6)
    rr=d.solve(row['theta'],tol=2e-11)
    assert abs(rr['Delta_thermal']-row['Delta_thermal'])<1e-8
    th=np.array(rr['theta']);f,info,out,U=d.spectrum(th,k=3);J=d.response_jacobian(th,out,U)
    for j in range(2):
        dt=np.zeros(2);dt[j]=1e-5
        num=(d.spectrum(th+dt,k=3)[0]-d.spectrum(th-dt,k=3)[0])/(2e-5)
        np.testing.assert_allclose(J[:,j],num,atol=2e-7,rtol=2e-7)
    # exact cache unchanged; altered local matrix must invalidate.
    d.spectrum(th,k=3);hits=d.window_cache_hits;d.spectrum(th,k=5);assert d.window_cache_hits>hits

@pytest.mark.parametrize('x',[.745,.6,.5182])
def test_raw_reference(x):
    d=json.loads((R/f'reference/d3original/results/L6/L6_z20_o160_x{x:.8f}.json').read_text())
    s=DressedSolver(6,20,160,eig_tol=1e-12,residual_tol=1e-8);s.set_delta(x)
    f,info,out,U=s.spectrum(d['theta'],k=5,diagnostics=True)
    for field,key in [(0,'even_gaps'),(1,'odd_gaps')]:np.testing.assert_allclose(out[field][0]-out[0][0][0],d[key],atol=3e-10,rtol=0)

@pytest.mark.parametrize('x',[.745,.6])
def test_boundary_guard(x):
    b=SphereBathBasis.build(2)
    with pytest.raises(ValueError):ProductOperator(b,x,6,nodes=2)
    with pytest.raises(MemoryError):SphereBathBasis.build(8,max_states=10)
    with pytest.raises(ValueError):b.weights(.5)
    with pytest.raises(ValueError):DressedSolver(3,6,64,window='vacuum')

@pytest.mark.parametrize('particles',[1,2,3])
def test_free_descendant_norms(particles):
    from ht3d.diagnostics import projected_translation,tensor_cross
    x=.6;z=6;b=SphereBathBasis.build(4)
    ops={j:ProductOperator(b,x,z,j) for j in [0,1,2]}
    af=np.diag(np.sqrt(np.arange(1,2*z)),1);ix=list(range(0,2*z,2))+list(range(1,2*z,2));a0=af[np.ix_(ix,ix)]
    v=np.zeros(ops[0].dim);f=particles%2;v[particles//2]=1
    def tr(v,jo,ji):
        W,Z=projected_translation(ops[jo],ops[ji])
        return tensor_cross(W,np.eye(2*z),v,ops[jo],ops[ji],f)+tensor_cross(Z,a0,v,ops[jo],ops[ji],f)
    v1=tr(v,1,0);trace=3*tr(v1,0,1);D=particles*x
    assert abs(v1@v1-2*D)<1e-12
    assert abs(trace@trace-24*D*(D-.5))<5e-12
