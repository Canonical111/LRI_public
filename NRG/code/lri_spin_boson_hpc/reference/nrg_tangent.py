"""Gauge-covariant analytic alpha tangent of a truncated bosonic NRG map.

No finite differences in alpha. Derivatives of the kept projectors include the
whole discarded subspace at each step. Kept-kept eigenbasis rotations are not
formed: the retained H tangent stays a full matrix in parallel-transport gauge.
This derivative is of the finite numerical map, not of its continuum limit.
"""
from dataclasses import asdict
import time
import numpy as np
from scipy.linalg import eigh
from threadpoolctl import threadpool_limits
from nrg import Config,chain_coefficients,_project_new,_project_old


def run_tangent(alpha,cfg):
    cfg.check()
    if alpha<=0:raise ValueError('positive alpha required for sqrt(alpha) tangent')
    start=time.perf_counter();nb=cfg.nb
    b=np.diag(np.sqrt(np.arange(1,nb)),1);onsite,hop=chain_coefficients(cfg.s,cfg.Lambda,cfg.nsites)
    en=np.array([-cfg.tunneling/2,cfg.tunneling/2]);par=np.array([1,-1]);sz=np.array([[0.,1.],[1.,0.]])
    de=np.zeros((2,2));prevb=dprevb=None;records=[];mingap=float('inf');sx=np.diag([1.,-1.]);logsz=logsx=0.
    with threadpool_limits(limits=cfg.threads):
      for site in range(cfg.nsites):
        nold=len(en);pb=(par[:,None]*((-1)**np.arange(nb))[None,:]).ravel()
        if site==0:
          coupling=.5*np.sqrt(2*alpha/(cfg.s+1))*np.kron(sz,b+b.T)
          H=np.diag(np.repeat(en,nb)+np.tile(np.arange(nb)*onsite[site],nold))+coupling
          DH=coupling/(2*alpha)
        else:
          H=np.diag(np.repeat(cfg.Lambda*en,nb)+np.tile(np.arange(nb)*onsite[site],nold))+hop[site]*(np.kron(prevb.T,b)+np.kron(prevb,b.T))
          DH=cfg.Lambda*np.kron(de,np.eye(nb))+hop[site]*(np.kron(dprevb.T,b)+np.kron(dprevb,b.T))
        ids=[np.flatnonzero(pb==p) for p in [1,-1]];es=[];vv=[];dvv=[];ders=[];sizes=[];dground=[]
        for block in ids:
          ee,U=eigh(H[np.ix_(block,block)],check_finite=False,driver='evd')
          k=min(cfg.keep,len(block));Uk=U[:,:k];Ud=U[:,k:]
          hd=DH[np.ix_(block,block)];tang=Uk.T@hd@Uk
          if len(ee)>k:
            gap=float(ee[k]-ee[k-1]);mingap=min(mingap,gap)
            if gap<5e-13*max(1,float(abs(ee[k]))):
              raise ArithmeticError(f'Non-smooth kept/discarded boundary at site {site}: gap={gap}')
            cross=Ud.T@hd@Uk;den=ee[:k][None,:]-ee[k:,None]
            dU=Ud@(cross/den)
          else:dU=np.zeros_like(Uk)
          es.append(ee[:k]);vv.append(Uk);dvv.append(dU);ders.append(tang);sizes.append(k);dground.append(float(tang[0,0]))
        gsector=int(es[1][0]<es[0][0]);ground=float(es[gsector][0]);dE0=dground[gsector]
        en=np.concatenate(es)-ground;par=np.repeat([1,-1],sizes);V=np.zeros((nold*nb,len(en)));DV=np.zeros_like(V);de=np.zeros((len(en),len(en)))
        offset=0
        for k,block in enumerate(ids):
          dst=np.arange(offset,offset+sizes[k]);V[np.ix_(block,dst)]=vv[k];DV[np.ix_(block,dst)]=dvv[k]
          de[np.ix_(dst,dst)]=ders[k];offset+=sizes[k]
        de-=dE0*np.eye(len(en))
        # Project newest oscillator; its explicit alpha derivative vanishes.
        a=np.einsum('mn,ank->amk',b,V.reshape(nold,nb,-1),optimize=True).reshape(V.shape)
        da=np.einsum('mn,ank->amk',b,DV.reshape(nold,nb,-1),optimize=True).reshape(V.shape)
        prevb=V.T@a;dprevb=DV.T@a+V.T@da
        odd=par[:,None]!=par[None,:];prevb*=odd;dprevb*=odd;de*=~odd
        ground_idx=int(np.argmin(en));sz=_project_old(V,sz,nb);sx=_project_old(V,sx,nb)
        sz*=odd;sx*=~odd;sx-=sx[ground_idx,ground_idx]*np.eye(len(en))
        nz=float(np.linalg.norm(sz));nx=float(np.linalg.norm(sx))
        if nz>0:sz/=nz;logsz+=np.log(nz)
        if nx>0:sx/=nx;logsx+=np.log(nx)
        cz=float(np.sum(sz[:,ground_idx]**2*np.exp(-en)));ct=float(np.sum(sx[:,ground_idx]**2*np.exp(-en)))
        gs=V[:,ground_idx].reshape(nold,nb)
        records.append({'iteration':site,'odd_gap':float(es[1][0]-es[0][0]),'d_alpha_odd_gap':dground[1]-dground[0],
           'log_spin_scale_correlation':float(np.log(max(cz,1e-300))+2*logsz),
           'log_thermal_scale_correlation':float(np.log(max(ct,1e-300))+2*logsx),
           'last_boson_occupation':float(np.sum(gs*gs*np.arange(nb)[None,:])),
           'last_boson_edge':float(np.sum(gs[:,-1]**2)),
           'log_abs_d_alpha_odd_gap':float(np.log(max(abs(dground[1]-dground[0]),1e-300))),
           'even_levels':(es[0][:cfg.nlevels]-ground).tolist(),'odd_levels':(es[1][:cfg.nlevels]-ground).tolist()})
    return {'alpha':alpha,'config':asdict(cfg),'records':records,'minimum_kept_discarded_gap':mingap,
            'seconds':time.perf_counter()-start,'method':'analytic kept-projector alpha tangent; no finite differences'}

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('critical');p.add_argument('--output',required=True);a=p.parse_args()
    d=json.loads(Path(a.critical).read_text());out=run_tangent(d['alpha'],Config(**d['config']))
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(out['seconds'])
