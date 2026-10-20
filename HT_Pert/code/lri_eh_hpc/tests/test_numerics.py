import json
from pathlib import Path
import numpy as np
import pytest
from lri_eh.numerics import compute,vacuum_expectation
from lri_eh._core.solver import vacuum_quotient
from lri_eh._core.operators import Space

@pytest.mark.parametrize('degree',[4,5,6,7])
@pytest.mark.parametrize('cutoff',[4,8,12,20])
def test_direct_response_against_original(cutoff,degree):
    from run_correction_only import correction
    old=correction(cutoff,degree,3.5);new=compute(cutoff,degree,3.5)
    for key in ('delta_C','delta_r','delta_g'):
        np.testing.assert_allclose(new[key],old[key],rtol=2e-11,atol=1e-8)
    assert new['validation']['exact_delta_C4_residual']<1e-11

@pytest.mark.parametrize('cutoff',[4,6,8])
def test_against_full_independent_recursion(cutoff):
    from validate_full_vacuum import full
    from run_vacuum_matched import compute as legacy
    vac=full(cutoff,7);raw=legacy(cutoff,7,False,3.5,False);new=compute(cutoff,7,3.5)
    for key in ('C','r','g'):
        np.testing.assert_allclose(new['delta_'+key],np.array(vac[key])-raw[key],rtol=2e-11,atol=1e-8)


def test_thread_invariance_and_fused_diagonal():
    from numba import set_num_threads
    set_num_threads(1);a=compute(16,7,3.5)
    set_num_threads(4);b=compute(16,7,3.5)
    for key in ('delta_C','delta_r','delta_g'):np.testing.assert_array_equal(a[key],b[key])
    s=Space(8,11,8,3,memory_limit_gib=1)
    rng=np.random.default_rng(512);psi=rng.normal(size=(s.dim,4))
    np.testing.assert_allclose(vacuum_expectation(s,psi,5),vacuum_quotient(s,psi,5),rtol=2e-12,atol=2e-12)


def test_exact_plan_edges():
    from lri_eh.planner import plan
    for d in (4,5,6,7):
        p=plan(12,d);s=Space(12,p['particle_cap'],p['nonzero_particle_cap'],3)
        assert p['basis_dimension']==s.global_dim
        assert p['edges_per_orientation']==len(s.creation.index)==len(s.annihilation.index)
        assert p['exact_edge_bytes']==s.edges_bytes


def test_explicit_int64_index_path():
    from lri_eh._core.kernels import ladder
    s=Space(8,11,8,3);rng=np.random.default_rng(22);x=rng.normal(size=(s.dim,4));ghost=np.empty((0,4))
    for e in (s.creation,s.annihilation):
        a=ladder(e.ptr,e.index,e.mode,e.occ,s.weights,x,ghost,3,s.P,-1)
        b=ladder(e.ptr,e.index.astype(np.int64),e.mode,e.occ,s.weights,x,ghost,3,s.P,-1)
        np.testing.assert_array_equal(a,b)
    from lri_eh._core.basis import count_tables,unrank,rank_seq
    G,Z=count_tables(164,11,8)
    dimension=int(Z[11,8,4*164]);assert dimension>2**31
    for idx in (2**31-1,2**31,dimension-1):
        seq=np.zeros(12,np.int32);p,q,n=unrank(idx,G,Z,164,11,8,seq)
        assert rank_seq(seq,p,G,Z,164,11,8)==idx
