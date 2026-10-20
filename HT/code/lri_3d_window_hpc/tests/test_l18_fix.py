"""Fallback, exact representation count, large index and provenance regressions."""
from pathlib import Path
from unittest.mock import patch
import sys, json
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from numba import set_num_threads
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from ht3d import basis
from ht3d.projector_preflight import census,symmetric_character,species_jplus
from ht3d.operators import ProductOperator
from ht3d.kernels import csr_batch,csr_serial


def kernel(A):
    st=basis._new_projector_stats(0,0)
    Q=basis._highest_weight_kernel(np.asarray(A,np.float64),{'L':4,'spin':0,'N':4},st)
    return Q,st


def test_default_nullspace_bit_equality():
    A=np.array([[1.,2.,3.],[3.,4.,6.]])
    Q,_=kernel(A)
    np.testing.assert_array_equal(Q,basis.null_space(A,rcond=5e-13))


def test_forced_fallback_real_kernel_and_unchanged_input(tmp_path,monkeypatch):
    A,_,_=species_jplus([(0,1,2),(0,2,1)],0)
    a=A.toarray();before=a.copy();q0,_=kernel(a)
    monkeypatch.setenv('HT3D_PROJECTOR_LOG',str(tmp_path/'events.jsonl'))
    with patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('forced')) as dd:
        q,st=kernel(a)
    assert dd.call_count==1 and st['gesvd_fallbacks']==1
    np.testing.assert_array_equal(a,before)
    np.testing.assert_allclose(q@q.T,q0@q0.T,atol=3e-14,rtol=3e-14)
    events=[json.loads(s) for s in (tmp_path/'events.jsonl').read_text().splitlines()]
    assert [e['event'] for e in events]==['svd_retry','block_done']
    assert events[0]['sources']==len(q)


def test_fallback_has_full_right_nullspace():
    a=np.zeros((2,5));a[0,0]=1;a[1,1]=2
    with patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('forced')):
        q,st=kernel(a)
    assert q.shape==(5,3)
    np.testing.assert_array_equal(a@q,0.)


def test_both_drivers_fail_loudly_with_dump(tmp_path,monkeypatch):
    monkeypatch.setenv('HT3D_PROJECTOR_DUMP_DIR',str(tmp_path))
    a=np.array([[1.,2.]])
    with patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('first')), patch.object(basis,'svd',side_effect=np.linalg.LinAlgError('second')):
        with pytest.raises(np.linalg.LinAlgError,match=r'Both J\+ SVD drivers failed'):
            kernel(a)
    dumps=list(tmp_path.glob('*.npy'))
    assert len(dumps)==1
    np.testing.assert_array_equal(np.load(dumps[0],allow_pickle=False),a)


@pytest.mark.parametrize('a',[np.array([[np.nan,1.]]),np.array([[np.inf,0.]]),np.zeros((3,2))])
def test_invalid_block_is_not_sent_to_lapack(a):
    with patch.object(basis,'null_space') as call:
        with pytest.raises(ValueError):kernel(a)
    assert not call.called


def test_no_masking_of_other_errors():
    with patch.object(basis,'null_space',side_effect=MemoryError('allocation')):
        with pytest.raises(MemoryError,match='allocation'):kernel([[1.,2.]])


def test_empty_kernel_cannot_silently_drop_states():
    with patch.object(basis,'null_space',return_value=np.empty((2,0))):
        with pytest.raises(RuntimeError,match='nullity'):kernel([[1.,2.]])


def test_inaccurate_kernel_rejected_without_weaker_gate():
    with patch.object(basis,'null_space',return_value=np.array([[1.],[0.]])):
        with pytest.raises(RuntimeError,match='verification'):kernel([[1.,2.]])


@pytest.mark.parametrize('L,J',[(4,0),(6,0),(6,1),(6,2)])
def test_forced_fallback_all_species_span_and_operators(L,J):
    with threadpool_limits(limits=1,user_api='blas'):
        b=basis.SphereBathBasis.build(L);op=ProductOperator(b,.6,4,J)
        bf=basis.SphereBathBasis.build(L)
        with patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('injected all blocks')):
            f=ProductOperator(bf,.6,4,J)
        R=op.S.T@f.S
        np.testing.assert_allclose((R.T@R).toarray(),np.eye(R.shape[0]),atol=3e-13)
        for W,V in zip(op.W,f.W):
            np.testing.assert_allclose((R.T@W@R).toarray(),V.toarray(),atol=2e-12,rtol=5e-13)
        assert f.projection_tests['svd_statistics']['gesvd_fallbacks']>0


@pytest.mark.parametrize('L', [0,2,4,6,8])
def test_exact_graph_bytes_and_edges(L):
    req=basis.graph_requirements(L);b=basis.SphereBathBasis.build(L)
    assert len(b.N)==req['states'] and len(b.parents)==req['edges']
    assert b.nbytes==req['graph_array_bytes']
    assert b.ptr.dtype==np.int64


def test_early_large_graph_rejection_before_allocations():
    with patch.object(basis,'_counts',side_effect=AssertionError('array construction reached')):
        with pytest.raises(MemoryError,match='before graph allocation'):
            basis.SphereBathBasis.build(18,max_states=50_000_000,max_bytes=2**30)


@pytest.mark.parametrize('L',[4,6,8])
def test_character_census_matches_entire_actual_graph(L):
    d=census(L,spins=(0,1,2));b=basis.SphereBathBasis.build(L)
    assert d['character_total_states']==len(b.N)
    for J in range(3):
        s=d['sectors'][str(J)];S,N,P,keep,meta=b.highest_weight(J,J%2)
        assert S.shape[1]==s['highest_weights']
        assert s['magnetic_sources']==np.count_nonzero((b.M==J)&(b.N%2==J%2))
        assert s['magnetic_targets']==np.count_nonzero((b.M==J+1)&(b.N%2==J%2))


@pytest.mark.parametrize('L,states,scalars,max_sources',[(16,8778392,15815,1864),(18,40968710,55859,4596),(20,182727113,196585,10967)])
def test_large_census_without_large_allocation(L,states,scalars,max_sources):
    d=census(L,spins=(0,));s=d['sectors']['0']
    assert d['graph']['states']==states and s['highest_weights']==scalars
    assert s['largest_blocks'][0]['sources']==max_sources


def test_species_singular_values_have_su2_gap():
    A,_,_=species_jplus([(0,1,3),(0,2,2),(0,3,1)],1)
    singular=np.linalg.svd(A.toarray(),compute_uv=False)
    vals=singular**2;js=np.rint((np.sqrt(1+4*(vals+2))-1)/2)
    np.testing.assert_allclose(vals,js*(js+1)-2,atol=1e-12)
    assert min(vals)>3.99999999999


def test_numba_csr64_serial_and_parallel():
    W=csr_matrix([[0.,2.,-1.],[3.,0.,4.]])
    ptr=W.indptr.astype(np.int64);idx=W.indices.astype(np.int64)
    X=np.arange(9,dtype=float).reshape(3,3)
    set_num_threads(4)
    try:
        np.testing.assert_array_equal(csr_serial(ptr,idx,W.data,X),W@X)
        np.testing.assert_array_equal(csr_batch(ptr,idx,W.data,X),W@X)
    finally:set_num_threads(1)
    wide=csr_matrix((np.array([2.]),np.array([2**31+2],np.int64),np.array([0,1],np.int64)),shape=(1,2**31+3))
    assert wide.indices.dtype==np.int64 and wide.indptr.dtype==np.int64
    assert int(wide.indices[0])==2**31+2

@pytest.mark.parametrize('strided',[False,True])
def test_streamed_sparse_hash_is_bit_identical(strided):
    import hashlib
    from ht3d.cache import sparse_hash
    W=csr_matrix([[1.,0.,2.],[0.,3.,4.]])
    if strided:
        data=np.empty(W.data.size*2);data[::2]=W.data;W.data=data[::2]
    h=hashlib.sha256();h.update(repr(W.shape).encode())
    for a in (W.indptr,W.indices,W.data):
        h.update(a.dtype.str.encode());h.update(np.ascontiguousarray(a).tobytes())
    assert sparse_hash(W)==h.hexdigest()
