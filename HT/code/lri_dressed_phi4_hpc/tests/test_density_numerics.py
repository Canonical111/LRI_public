"""Independent numerical tests of the opt-in span; no physical Ward target is fitted."""
import numpy as np
from scipy.linalg import block_diag
import pytest
from lri_dressed.density import FixedLocal,DensitySolver,select_density_basis,rotate_warm
from lri_dressed.local import LocalProblem
from lri_dressed.solver import DressedSolver


def span():
    s=DressedSolver(4,8,64,window='vacuum',backend='tensor');s.set_delta(.24)
    theta=s.initial(.04)
    _,_,u,info=s.local_problem.evaluate(.24,theta)
    return theta,u,info['local_scale']


def test_projected_operators_and_a0():
    theta,u,t=span()
    rng=np.random.default_rng(712)
    rotations=[np.linalg.qr(rng.normal(size=(8,4)))[0] for _ in (0,1)]
    u=u@block_diag(*rotations)
    loc=FixedLocal(u,t);base=LocalProblem(4,64)
    for j in range(1,5):
        assert np.allclose(loc.physq[j],u.T@(base.q[j]*t**j)@u,atol=2e-13,rtol=2e-14)
    # Noninvariance of the smaller span: powers of a projected q are wrong.
    assert np.linalg.norm(loc.physq[2]-loc.physq[1]@loc.physq[1])>1e-4
    w,L,U,info=loc.evaluate(.24,theta)
    c=np.diag(np.sqrt(np.arange(1,68)),k=-1)
    a=(t*(c+c.T)-(c-c.T)/t)/2
    assert np.max(abs(loc.a0(.24,theta)-U.T@a[:64,:64]@U))<2e-13
    wrong=(3*L[2]/info['g'])*(1-(w[:,None]-w[None,:])/.24)/2
    assert np.linalg.norm(wrong-loc.a0(.24,theta))>1e-5


@pytest.mark.parametrize('backend',['tensor','ladder'])
def test_same_span_matches_original_parent(backend):
    theta,u,t=span()
    old=DressedSolver(4,8,64,window='vacuum',backend=backend);old.set_delta(.24)
    new=DensitySolver(4,u,t,window='vacuum',backend=backend);new.set_delta(.24)
    a=old.spectrum(theta,k=5,diagnostics=True)
    b=new.spectrum(theta,k=5,diagnostics=True)
    for f in (0,1):assert np.max(abs(a[2][f][0]-b[2][f][0]))<3e-12
    assert np.max(abs(a[2]['window']['D']-b[2]['window']['D']))<3e-12


def test_fixed_span_window_jacobian():
    theta,u,t=span();s=DensitySolver(4,u[:,:],t,window='vacuum',backend='tensor');s.set_delta(.24)
    f,info,out,U=s.spectrum(theta,k=3)
    jac=s.response_jacobian(theta,out,U)
    for j in range(2):
        h=2e-6;step=np.eye(2)[j]*h
        fd=(s.spectrum(theta+step,k=3)[0]-s.spectrum(theta-step,k=3)[0])/(2*h)
        assert np.max(abs(fd-jac[:,j]))<2e-7


def test_warm_vectors_use_full_rotation():
    theta,u,t=span();s=DensitySolver(4,u,t,window='vacuum');s.set_delta(.24)
    _,_,old,_=s.prepare(theta)
    _,_,new,_=s.local_problem.evaluate(.24,theta+np.array([.03,.01]))
    vec=np.random.default_rng(912).normal(size=s.op.dim)
    result=rotate_warm(vec,s.op,1,old,new)
    assert abs(np.linalg.norm(result)-np.linalg.norm(vec))<1e-11
    x=vec.reshape(s.op.nB,s.nz);y=result.reshape(s.op.nB,s.nz)
    for p in (0,1):
        mask=(s.op.kpar^1)==p;ix=slice(p*s.nz,(p+1)*s.nz)
        assert np.max(abs(x[mask]@old[:,ix].T-y[mask]@new[:,ix].T))<3e-12


def test_density_targets_never_request_thermal(monkeypatch):
    s=DressedSolver(4,8,64,window='vacuum');s.set_delta(.24)
    theta=s.initial(.04);calls=[];original=s.sector_solve
    def wrapped(op,w,L,field,k,*a,**kw):
        calls.append((field,k));return original(op,w,L,field,k,*a,**kw)
    monkeypatch.setattr(s,'sector_solve',wrapped)
    u,t,meta=select_density_basis(s,theta,6)
    assert all(k==1 for f,k in calls if f==0)
    assert all(k==2 for f,k in calls if f==1)
    assert meta['thermal_target'] is False
    assert abs(sum(d['weight'] for d in meta['targets'])-1)<1e-15
    assert np.max(abs(u.T@u-np.eye(12)))<1e-12
    assert np.sum(np.asarray(meta['density_eigenvalues']))==pytest.approx(1,abs=1e-13)


def test_nonorthogonal_parity_and_scale_rejected():
    theta,u,t=span()
    bad=u.copy();bad[:,0]*=1.01
    with pytest.raises(ValueError):FixedLocal(bad,t)
    bad=u.copy();bad[:,0],bad[:,8]=u[:,8].copy(),u[:,0].copy()
    with pytest.raises(ValueError):FixedLocal(bad,t)
    with pytest.raises(ValueError):FixedLocal(u,float('nan'))
