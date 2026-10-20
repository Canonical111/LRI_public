from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import block_diag
from lri_spin import Config,run,run_tangent,chain_coefficients
from lri_spin.blocks import make_block,project_old,project_b,tangent_apply
from lri_spin.validation import validate_result
from nrg import run as reference_run,chain_coefficients as reference_chain
from nrg_tangent import run_tangent as reference_tangent

@pytest.mark.parametrize('nb',[4,5,8])
def test_block_matrix_and_projections(nb):
    rng=np.random.default_rng(40+nb);sizes=[3,2];oldpar=np.repeat([1,-1],sizes);en=[np.arange(3.)/3,np.arange(2.)/2]
    b=[rng.normal(size=(3,2)),rng.normal(size=(2,3))]
    bfull=np.block([[np.zeros((3,3)),b[0]],[b[1],np.zeros((2,2))]])
    bos=np.diag(np.sqrt(np.arange(1,nb)),1)
    full=np.diag(np.repeat(2*np.r_[tuple(en)],nb)+np.tile(.7*np.arange(nb),5))+ .4*(np.kron(bfull.T,bos)+np.kron(bfull,bos.T))
    blocks=[make_block(en,b,.7,.4,2.,nb,s) for s in (0,1)]
    perms=[];vecs=[];V=np.zeros((5*nb,8))
    for s,H in enumerate(blocks):
        ids=[]
        for n in range(nb):
            ids.extend(a*nb+n for a in np.flatnonzero(oldpar==(1 if (s^(n&1))==0 else -1)))
        ids=np.array(ids);perms.append(ids)
        np.testing.assert_allclose(H.dense(),full[np.ix_(ids,ids)],rtol=0,atol=1e-14)
        U=np.linalg.qr(rng.normal(size=(len(ids),4)))[0];vecs.append(U);V[ids,s*4:(s+1)*4]=U
        np.testing.assert_allclose(H.apply(U),H.dense()@U,rtol=1e-13,atol=1e-13)
        be,bu=H.solve(4,backend='banded');de,du=H.solve(4)
        np.testing.assert_allclose(be,de,atol=1e-12)
    layouts=[h.layout for h in blocks]
    ref=V.T@np.kron(np.eye(5),bos)@V
    got=project_b(vecs,layouts)
    for s in (0,1):np.testing.assert_allclose(got[s],ref[s*4:(s+1)*4,(1-s)*4:(2-s)*4],atol=1e-13)
    for odd in (False,True):
        op=b if odd else [rng.normal(size=(3,3)),rng.normal(size=(2,2))]
        O=bfull if odd else block_diag(*op)
        ref=V.T@np.kron(O,np.eye(nb))@V;got=project_old(vecs,layouts,op,odd)
        for s in (0,1):
            t=1-s if odd else s
            np.testing.assert_allclose(got[s],ref[s*4:(s+1)*4,t*4:(t+1)*4],atol=1e-13)
    de=[rng.normal(size=(3,3)),rng.normal(size=(2,2))]
    DH=2*np.kron(block_diag(*de),np.eye(nb))+.4*(np.kron(bfull.T,bos)+np.kron(bfull,bos.T))
    for s,H in enumerate(blocks):
        np.testing.assert_allclose(tangent_apply(H.layout,vecs[s],de,b,.4,2),DH[np.ix_(perms[s],perms[s])]@vecs[s],atol=1e-13)

@pytest.mark.parametrize('s,alpha,k,b,n',[(.8,.4,12,6,12),(.98,1.08,16,8,14),(.52,.1278,12,5,12)])
@pytest.mark.parametrize('tangent',[False,True])
def test_reference_trajectories(s,alpha,k,b,n,tangent):
    c=Config(s=s,Lambda=3.,keep=k,nb=b,nsites=n)
    old=(reference_tangent if tangent else reference_run)(alpha,c)
    new=run(alpha,c,tangent=tangent)
    keys=['odd_gap','last_boson_occupation','last_boson_edge','log_spin_scale_correlation','log_thermal_scale_correlation','even_levels','odd_levels']
    if tangent:keys+=['d_alpha_odd_gap']
    for key in keys:
        for a,v in zip(new['records'],old['records']):
            np.testing.assert_allclose(a[key],v[key],atol=1e-9,rtol=2e-10,err_msg=key)
    validate_result(new,c,tangent=tangent)

@pytest.mark.parametrize('workers,threads',[(1,1),(1,2),(2,2)])
def test_threading_and_observer_skipping(workers,threads):
    c=Config(s=.8,Lambda=3,keep=12,nb=6,nsites=12,threads=threads)
    a=run_tangent(.4,replace(c,threads=1));b=run_tangent(.4,c,sector_workers=workers,backend='dense' if workers==2 else 'ordered')
    z=run(.4,c,sector_workers=workers,observers=False,backend='dense' if workers==2 else 'ordered')
    for r,q,w in zip(a['records'],b['records'],z['records']):
        np.testing.assert_allclose([r['odd_gap'],r['d_alpha_odd_gap']],[q['odd_gap'],q['d_alpha_odd_gap']],atol=1e-9,rtol=1e-10)
        assert abs(r['odd_gap']-w['odd_gap'])<1e-10

@pytest.mark.parametrize('s,alpha',[(.8,.4),(.98,1.08)])
def test_finite_difference(s,alpha):
    c=Config(s=s,Lambda=3,keep=12,nb=6,nsites=12);h=3e-7
    t=run_tangent(alpha,c);m=run(alpha-h,c);p=run(alpha+h,c)
    v=np.array([r['d_alpha_odd_gap'] for r in t['records']]);fd=np.array([r['odd_gap']-q['odd_gap'] for r,q in zip(p['records'],m['records'])])/(2*h)
    assert np.max(abs(v-fd)/np.maximum(1,abs(v)))<2e-6

@pytest.mark.parametrize('s,lam',[(.5,2.),(.8,3.),(.999,1.5)])
def test_chain_identical(s,lam):
    for a,b in zip(chain_coefficients(s,lam,200),reference_chain(s,lam,200)):np.testing.assert_array_equal(a,b)

@pytest.mark.parametrize('kw',[{'s':float('nan')},{'Lambda':1.},{'nb':1},{'threads':0},{'keep':2.5}])
def test_invalid_config(kw):
    with pytest.raises(ValueError):Config(**kw).check()

@pytest.mark.parametrize('s,lam',[(.55,1.5),(.8,2.),(.99,3.)])
def test_independent_star_chain_moments(s,lam):
    onsite,hop=chain_coefficients(s,lam,32);q=1/lam;n=np.arange(32)
    J=np.diag(onsite*q**n)+np.diag(hop[1:]*q**n[1:],1)+np.diag(hop[1:]*q**n[1:],-1)
    c=(s+1)/(s+2)*(1-q**(s+2))/(1-q**(s+1));vec=np.eye(32)[:,0]
    for k in range(20):
        exact=c**k*(1-q**(s+1))/(1-q**(s+k+1))
        assert abs(vec[0]-exact)<3e-14
        vec=J@vec


def test_untruncated_dense_observers_and_spectrum():
    from scipy.linalg import eigh
    from threadpoolctl import threadpool_limits
    cfg=Config(s=.98,Lambda=3,nb=3,keep=256,nsites=4);alpha=1.0814
    rr=run(alpha,cfg);b=np.diag(np.sqrt(np.arange(1,cfg.nb)),1);Ib=np.eye(cfg.nb)
    sz=np.array([[0.,1.],[1.,0.]]);sx=np.diag([1.,-1.]);H=-cfg.tunneling*sx/2
    onsite,hop=chain_coefficients(cfg.s,cfg.Lambda,cfg.nsites);last=None;par=np.array([1,-1])
    with threadpool_limits(limits=1):
      for n in range(cfg.nsites):
        I=np.eye(H.shape[0]);H=np.kron(H,Ib)+cfg.Lambda**(-n)*onsite[n]*np.kron(I,b.T@b)
        if n==0:H+=.5*np.sqrt(2*alpha/(cfg.s+1))*np.kron(sz,b+b.T)
        else:H+=cfg.Lambda**(-n)*hop[n]*(np.kron(last.T,b)+np.kron(last,b.T))
        last=np.kron(I,b);sz=np.kron(sz,Ib);sx=np.kron(sx,Ib);par=(par[:,None]*(-1)**np.arange(cfg.nb)[None,:]).ravel()
        e,v=eigh(H);gaps=(e-e[0])*cfg.Lambda**n;spin=(v.T@sz@v[:,0])**2;therm=(v.T@sx@v[:,0])**2;therm[0]=0
        assert abs(float(np.log(spin@np.exp(-gaps)))-rr['records'][n]['log_spin_scale_correlation'])<1e-10
        assert abs(float(np.log(therm@np.exp(-gaps)))-rr['records'][n]['log_thermal_scale_correlation'])<1e-10
        for p,key in [(1,'even_levels'),(-1,'odd_levels')]:
            ids=np.flatnonzero(par==p);er=eigh(H[np.ix_(ids,ids)],eigvals_only=True)
            expected=(er-e[0])*cfg.Lambda**n
            np.testing.assert_allclose(rr['records'][n][key],expected[:len(rr['records'][n][key])],atol=1e-10)


def test_default_keeps_primal_replay():
    c=Config(s=.8,Lambda=3,keep=16,nb=8,nsites=26)
    for tangent in (False,True):
        ref=(reference_tangent if tangent else reference_run)(.439,c)
        r=run(.439,c,tangent=tangent)
        # Across runtime/BLAS versions equality need not be bitwise; tight tolerance remains required.
        for a,b in zip(r['records'],ref['records']):
            np.testing.assert_allclose(a['even_levels'],b['even_levels'],rtol=2e-12,atol=1e-10)
            np.testing.assert_allclose(a['odd_levels'],b['odd_levels'],rtol=2e-12,atol=1e-10)
            if tangent:np.testing.assert_allclose(a['d_alpha_odd_gap'],b['d_alpha_odd_gap'],rtol=2e-10,atol=1e-9)
