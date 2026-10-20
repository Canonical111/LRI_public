from pathlib import Path
import sys,math,json
import numpy as np
import pytest
from scipy.sparse import csr_matrix,diags,eye,kron
from scipy.linalg import eigh
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'upstream'))
from ht2d.basis import CircleBathBasis
from ht2d.operators import ProductOperator,normal_power
from ht2d.solver import DressedSolver
from ht2d.density import DensitySolver,select_density_basis,FixedLocal
from ht2d.window import converged,FIXED_POINT_CEILING
from d2dressed.solver import DressedSolver as Original
from d2dressed.operators import ProductOperator as OriginalOperator
METRICS={}

@pytest.mark.parametrize('J',[0,1,2,-1])
def test_circle_vertices(J):
    b=CircleBathBasis.build(4);new=ProductOperator(b,.3,6,J,'tensor');old=OriginalOperator(b,.3,6,J,'tensor')
    err=max(np.max(abs((a-c).toarray())) for a,c in zip(new.W,old.W))
    METRICS[f'original_vertex_J{J}']=float(err);assert err<2e-13
    # Explicit finite Fourier average of full complete vertices, independently.
    S=new.S
    if S is None:S=csr_matrix((np.ones(new.nB),(new.keep,np.arange(new.nB))),shape=(new.fullB,new.nB))
    maxerr=0.
    for k in range(1,5):
        W=normal_power(new.B,k).tocoo();angular=np.zeros(W.shape,dtype=complex)
        for m in range(9):
            v=W.data*np.exp(2j*np.pi*m/9*(b.J[W.row]-b.J[W.col]))/9
            np.add.at(angular,(W.row,W.col),v)
        maxerr=max(maxerr,float(np.max(abs(S.T@angular@S-new.W[k-1].toarray()))))
    assert maxerr<2e-13;METRICS[f'Fourier_J{J}']=maxerr

@pytest.mark.parametrize('x',[.495,.3,.126])
def test_raw_spectra_replay(x):
    a=DressedSolver(4,8,64,window='none',eig_tol=1e-12);a.set_delta(x)
    b=Original(4,8,64,eig_tol=1e-12);b.set_delta(x);th=b.initial(2-4*x)
    av=a.spectrum(th,k=5)[2];bv=b.spectrum(th,k=5)[2]
    err=max(np.max(abs(av[f][0]-bv[f][0])) for f in (0,1))
    METRICS[f'raw_replay_{x}']=float(err);assert err<2e-11

@pytest.mark.parametrize('J',[0,1,2])
def test_backend_window_actions(J):
    b=CircleBathBasis.build(4)
    s=DressedSolver(4,6,64);s.set_delta(.3);w,L,_,_=s.local_problem.evaluate(.3,s.initial(.8))
    a=ProductOperator(b,.3,6,J,'tensor');c=ProductOperator(b,.3,6,J,'ladder')
    D=-.031*b.N; a.set_bath_shift(D);c.set_bath_shift(D)
    rng=np.random.default_rng(37)
    for f in (0,1):
        v=rng.normal(size=a.dim);u=rng.normal(size=a.dim)
        assert np.max(abs(a.apply(v,w,L,f)-c.apply(v,w,L,f)))<2e-11
        assert abs(u@a.apply(v,w,L,f)-v@a.apply(u,w,L,f))<3e-10
        assert abs(a.level_weights(v).sum()-v@v)<1e-11


def test_normal_ordering():
    s=DressedSolver(4,6,64);s.set_delta(.3);th=s.initial(.8)
    w,L,U,info=s.local_problem.evaluate(.3,th);t=info['local_scale'];x=.3;r=info['r'];g=info['g']
    lp=s.local_problem;I=np.eye(lp.osc);q=[t**j*lp.q[j] for j in range(5)];pp=lp.pp/t**2
    H=x/4*(pp+q[2]-2*I)+r*(q[2]-I)+g/12*(q[4]-6*q[2]+3*I)
    Z=U.T@H@U;Z-=Z[0,0]*np.eye(2*s.nz)
    Qs=[U.T@(2*r*q[1]+g*(q[3]-3*q[1])/3)@U,
        U.T@(r*I+g*(q[2]-I)/2)@U, U.T@(g*q[1]/3)@U, g/12*np.eye(2*s.nz)]
    assert np.max(abs(Z-np.diag(w)))<2e-11
    assert np.max(abs(np.array(Qs)-L))<2e-11


def test_window_fixedpoint_dense_and_derivative():
    s=DressedSolver(4,10,80,window='vacuum',eig_tol=1e-13);s.set_delta(.3)
    sol=s.solve(tol=1e-11);th=np.array(sol['theta']);_,info,out,U=s.spectrum(th,k=5,diagnostics=True)
    win=out['window'];w,L,_,_=s.local_problem.evaluate(.3,th)
    # Direct dense spectra, using independently constructed per-row windows.
    errs=[]
    for lev in [2,4]:
        op=s.win.ops.get(lev,s.op);ss=win['Ev'][lev]
        shift=np.array([ss-win['Ev'][max(0,lev-int(n)-(int(n)%2))] if n else 0 for n in op.basis.N])
        # Here lev even, even_floor(lev-n) = lev-n-(n%2).
        op.set_bath_shift(shift);H=op.linear_operator(w,L,0)@np.eye(op.dim)
        errs.append(abs(eigh(H,eigvals_only=True)[0]-ss))
    assert max(errs)<1e-11;METRICS['window_dense']=float(max(errs))
    jac=s.response_jacobian(th,out,U);fd=np.empty((2,2))
    for j in (0,1):
        h=1e-5;tp=th.copy();tm=th.copy();tp[j]+=h;tm[j]-=h
        fd[:,j]=(s.spectrum(tp,k=3)[0]-s.spectrum(tm,k=3)[0])/(2*h)
    err=np.max(abs(fd-jac));METRICS['moving_window_jacobian']=float(err);assert err<3e-6
    assert not converged(2e-11,1e10,1e-12)


def test_density_full_window_and_jacobian():
    s=DressedSolver(4,16,128,window='vacuum',eig_tol=1e-13);s.set_delta(.3)
    r=s.solve(tol=1e-11);u,t,meta=select_density_basis(s,r['theta'],10)
    assert not meta['thermal_target'];assert abs(sum(z['weight'] for z in meta['targets'])-1)<1e-14
    d=DensitySolver(4,u,t,window='vacuum',eig_tol=1e-13);d.set_delta(.3)
    th=np.array(r['theta']);_,info,out,U=d.spectrum(th,k=3)
    jac=d.response_jacobian(th,out,U);fd=np.empty((2,2))
    for j in (0,1):
        h=1e-5;tp=th.copy();tm=th.copy();tp[j]+=h;tm[j]-=h
        fd[:,j]=(d.spectrum(tp,k=3)[0]-d.spectrum(tm,k=3)[0])/(2*h)
    err=np.max(abs(fd-jac));METRICS['density_window_jacobian']=float(err);assert err<1e-6
    dr=d.solve(r['theta'],tol=1e-11)
    METRICS['compressed_thermal_gap']=abs(dr['Delta_thermal']-r['Delta_thermal'])
    assert METRICS['compressed_thermal_gap']<1e-7
    assert dr['tuning_residual']<1e-10


def test_free_window_zero():
    s=DressedSolver(4,8,64,window='vacuum');s.set_delta(.4)
    w,X,U,t,res,edge=s.local_problem.local(.4,.1,0.)
    out={};state,info=s.window_spectrum(w,np.zeros((4,16,16)),4,out)
    assert max(abs(v) for v in state['Ev'].values())<1e-12
    assert max(abs(state['D']))<1e-12


def test_parameter_contracts():
    with pytest.raises(ValueError):DressedSolver(5,window='vacuum')
    with pytest.raises(ValueError):DressedSolver(4,angular=1,window='vacuum')
    with pytest.raises(ValueError):FixedLocal(np.ones((64,12)),1.)


def test_z_write_metrics():
    (ROOT/'validation/independent_metrics.json').write_text(json.dumps(METRICS,indent=2)+'\n')
