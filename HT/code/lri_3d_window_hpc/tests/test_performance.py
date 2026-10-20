"""Independent tests of exact algebraic optimizations, not physical Ward targets."""
from pathlib import Path
import sys,json,subprocess,os
import numpy as np
import pytest
from numba import set_num_threads
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'code'),str(R/'reference/d3original/code')]
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator,restrict_operator
from ht3d.local import LocalProblem
from ht3d.solver import DressedSolver
from ht3d.cache import ArrayCache,digest,COUNTERS
from d3dressed.basis import SphereBathBasis as OriginalBasis

@pytest.mark.parametrize('L,J',[(4,0),(4,1),(4,2),(6,0),(6,1),(6,2),(6,3),(8,0),(8,1),(8,2)])
def test_ranked_projectors_and_no_graph_mutation(L,J):
    b=SphereBathBasis.build(L);old=OriginalBasis.build(L)
    snapshots={name:getattr(b,name).copy() for name in ('N','P','M','ptr','parents','modes','sqocc','tree','last','counts')}
    S,N,P,k,test=b.highest_weight(J,J%2);S0,N0,P0,k0,_=old.highest_weight(J,J%2)
    np.testing.assert_array_equal(N,N0);np.testing.assert_array_equal(P,P0)
    np.testing.assert_allclose(S.toarray(),S0.toarray(),atol=2e-14,rtol=2e-14)
    op=ProductOperator(b,.6,6,J)
    for key,a in snapshots.items():np.testing.assert_array_equal(getattr(b,key),a)

@pytest.mark.parametrize('L,J,x',[(4,0,.5182),(4,1,.6),(4,2,.745),(6,0,.6),(6,1,.5182),(6,2,.6),(6,3,.745),(8,0,.5182),(8,1,.745),(8,2,.6)])
def test_rotational_trace_against_full_quadrature(L,J,x):
    b=SphereBathBasis.build(L)
    pole=ProductOperator(b,x,8,J);quad=ProductOperator(b,x,8,J,nodes=L+1)
    more=ProductOperator(b,x,8,J,nodes=L+4)
    for a,c,d in zip(pole.W,quad.W,more.W):
        np.testing.assert_allclose(a.toarray(),c.toarray(),atol=3e-12,rtol=5e-13)
        np.testing.assert_allclose(a.toarray(),d.toarray(),atol=3e-12,rtol=5e-13)
    w,V,_,_=LocalProblem(8,64).evaluate(x,[.4,-2.2])
    for f in (0,1):
        X=np.random.default_rng(13+f).normal(size=(pole.dim,3))
        a=pole.linear_operator(w,V,f)@X;c=quad.linear_operator(w,V,f)@X
        np.testing.assert_allclose(a,c,atol=8e-12,rtol=5e-13)

@pytest.mark.parametrize('top', [6,8,10])
def test_every_lower_cutoff_is_exact_and_independent(top):
    p=ProductOperator(SphereBathBasis.build(top),.6,8)
    for ell in range(2,top,2):
        a=restrict_operator(p,ell);b=ProductOperator(SphereBathBasis.build(ell),.6,8)
        np.testing.assert_array_equal(a.N,b.N);np.testing.assert_array_equal(a.P,b.P)
        for aa,bb in zip(a.W,b.W):np.testing.assert_allclose(aa.toarray(),bb.toarray(),atol=3e-12,rtol=5e-13)
        assert a.basis.cutoff==ell
        # No mutable shifts or sparse arrays may alias parent.
        for W in a.W:
            assert all(not np.shares_memory(W.data,V.data) for V in p.W)
        a.set_bath_shift(np.full(a.fullB,.17));np.testing.assert_array_equal(p.hb,p.hb0)
    with pytest.raises(ValueError):restrict_operator(p,top+1)

@pytest.mark.parametrize('mode',['consistent','literal'])
def test_window_hierarchy_matches_independent_original_spaces(mode):
    a=DressedSolver(6,8,64,window='vacuum',window_mode=mode,eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    b=DressedSolver(6,8,64,window='vacuum',window_mode=mode,eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    a.set_delta(.6);b.set_delta(.6)
    from ht3d.window import VacuumWindow
    b.win=VacuumWindow(6,8,.6,'tensor',mode,eig_tol=1e-12,ncv=40)
    for theta in ([.8,-2.15],[.801,-2.149]):
        fa,ia,oa,ua=a.spectrum(theta,k=3,diagnostics=True)
        fb,ib,ob,ub=b.spectrum(theta,k=3,diagnostics=True)
        np.testing.assert_allclose(fa,fb,atol=3e-11,rtol=2e-11)
        for f in (0,1):np.testing.assert_allclose(oa[f][0],ob[f][0],atol=3e-11,rtol=2e-11)
        np.testing.assert_allclose(oa['window']['D'],ob['window']['D'],atol=3e-11)

@pytest.mark.parametrize('J',[0,1,2])
def test_immutable_cache_replays_and_guards(tmp_path,J):
    b=SphereBathBasis.build(6,cache_dir=tmp_path);a=ProductOperator(b,.6,8,J)
    cc=SphereBathBasis.build(6,cache_dir=tmp_path);d=ProductOperator(cc,.6,12,J)
    assert isinstance(cc.N,np.memmap) and not cc.N.flags.writeable
    for aa,bb in zip(a.W,d.W):np.testing.assert_array_equal(aa.toarray(),bb.toarray())
    assert isinstance(d.W[0].data.base,np.ndarray)
    with pytest.raises(MemoryError):SphereBathBasis.build(6,cache_dir=tmp_path,max_states=1)
    cache=ArrayCache(tmp_path);path=cache.path('graph',{'L':6})/'N.npy'
    with path.open('r+b') as f:f.seek(-1,os.SEEK_END);b=f.read(1);f.seek(-1,os.SEEK_END);f.write(bytes([b[0]^1]))
    with pytest.raises(ValueError,match='Invalid immutable cache'):SphereBathBasis.build(6,cache_dir=tmp_path)


def test_cache_exact_x_and_method_binding(tmp_path):
    b=SphereBathBasis.build(4,cache_dir=tmp_path)
    a=ProductOperator(b,.6,8);q=ProductOperator(b,.6,8,nodes=5);c=ProductOperator(b,.6001,8)
    assert len(list(tmp_path.glob('vertices-*')))==3
    assert np.max(abs(a.W[1].toarray()-c.W[1].toarray()))>1e-6
    np.testing.assert_allclose(a.W[1].toarray(),q.W[1].toarray(),atol=2e-13)


def test_cache_concurrent_atomic_publication(tmp_path):
    script='''from ht3d.cache import ArrayCache\nimport numpy as np,sys\nc=ArrayCache(sys.argv[1]);c.save('toy',{'x':1},{'a':np.arange(1000.)});a,_=c.load('toy',{'x':1});assert np.array_equal(a['a'],np.arange(1000.))'''
    env=dict(os.environ,PYTHONPATH=str(R/'code'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    ps=[subprocess.Popen([sys.executable,'-c',script,str(tmp_path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    for p in ps:
        out,err=p.communicate(timeout=60);assert p.returncode==0,err.decode()
    assert len(list(tmp_path.glob('toy-*')))==1
    assert not list(tmp_path.glob('.ht3d-building-*'))


def test_parallel_action_preserves_tolerance():
    b=SphereBathBasis.build(12);p=ProductOperator(b,.6,8)
    w,V,_,_=LocalProblem(8,64).evaluate(.6,[.3,-2.2]);v=np.random.default_rng(2).normal(size=p.dim)
    try:
        for f in (0,1):
            set_num_threads(1);a=p.apply(v,w,V,f)
            set_num_threads(4);c=p.apply(v,w,V,f)
            np.testing.assert_allclose(a,c,atol=3e-12,rtol=5e-13)
    finally:set_num_threads(1)

@pytest.mark.parametrize('window',['none','vacuum'])
def test_calibration_only_roots_preserve_targets_and_jacobian(window):
    a=DressedSolver(6,8,64,window=window,eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    b=DressedSolver(6,8,64,window=window,eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    a.set_delta(.6);b.set_delta(.6)
    theta=np.array([.8,-2.15])
    f,i,o,u=a.spectrum(theta,k=(1,2),diagnostics=True)
    ff,ii,oo,uu=b.spectrum(theta,k=3,diagnostics=True)
    assert len(o[0][0])==1 and len(o[1][0])==2
    np.testing.assert_allclose(f,ff,atol=2e-12,rtol=2e-12)
    np.testing.assert_allclose(a.response_jacobian(theta,o,u),b.response_jacobian(theta,oo,uu),atol=2e-10,rtol=2e-10)
    f,i,o,u=a.spectrum(theta,k=5,diagnostics=True)
    assert len(o[0][0])==5 and len(o[1][0])==5
    assert i['max_eigenvector_residual']<1e-8


def test_cached_vertices_are_bound_to_projector_gauge(tmp_path):
    b=SphereBathBasis.build(4,cache_dir=tmp_path);a=ProductOperator(b,.6,8)
    S,N,P,keep,meta=b.highest_weight(0,0)
    S=S.copy();sign=np.ones(S.shape[1]);sign[-1]=-1;S=S.multiply(sign).tocsr()
    b._projectors[(0,0)]=(S,N,P,keep,meta)
    c=ProductOperator(b,.6,8)
    assert len(list(tmp_path.glob('vertices-*')))==2
    for W,V in zip(a.W,c.W):np.testing.assert_allclose(V.toarray(),sign[:,None]*W.toarray()*sign[None,:],atol=1e-13)


def test_cache_cli_manifest_restart_and_preparation(tmp_path):
    # Separate real consuming processes; no mocked numerical solver.
    env=dict(os.environ,NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    cache=tmp_path/'cache'
    subprocess.run([sys.executable,str(R/'scripts/prepare_cache.py'),'--L','4','--x','.6','--spins','0','1',
                   '--cache-dir',str(cache),'--threads','1'],check=True,env=env,stdout=subprocess.PIPE)
    output=tmp_path/'point.json'
    argv=['--L','4','--x','.6','--nz','12','--osc','96','--window','vacuum','--diagnostics','first',
          '--threads','1','--cache-dir',str(cache),'--output',str(output),'--resume']
    request=tmp_path/'request.json';request.write_text(json.dumps([argv]));manifest=tmp_path/'frozen.json'
    subprocess.run([sys.executable,str(R/'cluster/make_manifest.py'),'--request-list',str(request),'--output',str(manifest)],check=True,env=env,stdout=subprocess.PIPE)
    command=[sys.executable,str(R/'cluster/run_item.py'),'--manifest',str(manifest),'--index','0']
    subprocess.run(command,check=True,env=env,stdout=subprocess.PIPE)
    original=output.read_bytes();row=json.loads(original)
    assert row['static_cache_counters']['hits']>=3 and row['accepted']
    subprocess.run(command,check=True,env=env,stdout=subprocess.PIPE)
    assert output.read_bytes()==original and not Path(str(output)+'.claim').exists()
