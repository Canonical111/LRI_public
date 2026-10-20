import json,math
from pathlib import Path
from fractions import Fraction
import numpy as np
import pytest
from lri_c8.engine import compute,assemble,validate_result,low_calibration,component
from lri_c8.residual import OuterSpace,resolvent_norm,creation_stored,creation_ranked,last_resolvent_stored,last_resolvent_ranked
from lri_c8.packed import PackedCore,packed_ladder
from lri_c8._core.operators import Space
from lri_c8.planning import counts,plan
ROOT=Path(__file__).resolve().parents[1]
TOL={'atol':1e-7,'rtol':2e-11}

@pytest.mark.parametrize('scheme',['raw','vacuum_only'])
@pytest.mark.parametrize('L',[2,4,6,8,12])
def test_full_recursion(L,scheme):
    from validate_recursion import full
    a=compute(L,scheme);b=full(L,scheme)
    for k in ['C','r','g']:np.testing.assert_allclose(a[k],b[k],**TOL)
    validate_result(a)

@pytest.mark.parametrize('L',[4,8,16,24])
def test_saved_and_rational(L):
    r=compute(L)
    b=json.loads((ROOT/f'inputs/raw/raw_L{L}_d8.json').read_text())
    for k in ('C','r','g'):np.testing.assert_allclose(r[k],b[k],**TOL)
    records=json.loads((ROOT/'inputs/exact_rational_validation.json').read_text())
    for rec in records:
        if rec['cutoff']==L:
            for k in ('C','r','g'):
                a=[float(Fraction(x)) for x in rec['rational_'+k]]
                np.testing.assert_allclose(r[k],a,**TOL)

def test_fresh_exact_rational():
    from exact_rational import exact
    r=exact(4);a=compute(4)
    for k in ('C','r','g'):np.testing.assert_allclose(a[k],[float(Fraction(v)) for v in r['rational_'+k]],**TOL)

@pytest.mark.parametrize('scheme',['raw','vacuum_only'])
def test_outer_backends_and_threads(scheme):
    import numba
    numba.set_num_threads(1);a=compute(12,scheme,'stored')
    numba.set_num_threads(2);b=compute(12,scheme,'ranked')
    for k in ('C','r','g','energies'):np.testing.assert_allclose(a[k],b[k],atol=1e-10,rtol=2e-14)

@pytest.mark.parametrize('L',[4,12])
def test_operators_packing_and_wide_indices(L):
    pc=PackedCore(L);orig=Space(L,15,12,7);rng=np.random.default_rng(3021)
    for p in (0,1):
        sp=pc.sector(p);x=np.zeros((orig.dim,3));xp=rng.normal(size=(sp.dim,3));x[pc.rows[p]]=xp
        # Verify complete vertices only project reflection at the end.
        ma,va=sp.vertices(xp,3,parity=p);mb,vb=orig.vertices(x,3,parity=p)
        np.testing.assert_allclose(ma,mb[pc.rows[p]],rtol=5e-14,atol=2e-12)
        np.testing.assert_allclose(va,vb[pc.rows[p]],rtol=5e-14,atol=2e-12)
        for tag in ('B','C'):
            e=pc.edges[tag,1-p]
            wide=packed_ladder(e.ptr,e.index.astype(np.int64),e.mode,e.occ,pc.weights,xp,3)
            regular=sp.linear(xp,3,tag=='C',p)
            np.testing.assert_array_equal(wide,regular)
    big=OuterSpace(L,pc.dim,'stored',pc.rows);ranked=OuterSpace(L,pc.dim,'ranked',pc.rows)
    vec=rng.normal(size=big.dim)
    for p in (0,1):
        e=big.edge
        a=creation_stored(e.ptr,e.index.astype(np.int64),e.mode,e.occ,big.weights,vec,big.P,p)
        b=ranked.creation(vec,p);np.testing.assert_array_equal(a,b)
        va=last_resolvent_stored(e.ptr,e.index.astype(np.int64),e.mode,e.occ,big.weights,vec,big.P,big.N,big.Q,p)
        vb=last_resolvent_ranked(ranked.G,ranked.Z,L,big.weights,vec,big.P,big.N,big.Q,p)
        np.testing.assert_array_equal(va,vb)

@pytest.mark.parametrize('L',[4,8,16])
def test_rank_embedding_and_counts(L):
    small=Space(L,15,12,7);pc=PackedCore(L);big=OuterSpace(L,pc.dim,'stored',pc.rows)
    c=counts(L,15,12);b=counts(L,19,16)
    assert c['dim']==small.dim and b['dim']==big.dim
    assert c['edges_per_orientation']==len(small.creation.index)==len(small.annihilation.index)
    assert b['edges_per_orientation']==big.nedges
    for p in (0,1):
        idx=big.maps[p];assert len(np.unique(idx))==len(idx)
        np.testing.assert_array_equal(big.P[idx],pc.P[p]);np.testing.assert_array_equal(big.N[idx],pc.N[p])
        assert len(pc.P[p])==c['parity_dimensions'][p]

@pytest.mark.parametrize('bad',[1,3,0,-2])
def test_invalid_cutoff(bad):
    with pytest.raises(ValueError):compute(bad)

def test_finiteness_and_caps():
    r=compute(4)
    for key in ['low_order_residual','second_order_shell_residual','tuning_residual']:
        bad=dict(r);bad[key]=float('nan')
        with pytest.raises(ArithmeticError):validate_result(bad)
    bad=dict(r);bad['particle_cap']=15
    with pytest.raises(ArithmeticError):validate_result(bad)
    with pytest.raises(MemoryError):compute(50,memory_limit_gib=.01)

def test_reference_shards_exact():
    # Assemble independent reference calculations, not an average of physical exponents.
    parts=[compute(8,references=(p,)) for p in (0,1,3,2)]
    c={p:parts[i]['components'][str(p)] for i,p in enumerate((0,1,3,2))}
    a=assemble(c,parts[0]['low'],8,'raw');b=compute(8)
    for k in ('C','r','g'):np.testing.assert_array_equal(a[k],b[k])

@pytest.mark.parametrize('L',[2,4,6,8,12])
def test_all_exact_rational_records(L):
    # Every stored exact-rational record (test_saved_and_rational only reaches L=4,8).
    rec=[x for x in json.loads((ROOT/'inputs/exact_rational_validation.json').read_text()) if x['cutoff']==L]
    assert len(rec)==1
    r=compute(L)
    for k in ('C','r','g'):
        np.testing.assert_allclose(r[k],[float(Fraction(x)) for x in rec[0]['rational_'+k]],**TOL)

@pytest.mark.parametrize('L',[4,16,24,32])
def test_saved_vacuum_only(L):
    r=compute(L,'vacuum_only')
    b=json.loads((ROOT/f'inputs/vacuum_only/vacuum_only_L{L}_d8.json').read_text())
    for k in ('C','r','g','energies'):np.testing.assert_allclose(r[k],b[k],**TOL)

@pytest.mark.parametrize('scheme',['raw','vacuum_only'])
def test_uncapped_support(scheme):
    # Independent check of the P<=19,Q<=16 support AND the P<=15,Q<=12 core split: the
    # original solver with NO particle caps (energy cutoff only) at L=24, where P caps and
    # both Q caps (Q=13 needs L>=16.25, Q=17 needs L>=21.25) bind.
    import c8_solver
    orig=c8_solver.compute
    def uncapped(cutoff,degree=8,scheme='raw',checkpoint=None,memory_limit_gib=None,pmax=None,qmax=None):
        cap=min(4*cutoff,255)
        return orig(cutoff,degree,scheme,checkpoint,memory_limit_gib,cap if pmax is None else pmax,cap if qmax is None else qmax)
    c8_solver.compute=uncapped
    try:b=uncapped(24,8,scheme)
    finally:c8_solver.compute=orig
    assert b['particle_cap']==96 and b['basis_dimension']>counts(24,19,16)['dim']
    a=compute(24,scheme)
    for k in ('C','r','g','energies'):np.testing.assert_allclose(a[k],b[k],**TOL)
