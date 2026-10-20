import math,json
from pathlib import Path
import numpy as np
import pytest
from scipy.sparse import kron,csr_matrix,diags
from dressed_zero import DressedZero,partitions_upto
from fast_response import FastDressedZero
from lri_dressed.basis import BathBasis,count_table,_decode,_rank
from lri_dressed.local import LocalProblem
from lri_dressed.operators import ProductOperator
from lri_dressed.solver import DressedSolver
from lri_dressed.planning import plan
from numba import set_num_threads

@pytest.mark.parametrize('N',[2,4,6,8,10,12])
def test_exact_rank_and_counts(N):
    states=partitions_upto(N);b=BathBasis.build(N);c=count_table(N)
    assert len(states)==len(b.N)==int(c[N,1])
    for i,state in enumerate(states):
        occ=_decode(i,N,c)
        got=tuple(k for k in range(1,N+1) for _ in range(occ[k]))
        assert state==got;assert _rank(occ,N,c)==i
    np.testing.assert_array_equal(b.N,[sum(s) for s in states])
    np.testing.assert_array_equal(b.P,[len(s) for s in states])
    p=plan(N,4,32)
    assert p['creation_edges_exact']==len(b.col)
    assert p['bath_states_reflection_even']==sum(b.N%2==0)


def old_matrix(ref,w,L):
    H=kron(diags(w),ref.Ib)+kron(ref.Iz,ref.Hb)
    for j in range(4):H+=kron(csr_matrix(L[j]),ref.W[j+1])
    return H.tocsr()

def permutation(ref,field):
    return np.array([(field^int(ref.P[i]%2))*ref.nz*ref.nB+a*ref.nB+k for k,i in enumerate(ref.keep) for a in range(ref.nz)])

@pytest.mark.parametrize('reflection',[0,1])
@pytest.mark.parametrize('delta',[.23,.1,.01])
def test_tensor_ladder_operators_and_densities(reflection,delta):
    N=8;z=6;osc=64
    ref=DressedZero(N,z,osc,reflection=reflection);ref.set_delta(delta)
    b=BathBasis.build(N);col_before=b.col.copy()
    w,L,U,info=LocalProblem(z,osc).evaluate(delta,ref.initial(1-4*delta))
    H=old_matrix(ref,w,L);rng=np.random.default_rng(377)
    for backend in ('tensor','ladder','tensor'):
        op=ProductOperator(b,delta,z,reflection,backend)
        for f in (0,1):
            p=permutation(ref,f);x=rng.normal(size=op.dim);x/=np.linalg.norm(x)
            full=np.zeros(H.shape[0]);full[p]=x;exact=(H@full)[p]
            y=op.apply(x,w,L,f)
            np.testing.assert_allclose(y,exact,atol=3e-12,rtol=2e-12)
            weights,corr,bath=op.contractions(x,f)
            np.testing.assert_allclose(weights@w+np.sum(corr*L)+bath,x@exact,rtol=2e-12,atol=3e-12)
            v=rng.normal(size=op.dim)
            assert abs(v@y-x@op.apply(v,w,L,f))<1e-10
    np.testing.assert_array_equal(b.col,col_before)  # sorting a CSR must not mutate rank-edge metadata

@pytest.mark.parametrize('backend',['tensor','ladder'])
def test_jacobian_moving_basis(backend):
    N=8;z=6;osc=64;delta=.1
    ref=FastDressedZero(N,z,osc);ref.set_delta(delta)
    opt=DressedSolver(N,z,osc,backend=backend);opt.set_delta(delta)
    theta=ref.initial(.6);res,info,out,U=opt.spectrum(theta,k=3)
    old={}
    for f in (0,1):
        perm=np.searchsorted(ref.ix[f],permutation(ref,f))
        vv=np.zeros_like(out[f][1]);vv[perm]=out[f][1];old[f]=(out[f][0],vv)
    want=ref.response_jacobian(theta,old,U)
    got=opt.response_jacobian(theta,out,U)
    np.testing.assert_allclose(got,want,rtol=2e-7,atol=2e-8)
    spectral=np.empty((2,2))
    for j in range(2):
        h=1e-5*max(1,abs(theta[j]));a=theta.copy();b=theta.copy();a[j]+=h;b[j]-=h
        spectral[:,j]=(opt.spectrum(a,k=3)[0]-opt.spectrum(b,k=3)[0])/(2*h)
    np.testing.assert_allclose(got,spectral,rtol=2e-7,atol=2e-8)

@pytest.mark.parametrize('delta',[.24,.1,.01])
def test_full_tuning_against_reference(delta):
    root=Path(__file__).resolve().parents[1]
    seed=json.loads((root/f'inputs/N16_z24_o192_d{delta:.8f}.json').read_text())['theta']
    ref=FastDressedZero(8,8,80);ref.set_delta(delta);want=ref.solve(seed)
    for backend in ('tensor','ladder'):
        opt=DressedSolver(8,8,80,backend=backend);opt.set_delta(delta);got=opt.solve(seed)
        for k in ('Delta_thermal','Delta_sigma_measured','Delta_shadow_measured','r','g'):
            np.testing.assert_allclose(got[k],want[k],rtol=2e-9,atol=2e-9)
        np.testing.assert_allclose(got['even_gaps'],want['even_gaps'],rtol=2e-9,atol=2e-9)
        assert got['max_eigenvector_residual']<2e-7

@pytest.mark.parametrize('backend',['tensor','ladder'])
def test_threads_and_int64_path(backend):
    b=BathBasis.build(8);d=.1;z=6
    ref=DressedSolver(8,z,64,backend=backend,basis=b);ref.set_delta(d)
    w,L,U,info=ref.local_problem.evaluate(d,ref.initial(.6))
    x=np.random.default_rng(12).normal(size=ref.op.dim)
    set_num_threads(1);y=ref.op.apply(x,w,L,0)
    set_num_threads(4);z4=ref.op.apply(x,w,L,0);np.testing.assert_array_equal(y,z4)
    set_num_threads(1)
    b.col=b.col.astype(np.int64);op=ProductOperator(b,d,z,0,backend)
    for a in [op.B,op.C]+list(op.W or []):
        a.indices=a.indices.astype(np.int64);a.indptr=a.indptr.astype(np.int64)
    if op.W is not None:
        op.ptrs=tuple(a.indptr for a in op.W);op.cols=tuple(a.indices for a in op.W)
    np.testing.assert_allclose(op.apply(x,w,L,0),y,atol=1e-12,rtol=1e-12)


def test_invalid_parameters():
    with pytest.raises(ValueError):DressedSolver(1,4,32)
    with pytest.raises(ValueError):DressedSolver(4,4,15)
    h=DressedSolver(4,4,32)
    for d in (0,.25,-1,float('nan')):
        with pytest.raises(ValueError):h.set_delta(d)
