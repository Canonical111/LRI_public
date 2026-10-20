from pathlib import Path
import sys,importlib.util,json,math
import numpy as np
import pytest
from numba import set_num_threads,get_num_threads
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'upstream'))
from ht2d.basis import CircleBathBasis,dimension
from ht2d.operators import ProductOperator
from ht2d.solver import DressedSolver
from ht2d.density import DensitySolver,select_density_basis
from ht2d.diagnostics import projected_translation,translation_parts,projector,diagnose
from d2dressed.operators import ProductOperator as OldOperator


def old_basis():
 spec=importlib.util.spec_from_file_location('port_basis_oracle',ROOT/'reference/code/ht2d/basis.py')
 m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m.CircleBathBasis


@pytest.mark.parametrize('L',[0,1,2,4,6,8,10])
def test_ranked_basis_exact(L):
 a=CircleBathBasis.build(L);b=old_basis().build(L)
 for name in ('N','P','J','indptr','parent','mode','sqocc'):
  assert np.array_equal(getattr(a,name),getattr(b,name))
 assert list(a.states)==b.states
 for i in np.linspace(0,len(a.N)-1,min(51,len(a.N)),dtype=int):
  assert a.rank(a.states[i])==i
  swap={k:a.labels.index((bb,aa)) for k,(aa,bb) in enumerate(a.labels)}
  assert a.states[a.mirror[i]]==tuple(sorted(swap[k] for k in a.states[i]))


def test_resource_guards_and_rank_validation():
 with pytest.raises(MemoryError):CircleBathBasis.build(16,max_states=3)
 with pytest.raises(MemoryError):CircleBathBasis.build(16,max_bytes=64)
 b=CircleBathBasis.build(4)
 for v in [(-1,),(2,0),(500,), (0,)*5]:
  with pytest.raises(ValueError):b.rank(v)
 assert dimension(18)==477988
 assert not isinstance(b.states,list)


@pytest.mark.parametrize('J',[-1,0,1,2])
@pytest.mark.parametrize('x',[.126,.495])
def test_gram_all_normal_products_and_fields(J,x):
 b=CircleBathBasis.build(6);g=ProductOperator(b,x,8,J,'gram');old=OldOperator(b,x,8,J,'tensor')
 s=DressedSolver(6,8,80,window='none');s.set_delta(x)
 w,L,_,_=s.local_problem.evaluate(x,s.initial(2-4*x))
 rng=np.random.default_rng(128+J);v=rng.normal(size=g.dim);block=rng.normal(size=(g.dim,3))
 for a,y in zip(g.bath_powers(v.reshape(g.nB,8)),old.bath_powers(v.reshape(g.nB,8))):
  assert np.max(abs(a-y))<2e-12
 D=-.07*b.N;g.set_bath_shift(D);old.hb=old.hb+.0 if not hasattr(old,'set_bath_shift') else old.hb
 # Original d2dressed class has no setter, but reads hb directly.
 old.hb=old.hb0+D if hasattr(old,'hb0') else b.N+x*b.P+D
 for f in (0,1):
  np.testing.assert_allclose(g.apply(v,w,L,f),old.apply(v,w,L,f),rtol=5e-14,atol=2e-11)
  mat=g.apply_block(block,w,L,f)
  each=np.column_stack([g.apply(block[:,k],w,L,f) for k in range(3)])
  np.testing.assert_allclose(mat,each,rtol=5e-14,atol=2e-11)
  np.testing.assert_allclose(g.contractions(v,f)[0],old.contractions(v,f)[0],rtol=5e-14,atol=2e-12)


@pytest.mark.parametrize('Jout,Jin',[(1,0),(2,1),(0,1),(-1,0)])
def test_projected_translation_matches_full(Jout,Jin):
 b=CircleBathBasis.build(6);a=ProductOperator(b,.25,8,Jout,'gram');c=ProductOperator(b,.25,8,Jin,'gram')
 side=0 if Jout>Jin else 1
 direct=projected_translation(a,c,side);full=translation_parts(b,.25,side)
 for u,v in zip(direct,full):
  err=u-projector(a).T@v@projector(c)
  assert np.max(abs(err.data),initial=0)<2e-14


@pytest.mark.parametrize('mode',['consistent','literal'])
def test_exact_cache_invalidates_and_dense_shifts(mode):
 s=DressedSolver(6,8,80,window='vacuum',window_mode=mode,backend='gram',eig_tol=1e-13)
 s.set_delta(.3);theta=s.initial(.8)
 _,_,out,_=s.spectrum(theta,k=3);hits=s.window_cache_hits
 _,_,other,_=s.spectrum(theta,k=5,diagnostics=True)
 assert s.window_cache_hits==hits+1
 assert np.allclose(out[0][0],other[0][0][:3],atol=2e-12,rtol=0)
 th=theta.copy();th[0]+=1e-4
 s.spectrum(th,k=3);assert s.window_cache_hits==hits+1
 # Change shifts at exactly fixed w,L: the dense cache must NOT freeze the bath.
 op=s.win.ops[2];w,L,_,_=s.local_problem.evaluate(.3,theta)
 op.set_bath_shift(None);e,_,_,_=s.sector_solve(op,w,L,0,3)
 op.set_bath_shift(.031*op.basis.N);f,_,_,_=s.sector_solve(op,w,L,0,3)
 dense=op.linear_operator(w,L,0)@np.eye(op.dim)
 assert not np.allclose(e,f)
 np.testing.assert_allclose(f,np.linalg.eigvalsh(dense)[:3],rtol=0,atol=2e-12)


@pytest.mark.parametrize('x',[.495,.3,.126])
def test_gram_tensor_full_window_retuning(x):
 rows=[]
 for backend in ['tensor','gram','ladder']:
  s=DressedSolver(6,16,128,backend=backend,window='vacuum',eig_tol=1e-12,residual_tol=1e-8,ncv=40);s.set_delta(x)
  teacher=json.loads((ROOT/'reference/results'/f'teacher_L6_x{x:.3f}.json').read_text())
  rows.append(s.solve(teacher['theta'],tol=3e-11,maxiter=50))
 for r in rows[1:]:
  for key in ['theta','even_gaps','odd_gaps']:
   np.testing.assert_allclose(r[key],rows[0][key],rtol=0,atol=3e-9)
  assert r['tuning_residual']<1e-10


def test_gram_parallel_consistency():
 b=CircleBathBasis.build(12);s=DressedSolver(12,16,192,basis=b,backend='gram');s.set_delta(.25)
 w,L,_,_=s.local_problem.evaluate(.25,s.initial(1.))
 x=np.random.default_rng(91).normal(size=(s.op.dim,6))
 n=get_num_threads()
 try:
  set_num_threads(1);a=s.op.apply_block(x,w,L,0)
  set_num_threads(4);c=s.op.apply_block(x,w,L,0)
  np.testing.assert_allclose(c,a,rtol=3e-14,atol=1e-11)
 finally:set_num_threads(n)

@pytest.mark.parametrize('shape',[(19,7),(7,19),(4,31)])
def test_parallel_rectangular_csr(shape):
    from scipy.sparse import random as sparse_random
    from ht2d.kernels import csr_batch,csr_serial
    a=sparse_random(*shape,density=.6,format='csr',random_state=123)
    x=np.random.default_rng(12).normal(size=(shape[1],9))
    for f in (csr_batch,csr_serial):
        y=f(a.indptr,a.indices,a.data,x)
        assert y.shape==(shape[0],9)
        np.testing.assert_allclose(y,a@x,rtol=2e-15,atol=2e-15)


def test_resource_limits_forwarded_to_vacuum_levels(monkeypatch):
    import ht2d.window as win
    original=CircleBathBasis.build
    seen=[]
    def tracked(cutoff,**kwargs):
        seen.append(kwargs.copy());return original(cutoff,**kwargs)
    b=original(6)
    monkeypatch.setattr(win.BathBasis,'build',tracked)
    s=DressedSolver(6,8,80,basis=b,window='vacuum',max_bath_states=123456,max_basis_bytes=123456789)
    s.set_delta(.3)
    assert len(seen)==2
    assert all(d['max_states']==123456 and d['max_bytes']==123456789 for d in seen)
