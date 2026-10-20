"""Chain Hamiltonian truncation (bosonic NRG) for the unbiased spin-boson model.

No CFT or thermal-coefficient targets enter this solver. Float64, no fastmath.
The energy scale changes at each iteration. Its gaps are NOT CFT dimensions.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import time
import numpy as np
from scipy.linalg import eigh
from threadpoolctl import threadpool_limits

@dataclass(frozen=True)
class Config:
    s: float = 0.9
    Lambda: float = 2.0
    nb: int = 8
    keep: int = 32  # states PER field-parity block
    nsites: int = 70
    tunneling: float = 0.1
    nlevels: int = 8
    threads: int = 1
    def check(self):
        if not (0.0 < self.s <= 1.0 and self.Lambda > 1.0):
            raise ValueError('Require 0<s<=1 and Lambda>1.')
        if min(self.nb,self.keep,self.nsites) < 2 or self.tunneling <= 0:
            raise ValueError('Resolutions/tunneling must be positive.')

def chain_coefficients(s: float, Lambda: float, nsites: int):
    """Exact recurrence for the ONE-MODE-PER-LOG-BIN discretized spectral measure.

    rho(w)=2*alpha*w**s, 0<w<1. It is J/pi in usual spin-boson notation.
    Return epsilon_n / Lambda**(-n) and t_(n-1) / Lambda**(-n).
    Little-q-Jacobi recurrence; validated independently against star moments.
    """
    q=1.0/Lambda; a=q**s
    c=(s+1)/(s+2)*(-np.expm1((s+2)*np.log(q)))/(-np.expm1((s+1)*np.log(q)))
    n=np.arange(nsites+1,dtype=float)
    A=(1-a*q**(n+1))**2/((1-a*q**(2*n+1))*(1-a*q**(2*n+2)))
    C=a*(1-q**n)**2/((1-a*q**(2*n))*(1-a*q**(2*n+1)))
    onsite=c*(A+C)
    hopping=np.zeros(nsites)
    hopping[1:]=c*np.sqrt(A[:-2]*C[1:-1]/q)
    return onsite[:nsites],hopping

def _project_old(V,op,nb):
    t=V.reshape(op.shape[0],nb,-1)
    applied=np.einsum('ab,bnk->ank',op,t,optimize=True).reshape(V.shape)
    return V.T@applied

def _project_new(V,op,nold):
    t=V.reshape(nold,op.shape[0],-1)
    applied=np.einsum('mn,ank->amk',op,t,optimize=True).reshape(V.shape)
    return V.T@applied

def run(alpha: float,cfg: Config):
    cfg.check()
    if not np.isfinite(alpha) or alpha<0: raise ValueError('alpha must be nonnegative finite')
    start=time.perf_counter()
    onsite,hop=chain_coefficients(cfg.s,cfg.Lambda,cfg.nsites)
    nb=cfg.nb; b=np.diag(np.sqrt(np.arange(1,nb)),1)
    en=np.array([-cfg.tunneling/2,cfg.tunneling/2]); par=np.array([1,-1])
    sz=np.array([[0.,1.],[1.,0.]])
    sx=np.diag([1.,-1.]); prevb=None
    records=[]; max_orth=max_resid=0.
    log_sz=0.; log_sx=0.
    with threadpool_limits(limits=cfg.threads):
      for site in range(cfg.nsites):
        nold=len(en)
        pfull=(par[:,None]*((-1)**np.arange(nb))[None,:]).ravel()
        if site==0:
            H=np.diag(np.repeat(en,nb)+np.tile(np.arange(nb)*onsite[site],nold))
            H+=0.5*np.sqrt(2*alpha/(cfg.s+1))*np.kron(sz,b+b.T)
        else:
            H=np.diag(np.repeat(cfg.Lambda*en,nb)+np.tile(np.arange(nb)*onsite[site],nold))
            H+=hop[site]*(np.kron(prevb.T,b)+np.kron(prevb,b.T))
        idx=[np.flatnonzero(pfull==p) for p in (1,-1)]
        es=[]; vs=[]; sizes=[]
        for ids in idx:
            nget=min(cfg.keep,len(ids))
            ee,uu=eigh(H[np.ix_(ids,ids)],subset_by_index=(0,nget-1),check_finite=False,driver='evr')
            es.append(ee); sizes.append(nget); vs.append(uu)
        ground=min(es[0][0],es[1][0]); en=np.concatenate(es)-ground
        par=np.repeat([1,-1],sizes)
        V=np.zeros((nold*nb,len(en)))
        for k,ids in enumerate(idx):
            offset=0 if k==0 else sizes[0]
            V[np.ix_(ids,np.arange(offset,offset+sizes[k]))]=vs[k]
        ground_idx=int(np.argmin(en)); gs=V[:,ground_idx].reshape(nold,nb)
        occ=float(np.sum(gs*gs*np.arange(nb)[None,:])); edge=float(np.sum(gs[:,-1]**2))
        sz=_project_old(V,sz,nb); sx=_project_old(V,sx,nb); prevb=_project_new(V,b,nold)
        # Exact parity selection rules. No numerical amplitude thresholds.
        odd=par[:,None]!=par[None,:]; sz*=odd; prevb*=odd; sx*=~odd
        # Remove the identity from the EVEN observer after EACH step before it
        # overwhelms its decaying connected matrix elements. Normalize both
        # observers, keeping separate logarithmic amplitudes. This does NOT
        # change Hamiltonian eigenvalues or truncate observer matrix entries.
        sx -= sx[ground_idx,ground_idx]*np.eye(len(en))
        nsz=float(np.linalg.norm(sz)); nsx=float(np.linalg.norm(sx))
        if nsz>0: sz/=nsz; log_sz+=np.log(nsz)
        if nsx>0: sx/=nsx; log_sx+=np.log(nsx)
        gap=float(es[1][0]-es[0][0]); weights=sz[:,ground_idx]**2
        corr=float(np.sum(weights*np.exp(-en)))
        sxweights=sx[:,ground_idx]**2; sxweights[ground_idx]=0
        thermal_corr=float(np.sum(sxweights*np.exp(-en)))
        records.append({'iteration':site,'log_energy_scale':float(-site*np.log(cfg.Lambda)),
             'odd_gap':gap,'last_boson_occupation':occ,'last_boson_edge':edge,
             'log_spin_scale_correlation':float(np.log(max(corr,1e-300))+2*log_sz),
             'log_retained_spin_weight':float(np.log(max(weights.sum(),1e-300))+2*log_sz),
             'log_thermal_scale_correlation':float(np.log(max(thermal_corr,1e-300))+2*log_sx),
             'even_levels':(es[0][:cfg.nlevels]-ground).tolist(),
             'odd_levels':(es[1][:cfg.nlevels]-ground).tolist()})
        if site in (0,1,2,cfg.nsites-1):
            res=H@V-V*(en+ground)[None,:]
            max_resid=max(max_resid,float(np.max(np.linalg.norm(res,axis=0))))
            max_orth=max(max_orth,float(np.max(np.abs(V.T@V-np.eye(V.shape[1])))))
    return {'alpha':alpha,'config':asdict(cfg),'records':records,
       'validation':{'max_checked_eigen_residual':max_resid,'max_checked_orthogonality':max_orth},
       'seconds':time.perf_counter()-start}

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--alpha',type=float,required=True)
    p.add_argument('--s',type=float,default=.9);p.add_argument('--Lambda',type=float,default=2)
    p.add_argument('--nb',type=int,default=8);p.add_argument('--keep',type=int,default=32)
    p.add_argument('--nsites',type=int,default=70);p.add_argument('--tunneling',type=float,default=.1)
    p.add_argument('--output',required=True);a=p.parse_args()
    cfg=Config(s=a.s,Lambda=a.Lambda,nb=a.nb,keep=a.keep,nsites=a.nsites,tunneling=a.tunneling)
    out=run(a.alpha,cfg);dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(out['seconds'],[(r['iteration'],round(r['odd_gap'],7),round(r['last_boson_occupation'],4)) for r in out['records'][::5]])
