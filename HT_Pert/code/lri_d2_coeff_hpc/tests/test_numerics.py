"""Independent coefficient, operator, precision, support and thread tests."""
from pathlib import Path
from fractions import Fraction
import json
import numpy as np
import pytest
from numba import set_num_threads
from lri_coeff.engine import Engine
from lri_coeff.basis import Graph,plan
from lri_coeff.operators import Operators
from circle_jets import CircleSpace,Engine as Reference
from analytic_checks import c2,vacuum2,window4
ROOT=Path(__file__).resolve().parents[1]

def compare(a,b,tol=5e-11):
    for k in ('C','r','g','energies','vacuum_coefficients'):
        aa=np.asarray(a[k]);bb=np.asarray(b[k]);err=np.max(abs(aa-bb)/np.maximum(1,abs(bb)))
        assert err<tol,(k,err)

@pytest.mark.parametrize('scheme',['raw','consistent','literal'])
@pytest.mark.parametrize('L',[0,2,4,6,8])
def test_coefficients(L,scheme):
    set_num_threads(1);a=Engine(L,8,scheme).solve(False);b=Reference(L,8,scheme).solve(False)
    compare(a,b)
    f=ROOT/f'reference/lri_d2_perturbative_C8/results/exact/{scheme}_L{L}_d8.json'
    if f.exists():
        q=json.loads(f.read_text());rr=np.array([float(Fraction(z)) for z in q['rational_C']]);assert np.max(abs(np.array(a['C'])-rr)/np.maximum(1,abs(rr)))<5e-12
    assert abs(a['C'][2]-float(c2(L)))<1e-12
    grids=range(0,L+1,2) if scheme!='raw' else [L]
    assert max(abs(row[2]-float(vacuum2(ell))) for row,ell in zip(a['vacuum_coefficients'],grids))<1e-12

@pytest.mark.parametrize('degree',[2,3,4,5,6,7,8])
def test_order(degree):
    a=Engine(4,degree,'consistent').solve(False);b=Reference(4,degree,'consistent').solve(False);compare(a,b)

@pytest.mark.parametrize('L',[0,2,4,8,12])
def test_exact_graph(L):
    a=Graph.build(L);b=CircleSpace(L,8)
    assert a.n==b.n
    assert np.array_equal(a.N,b.N);assert np.array_equal(a.P,b.P);assert np.array_equal(a.Jabs,b.Jabs)
    p=plan(L);assert p['ladder_edges']==a.nnz;assert p['scalar_even_by_cutoff'][-1]==np.count_nonzero(a.scalar&(a.P%2==0))
    assert p['scalar_odd_by_cutoff'][-1]==np.count_nonzero(a.scalar&(a.P%2==1))
    from scipy.sparse import csr_matrix
    for d in range(8):
        mat=csr_matrix((a.amp*a.u[a.mode,d],a.child,a.cptr),shape=(a.n,a.n));dif=mat-b.C[d]
        assert not dif.nnz or max(abs(dif.data))<2e-14

@pytest.mark.parametrize('L',[2,4,8])
def test_operator_and_moments(L):
    g=Graph.build(L);ops=Operators(g);ref=CircleSpace(L,8)
    rng=np.random.default_rng(7261);x=rng.normal(size=(g.n,4));x[g.Jabs!=0]=0
    n=g.n
    for d in [3,7]:
        m,v=ops.vertices(x,d,n);mr,vr=ref.vertices(x.T[:,:,None],d,n,ref.prefix(n))
        assert np.max(abs(m-mr[:,:,0].T))<2e-11;assert np.max(abs(v-vr[:,:,0].T))<3e-10
    ids=np.flatnonzero(g.scalar);psi=x[ids].T
    mm,vv=ops.moments(psi,ids,n,7)
    for k in range(8):
        m=0.;v=0.
        for j in range(min(k,3)+1):
            m+=float(np.sum(psi[j]*mr[k-j,ids,0],dtype=np.longdouble))
            v+=float(np.sum(psi[j]*vr[k-j,ids,0],dtype=np.longdouble))
        assert np.isclose(mm[k],m,atol=1e-10,rtol=2e-13)
        assert np.isclose(vv[k],v,atol=1e-9,rtol=2e-13)

@pytest.mark.parametrize('backend',['native','numba'])
def test_threads(backend):
    set_num_threads(1);a=Engine(10,8,'consistent',backend=backend).solve(False)
    set_num_threads(4);b=Engine(10,8,'consistent',backend=backend).solve(False)
    for k in ['C','r','g','energies','vacuum_coefficients']:assert np.array_equal(a[k],b[k]),k
    set_num_threads(1)

def test_backends_and_support():
    a=Engine(4,8,'consistent').solve(False)
    for kw in [dict(backend='numba'),dict(full_order=True),dict(pmax=23)]:compare(Engine(4,8,'consistent',**kw).solve(False),a)
    raw=Engine(4,8,'raw').solve(False)
    assert abs(a['C'][4]-raw['C'][4]-float(window4(4)))<1e-12
    literal=Engine(4,8,'literal').solve(False)
    assert np.max(abs(np.array(a['C'][:6])-literal['C'][:6]))<1e-10
    assert abs(a['C'][6]-literal['C'][6])>1e-6

def test_guards():
    for kw in [dict(L=3),dict(L=-2),dict(L=2,degree=9),dict(L=2,pmax=8),dict(L=2,reflection=False),dict(L=2,envelope=False),dict(L=20,max_states=10),dict(L=20,max_bytes=100000)]:
        with pytest.raises((ValueError,MemoryError)):Engine(**kw)
