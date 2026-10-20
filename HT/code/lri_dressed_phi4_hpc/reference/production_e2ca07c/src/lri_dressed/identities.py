"""Descendant-identity diagnostic: v_n(O) = E(d^n O) - E(O) - n for the tuned primaries.

In the continuum 1d LRI every descendant spacing is an exact integer, so v_n measures
regulator artifacts. Descendants are identified by overlap with L_{-1} applied to the
primary (level 1) or to the identified level-1 eigenvector (level 2), where

    L_{-1} = sum_{n>=0} sqrt((n+1)(n+2 delta)) a+_{n+1} a_n,

with the n=0 term acting on the dressed zero mode through a0 = q (1-(E_a-E_b)/delta)/2
(exact between local eigenstates because [H_z,q] = -i delta p). This is the FREE
generator, so overlaps are reported and weak or ambiguous identifications flagged.
Diagnostic only: it never feeds the tuning.
"""
from __future__ import annotations
import math,time
import numpy as np
from scipy.sparse import csr_matrix
from .operators import ProductOperator

PRIMARIES={'sigma':(0,1,0),'shadow':(0,1,1),'epsilon':(0,0,1)}   # (reflection, field, index)
MIN_OVERLAP=.15;MIN_RATIO=1.5


def mode_annihilators(basis):
    """a_k for k=1..cutoff on the full bath basis (both reflections), from the rank edges."""
    D=len(basis.N);rows=np.repeat(np.arange(D),np.diff(basis.ptr))
    out={}
    for k in range(1,basis.cutoff+1):
        m=basis.mode==k
        out[k]=csr_matrix((basis.amp[m],(basis.col[m].astype(np.int64),rows[m])),shape=(D,D))
    return out


class Generator:
    """Free L_{-1} on (full bath basis) x (2 nz dressed local states)."""
    def __init__(self,basis,delta,w,X1):
        ann=mode_annihilators(basis);D=len(basis.N);self.basis=basis
        bath=csr_matrix((D,D))
        for n in range(1,basis.cutoff):bath=bath+math.sqrt((n+1)*(n+2*delta))*(ann[n+1].T@ann[n])
        self.bath=bath.tocsr();self.a1dag=ann[1].T.tocsr();self.c0=math.sqrt(2*delta)
        self.a0=X1*(1-(w[:,None]-w[None,:])/delta)/2

    def embed(self,op,vec,field):
        X=np.asarray(vec).reshape(op.nB,op.nz);Y=np.zeros((len(self.basis.N),2*op.nz));p=op.kpar^field
        for par in (0,1):
            r=np.flatnonzero(p==par);Y[op.keep[r],par*op.nz:(par+1)*op.nz]=X[r]
        return Y

    def __call__(self,Y):return self.bath@Y+self.c0*(self.a1dag@Y)@self.a0.T


def identify(image,cands,base,level):
    """Best overlap of a target vector with eigenstates (index, gap, vector) whose gap lies within 1/2 of base+level."""
    nrm=float(np.linalg.norm(image))
    if not nrm>0:return {'status':'unavailable','reason':'L_-1 image has zero norm'},None
    lo,hi=base+level-.5,base+level+.5
    pool=[(j,g,Z) for j,g,Z in cands if lo<=g<=hi]
    if not pool:return {'status':'unavailable','reason':f'no computed eigenstate with gap in [{lo:.4f},{hi:.4f}]'},None
    ov=sorted(((abs(float(np.sum(image*Z)))/nrm,j,g,Z) for j,g,Z in pool),key=lambda t:-t[0])
    best,j,g,Z=ov[0];second=ov[1][0] if len(ov)>1 else 0.
    amb=best<MIN_OVERLAP or (second>0 and best/second<MIN_RATIO)
    return {'status':'ambiguous' if amb else 'ok','index':int(j),'gap':float(g),'violation':float(g-base-level),
            'overlap':float(best),'second_overlap':float(second),'candidates':len(pool)},Z


def diagnose(row,config,k=12,record_sha256=None):
    """Recompute sector spectra at the stored theta (same configuration) and report v1, v2."""
    from .solver import DressedSolver
    t=time.perf_counter();delta=config['delta'];theta=np.asarray(row['theta'],float)
    s=DressedSolver(config['bath_cut'],config['nz'],config['osc'],eig_tol=config['eig_tol'],zero_scale=config['zero_scale'],
        backend=config['resolved_backend'],ncv=config['ncv'],max_eig_iter=config['max_eig_iter'],
        residual_tol=config['residual_tol'],window=config.get('window','none'),
        window_mode=config.get('window_mode') or 'consistent',window_tol=config.get('window_tol') or 1e-12,
        window_maxiter=config.get('window_maxiter') or 50)
    s.set_delta(delta);w,L,U,local=s.prepare(theta)
    shift=None;window_info=None
    if s.win is not None:
        out={};state,window_info=s.window_spectrum(w,L,1,out)
        shift=state['D'][s.basis.N]
    s.op.set_bath_shift(shift)
    op1=ProductOperator(s.basis,delta,s.nz,1,s.backend);op1.set_bath_shift(shift)
    spectra={}
    for refl,op in ((0,s.op),(1,op1)):
        for f in (0,1):
            ww,vv,res,orth=s.sector_solve(op,w,L,f,k,diagnostics=True)
            spectra[(refl,f)]=(op,ww,vv,res,orth)
    E0=float(spectra[(0,0)][1][0])
    gen=Generator(s.basis,delta,w,3*L[2]/local['g'])   # L3 = (g/3) q
    full={key:[(float(ww[j]-E0),gen.embed(op,vv[:,j],key[1])) for j in range(len(ww))] for key,(op,ww,vv,_,_) in spectra.items()}
    report={}
    for name,(refl,f,idx) in PRIMARIES.items():
        cands=full[(refl,f)]
        if idx>=len(cands):report[name]={'status':'unavailable','reason':f'sector r{refl}f{f} has {len(cands)} computed states'};continue
        base,Y=cands[idx];entry={'gap':base}
        Z=Y
        for level in (1,2):
            image=gen(Z);tgt=((refl+level)%2,f)
            pool=[(j,g,V) for j,(g,V) in enumerate(full[tgt]) if not (tgt==(refl,f) and j==idx)]
            res,Zn=identify(image,pool,base,level)
            entry[f'level{level}']=res
            if Zn is None:
                if level==1:entry['level2']={'status':'unavailable','reason':'level 1 not identified'}
                break
            Z=Zn
        report[name]=entry
    return {'schema':'lri-dressed-identities-v1','record_sha256':record_sha256,'delta':delta,'bath_cut':config['bath_cut'],
        'window':config.get('window','none'),'window_mode':config.get('window_mode'),'theta':theta.tolist(),'k':k,
        'descendants':report,'window_correction':window_info,
        'sector_residuals':{f'r{a}f{b}':{'eigenvector':v[3],'orthogonality':v[4],'computed':int(len(v[1]))} for (a,b),v in spectra.items()},
        'generator':'free L_-1 with dressed zero mode; overlap-identified','seconds':time.perf_counter()-t}
