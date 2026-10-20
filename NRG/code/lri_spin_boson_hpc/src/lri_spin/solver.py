"""Exact block-structured bosonic NRG with the full kept-projector derivative.

Only storage/order of arithmetic change. nb and keep have their original meaning.
"""
from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import numpy as np
from threadpoolctl import threadpool_limits
from .config import Config,chain_coefficients
from .blocks import make_block, tangent_apply, project_b, project_old


def run(alpha:float,cfg:Config,*,tangent=False,backend='dense',observers=True,
        checkpoint=None,resume_state=None,stop_requested=None,check_every=0,sector_workers=1):
    cfg.check()
    if not np.isfinite(alpha) or alpha<0 or (tangent and alpha<=0):
        raise ValueError('Need alpha>=0 (strictly positive for analytic tangent)')
    if backend not in ('dense','banded'):raise ValueError('Unknown backend')
    if sector_workers not in (1,2) or cfg.threads<sector_workers or cfg.threads%sector_workers:
        raise ValueError('sector_workers=1 or 2 must divide the positive total thread budget')
    start=time.perf_counter();onsite,hop=chain_coefficients(cfg.s,cfg.Lambda,cfg.nsites)
    times={k:0. for k in ('assemble','eigensolve','tangent','projection','diagnostics','checkpoint')}
    if resume_state is None:
        en=[np.array([-cfg.tunneling/2]),np.array([cfg.tunneling/2])]
        sz=[np.ones((1,1)),np.ones((1,1))]
        sx=[np.ones((1,1)),-np.ones((1,1))]
        prevb=None; de=[np.zeros((1,1)),np.zeros((1,1))];db=None
        logsz=logsx=0.;records=[];mingap=None;maxres=maxorth=0.;begin=0
    else:
        st=resume_state
        en=[st['en0'],st['en1']];prevb=[st['b0'],st['b1']]
        sz=[st['sz0'],st['sz1']] if observers else None
        sx=[st['sx0'],st['sx1']] if observers else None
        de=[st['de0'],st['de1']] if tangent else None
        db=[st['db0'],st['db1']] if tangent else None
        meta=st['meta'];logsz=meta['logsz'];logsx=meta['logsx'];records=meta['records']
        begin=meta['next_site'];mingap=meta['mingap'];maxres=meta['maxres'];maxorth=meta['maxorth']
        times.update(meta.get('timing',{}))
    with threadpool_limits(limits=cfg.threads//sector_workers), \
         (ThreadPoolExecutor(max_workers=2) if sector_workers==2 else nullcontext()) as pool:
      for site in range(begin,cfg.nsites):
        tick=time.perf_counter()
        if site==0:
            c=.5*np.sqrt(2*alpha/(cfg.s+1))
            bp=[np.ones((1,1)),np.ones((1,1))]
            coupling=c;scale=1.
        else:bp=prevb;coupling=hop[site];scale=cfg.Lambda
        blocks=[make_block(en,bp,onsite[site],coupling,scale,cfg.nb,s) for s in (0,1)]
        layouts=[h.layout for h in blocks]
        times['assemble']+=time.perf_counter()-tick
        def solve_sector(s):
            H=blocks[s]; tick=time.perf_counter()
            vals,U=H.solve(cfg.keep,full=tangent,backend=backend)
            eigtime=time.perf_counter()-tick
            k=min(cfg.keep,len(vals));V=np.array(U[:,:k],order='F',copy=True)
            tick=time.perf_counter();gap=None;ds=DV=None
            if tangent:
                if site==0:
                    z=[np.zeros((1,1)),np.zeros((1,1))]
                    dHU=tangent_apply(H.layout,V,z,[bp[0]/(2*alpha),bp[1]/(2*alpha)],coupling,0.)
                else:
                    dHU=tangent_apply(H.layout,V,de,db,coupling,scale)
                ds=V.T@dHU
                if len(vals)>k:
                    gap=float(vals[k]-vals[k-1])
                    if gap<5e-13*max(1.,abs(float(vals[k]))):
                        raise ArithmeticError(f'Non-smooth kept/discarded boundary at site {site}: {gap}')
                    Ud=U[:,k:]
                    cross=Ud.T@dHU
                    cross/=vals[:k][None,:]-vals[k:,None]
                    DV=Ud@cross
                else:DV=np.zeros_like(V)
            return vals[:k].copy(),V,DV,ds,gap,eigtime,time.perf_counter()-tick
        solved=list(pool.map(solve_sector,(0,1))) if sector_workers==2 else [solve_sector(s) for s in (0,1)]
        ev=[v[0] for v in solved];vs=[v[1] for v in solved]
        dvs=[v[2] for v in solved];ders=[v[3] for v in solved]
        for v in solved:
            if v[4] is not None:mingap=v[4] if mingap is None else min(mingap,v[4])
        # With two workers these are worker-seconds, not elapsed wall seconds.
        times['eigensolve']+=sum(v[5] for v in solved)
        times['tangent']+=sum(v[6] for v in solved)
        gsector=int(ev[1][0]<ev[0][0]);ground=float(ev[gsector][0])
        en=[e-ground for e in ev]
        tick=time.perf_counter()
        bnew=project_b(vs,layouts)
        if tangent:
            dl=project_b(vs,layouts,left=dvs)
            dr=project_b(vs,layouts,right=dvs)
            db=[dl[s]+dr[s] for s in (0,1)]
            dground=[float(ders[s][0,0]) for s in (0,1)]
            de=[ders[s]-dground[gsector]*np.eye(len(en[s])) for s in (0,1)]
        prevb=bnew
        if observers:
            sz=project_old(vs,layouts,sz,odd=True)
            sx=project_old(vs,layouts,sx,odd=False)
            mean=float(sx[gsector][0,0]);sx=[v-mean*np.eye(len(v)) for v in sx]
            nz=np.sqrt(sum(np.sum(v*v) for v in sz));nx=np.sqrt(sum(np.sum(v*v) for v in sx))
            if nz>0:sz=[v/nz for v in sz];logsz+=np.log(nz)
            if nx>0:sx=[v/nx for v in sx];logsx+=np.log(nx)
        times['projection']+=time.perf_counter()-tick
        tick=time.perf_counter()
        normby=np.array([np.sum(v[:,0]**2) for v in layouts[gsector].split(vs[gsector])])
        rec={'iteration':site,'log_energy_scale':float(-site*np.log(cfg.Lambda)),
             'odd_gap':float(ev[1][0]-ev[0][0]),
             'last_boson_occupation':float(np.dot(np.arange(cfg.nb),normby)),
             'last_boson_edge':float(normby[-1]),
             'even_levels':en[0][:cfg.nlevels].tolist(),'odd_levels':en[1][:cfg.nlevels].tolist()}
        if observers:
            w=sz[1-gsector][:,0]**2;cw=float(w@np.exp(-en[1-gsector]))
            wx=sx[gsector][:,0]**2;wx[0]=0.;cx=float(wx@np.exp(-en[gsector]))
            rec.update(log_spin_scale_correlation=float(np.log(max(cw,1e-300))+2*logsz),
                       log_retained_spin_weight=float(np.log(max(w.sum(),1e-300))+2*logsz),
                       log_thermal_scale_correlation=float(np.log(max(cx,1e-300))+2*logsx))
        if tangent:
            dgap=dground[1]-dground[0]
            rec['d_alpha_odd_gap']=float(dgap)
            rec['log_abs_d_alpha_odd_gap']=float(np.log(max(abs(dgap),1e-300)))
        if site in (0,1,2,cfg.nsites-1) or (check_every and site%check_every==0):
            for s in (0,1):
                res=blocks[s].apply(vs[s])-vs[s]*ev[s][None,:]
                maxres=max(maxres,float(np.max(np.linalg.norm(res,axis=0))))
                maxorth=max(maxorth,float(np.max(abs(vs[s].T@vs[s]-np.eye(len(en[s]))))))
        if not np.all(np.isfinite(np.concatenate(en))) or not np.isfinite(rec['odd_gap']):
            raise ArithmeticError(f'Nonfinite spectrum at site {site}')
        records.append(rec);times['diagnostics']+=time.perf_counter()-tick
        # Scalar + retained-state checkpoint: no large parent matrices or eigenbases.
        stop=bool(stop_requested and stop_requested())
        if checkpoint is not None:
            tick=time.perf_counter()
            state={'en0':en[0],'en1':en[1],'b0':prevb[0],'b1':prevb[1]}
            if observers:state.update(sz0=sz[0],sz1=sz[1],sx0=sx[0],sx1=sx[1])
            if tangent:state.update(de0=de[0],de1=de[1],db0=db[0],db1=db[1])
            state['meta']={'next_site':site+1,'logsz':float(logsz),'logsx':float(logsx),
                'records':records,'mingap':mingap,'maxres':maxres,'maxorth':maxorth,'timing':times}
            checkpoint(state,stop or site+1==cfg.nsites)
            times['checkpoint']+=time.perf_counter()-tick
        if stop:
            from .io import Interrupted
            raise Interrupted(f'Stopped safely after site {site}')
    return {'alpha':float(alpha),'config':cfg.asdict(),'records':records,
       'validation':{'max_checked_eigen_residual':maxres,'max_checked_orthogonality':maxorth},
       'minimum_kept_discarded_gap':mingap,'seconds':time.perf_counter()-start,'timing':times,
       'method':'block exact-projector tangent' if tangent else 'block NRG',
       'backend':backend,'observers':observers,'resumed_at_site':begin,'sector_workers':sector_workers}


def run_tangent(alpha,cfg,**kw):
    return run(alpha,cfg,tangent=True,**kw)
