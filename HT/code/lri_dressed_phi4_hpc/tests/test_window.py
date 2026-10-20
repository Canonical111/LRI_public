import json
from pathlib import Path
import numpy as np
import pytest
from scipy.linalg import eigh
from scipy.optimize import brentq
from scipy.sparse import kron,csr_matrix,diags
from dressed_zero import DressedZero
from lri_dressed.local import LocalProblem
from lri_dressed.solver import DressedSolver
from lri_dressed.operators import ProductOperator
from lri_dressed.basis import BathBasis
from lri_dressed.io import validate_result
from lri_dressed.window import even_floor

ROOT=Path(__file__).resolve().parents[1]


def dense_vacuum(Lp,z,osc,delta,w,L):
    """Independent Kronecker field-even, reflection-even block of H(L') and its bath levels."""
    ref=DressedZero(Lp,z,osc,reflection=0);ref.set_delta(delta)
    H=kron(diags(w),ref.Ib)+kron(ref.Iz,ref.Hb)
    for j in range(4):H+=kron(csr_matrix(L[j]),ref.W[j+1])
    ix=ref.ix[0];levels=ref.N[ref.keep][ix%ref.nB]
    return H.tocsr()[ix][:,ix].toarray(),levels


def reference_table(cut,z,osc,delta,theta,mode):
    """D(N) from dense matrices; the consistent fixed point by bracketing root search (no Newton)."""
    w,L,U,_=LocalProblem(z,osc).evaluate(delta,theta);top=even_floor(cut);Ev={0:0.}
    for Lp in range(2,top+1,2):
        H,levels=dense_vacuum(Lp,z,osc,delta,w,L)
        if mode=='literal':Ev[Lp]=float(eigh(H,eigvals_only=True,subset_by_index=(0,0))[0]);continue
        low=np.array([Ev[even_floor(Lp-n)] if n else 0. for n in levels])
        def F(s):
            M=H.copy();M[np.diag_indices_from(M)]+=np.where(levels>0,s-low,0.)
            return float(eigh(M,eigvals_only=True,subset_by_index=(0,0))[0])-s
        a=Ev[Lp-2]-5.;b=Ev[Lp-2]+5.
        Ev[Lp]=brentq(F,a,b,xtol=1e-15,rtol=1e-15)
    return np.array([Ev[top]-Ev[even_floor(cut-n)] if n else 0. for n in range(cut+1)])


@pytest.mark.parametrize('mode',['consistent','literal'])
@pytest.mark.parametrize('backend',['tensor','ladder'])
@pytest.mark.parametrize('cut',[6,7])
def test_window_table_against_dense_reference(mode,backend,cut):
    z=4;osc=32;delta=.1
    theta=np.array(json.loads((ROOT/'inputs/N16_z24_o192_d0.10000000.json').read_text())['theta'])
    s=DressedSolver(cut,z,osc,backend=backend,window='vacuum',window_mode=mode);s.set_delta(delta)
    res,info,out,U=s.spectrum(theta,k=3)
    got=np.array([info['window']['D_by_N'][str(n)] for n in range(cut+1)])
    want=reference_table(cut,z,osc,delta,theta,mode)
    np.testing.assert_allclose(got,want,rtol=0,atol=1e-10)
    reach=np.array([even_floor(cut-n)<even_floor(cut) for n in range(cut+1)])   # window strictly below the top
    assert got[0]==0. and np.all(got[reach]<0) and np.all(got[~reach]==0.)       # vacuum fluctuations lower the energy
    if mode=='consistent':                          # the main ground state is the top-level fixed point
        assert abs(out[0][0][0]-float(info['window']['Ev'][str(even_floor(cut))]))<1e-11


@pytest.mark.parametrize('mode',['consistent','literal'])
@pytest.mark.parametrize('backend',['tensor','ladder'])
def test_window_jacobian_matches_finite_differences(mode,backend):
    s=DressedSolver(8,6,64,backend=backend,window='vacuum',window_mode=mode);s.set_delta(.1)
    theta=np.array(json.loads((ROOT/'inputs/N16_z24_o192_d0.10000000.json').read_text())['theta'])+np.array([.01,.002])
    res,info,out,U=s.spectrum(theta,k=3);got=s.response_jacobian(theta,out,U)
    fd=np.empty((2,2))
    for j in range(2):
        h=1e-5*max(1,abs(theta[j]));a=theta.copy();b=theta.copy();a[j]+=h;b[j]-=h
        fd[:,j]=(s.spectrum(a,k=3)[0]-s.spectrum(b,k=3)[0])/(2*h)
    np.testing.assert_allclose(got,fd,rtol=1e-6,atol=1e-8)


def test_window_none_operator_unchanged():
    b=BathBasis.build(8);op=ProductOperator(b,.1,6,0,'tensor')
    np.testing.assert_array_equal(op.hbk,(b.N+.1*b.P)[op.keep])
    op.set_bath_shift(np.ones(len(b.N)));op.set_bath_shift(None)
    np.testing.assert_array_equal(op.hbk,(b.N+.1*b.P)[op.keep])
    s=DressedSolver(6,4,32);s.set_delta(.2);assert s.win is None
    res,info,out,U=s.spectrum(s.initial(.2),k=3);assert 'window' not in out and 'window' not in info


def test_window_solve_record_gates(tmp_path):
    from lri_dressed.cli import main
    from lri_dressed.io import read_envelope
    base=['run','--bath-cut','6','--nz','4','--osc','32','--deltas','.2','--threads','1','--memory-limit-gib','2','--seed-dir',str(ROOT/'inputs')]
    assert main(base+['--output-dir',str(tmp_path/'raw')])==0
    assert main(base+['--output-dir',str(tmp_path/'win'),'--window','vacuum'])==0
    raw=read_envelope(next((tmp_path/'raw').glob('*.json')),'result');win=read_envelope(next((tmp_path/'win').glob('*.json')),'result')
    assert raw['config']['window']=='none' and win['config']['window']=='vacuum' and win['config']['window_mode']=='consistent'
    assert raw['config']!=win['config'] and raw['payload']['window']=='none'
    wc=win['payload']['window_correction'];validate_result(win['payload'],win['config'])
    assert wc['D_by_N']['0']==0. and wc['top_fixed_point_residual']<=1e-11
    assert abs(win['payload']['Delta_sigma_measured']-.2)<1e-8
    bad=json.loads(json.dumps(win['payload']));bad['window_correction']['top_fixed_point_residual']=1.
    with pytest.raises(ValueError):validate_result(bad,win['config'])
    bad=json.loads(json.dumps(win['payload']));bad['window']='none'
    with pytest.raises(ValueError):validate_result(bad,win['config'])


def test_window_rejects_unsupported_settings():
    with pytest.raises(ValueError):DressedSolver(6,4,32,reflection=1,window='vacuum')
    with pytest.raises(ValueError):DressedSolver(6,4,32,window='vacuum',window_tol=1e-9)


def test_absolute_fixed_point_ceiling(tmp_path):
    from lri_dressed.cli import main
    from lri_dressed.io import read_envelope
    assert main(['run','--bath-cut','6','--nz','4','--osc','32','--deltas','.2','--threads','1','--seed-dir',str(ROOT/'inputs'),
                 '--output-dir',str(tmp_path),'--window','vacuum'])==0
    rec=read_envelope(next(tmp_path.glob('*.json')),'result');bad=json.loads(json.dumps(rec['payload']))
    bad['window_correction']['top_fixed_point_residual']=5e-11          # within 5*tol*|Ev| for large |Ev|, above the ceiling
    with pytest.raises(ValueError):validate_result(bad,rec['config'])
    bad=json.loads(json.dumps(rec['payload']));lev=next(iter(bad['window_correction']['sublevel_fixed_point_residuals']))
    bad['window_correction']['sublevel_fixed_point_residuals'][lev]=2e-11
    with pytest.raises(ValueError):validate_result(bad,rec['config'])
