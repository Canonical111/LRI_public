"""Reference-order kernel: preserve operation order of projected operators.

Avoid full doubled-space H and DH, but retain legacy eigenvector ordering and
BLAS association. Useful when unstable terminal flows demand numerical replay.
"""
from dataclasses import asdict
import time
import numpy as np
from scipy.linalg import eigh
from threadpoolctl import threadpool_limits
from .config import Config,chain_coefficients

def _project_old(V,op,nb):
    t=V.reshape(op.shape[0],nb,-1)
    applied=np.einsum('ab,bnk->ank',op,t,optimize=True).reshape(V.shape)
    return V.T@applied

def _project_new(V,op,nold):
    t=V.reshape(nold,op.shape[0],-1)
    applied=np.zeros_like(t)
    applied[:,:-1,:]=np.sqrt(np.arange(1,op.shape[0]))[None,:,None]*t[:,1:,:]
    applied=applied.reshape(V.shape)
    return V.T@applied

def _assemble(en,par,nb,onsite,hop,scale,op,sector,old_tangent=None):
    ids=np.flatnonzero((par[:,None]*((-1)**np.arange(nb))[None,:]).ravel()==sector)
    n=ids%nb;a=ids//nb;D=len(ids)
    H=np.zeros((D,D),order="F")
    if old_tangent is None:
        diag=np.repeat(scale*en,nb)+np.tile(np.arange(nb)*onsite,len(en))
        np.fill_diagonal(H,diag[ids])
    # Same old-major ordering as reference H[np.ix_(ids,ids)].
    for m in range(nb):
        row=np.flatnonzero(n==m);ar=a[row]
        if old_tangent is not None:
            H[np.ix_(row,row)]=scale*old_tangent[np.ix_(ar,ar)]
        if m+1<nb:
            col=np.flatnonzero(n==m+1);ac=a[col]
            H[np.ix_(row,col)]+=hop*(op.T[np.ix_(ar,ac)]*np.sqrt(m+1))
            H[np.ix_(col,row)]+=hop*(op[np.ix_(ac,ar)]*np.sqrt(m+1))
    return ids,H

def run_reference_order(alpha,cfg,*,tangent=False,observers=True,fast_tangent=True,
                        checkpoint=None,resume_state=None,stop_requested=None,check_every=0):
    cfg.check()
    if not np.isfinite(alpha) or alpha<0 or (tangent and alpha<=0):raise ValueError('Invalid alpha')
    start=time.perf_counter();onsite,hop=chain_coefficients(cfg.s,cfg.Lambda,cfg.nsites)
    nb=cfg.nb;b=np.diag(np.sqrt(np.arange(1,nb)),1)
    en=np.array([-cfg.tunneling/2,cfg.tunneling/2]);par=np.array([1,-1]);sz=np.array([[0.,1.],[1.,0.]])
    sx=np.diag([1.,-1.]);prevb=dprevb=None;de=np.zeros((2,2));records=[];maxres=maxorth=0.;mingap=None
    logsz=logsx=0.;begin=0
    if resume_state is not None:
        st=resume_state;m=st['meta'];en=st['en'];par=np.array(m['par']);prevb=st['b']
        if observers:sz=st['sz'];sx=st['sx']
        if tangent:de=st['de'];dprevb=st['db']
        logsz=m['logsz'];logsx=m['logsx'];begin=m['next_site'];records=m['records'];mingap=m['mingap'];maxres=m['maxres'];maxorth=m['maxorth']
    with threadpool_limits(limits=cfg.threads):
      for site in range(begin,cfg.nsites):
        nold=len(en);es=[];vs=[];dvs=[];ders=[];sizes=[];idx=[];hs=[]
        coupling=.5*np.sqrt(2*alpha/(cfg.s+1)) if site==0 else hop[site]
        op=sz if site==0 else prevb;scale=1 if site==0 else cfg.Lambda
        for sector in (1,-1):
            ids,H=_assemble(en,par,nb,onsite[site],coupling,scale,op,sector);idx.append(ids)
            keep=min(cfg.keep,len(ids))
            checked=site in (0,1,2,cfg.nsites-1) or (check_every and site%check_every==0)
            if not np.all(np.isfinite(H)):raise ArithmeticError(f'Nonfinite Hamiltonian at site {site}')
            Hsave=H.copy() if checked else None
            ee,U=eigh(H,check_finite=False,overwrite_a=True,driver='evd' if tangent else 'evr',
                      subset_by_index=None if tangent else (0,keep-1))
            if tangent:
                if site==0:
                    # Match (coupling/(2alpha)) association in original DH.
                    _,DH=_assemble(np.zeros_like(en),par,nb,0.,coupling,0.,op,sector)
                    DH/=2*alpha
                else:
                    _,DH=_assemble(en,par,nb,0.,coupling,scale,dprevb,sector,old_tangent=de)
                if not np.all(np.isfinite(DH)):raise ArithmeticError(f'Nonfinite tangent Hamiltonian at site {site}')
                Uk=U[:,:keep];Ud=U[:,keep:]
                applied=DH@Uk if fast_tangent else None
                tang=Uk.T@applied if fast_tangent else Uk.T@DH@Uk
                ders.append(tang)
                if len(ee)>keep:
                    gap=float(ee[keep]-ee[keep-1]);mingap=gap if mingap is None else min(mingap,gap)
                    if gap<5e-13*max(1,abs(float(ee[keep]))):raise ArithmeticError('Non-smooth retained boundary')
                    cross=Ud.T@applied if fast_tangent else Ud.T@DH@Uk;den=ee[:keep][None,:]-ee[keep:,None];dU=Ud@(cross/den)
                else:dU=np.zeros_like(Uk)
                dvs.append(dU)
            retained=np.array(U[:,:keep],order='F',copy=True)
            es.append(ee[:keep].copy());vs.append(retained);sizes.append(keep)
            if checked:
                maxres=max(maxres,float(np.max(np.linalg.norm(Hsave@retained-retained*ee[:keep][None,:],axis=0))))
                maxorth=max(maxorth,float(np.max(abs(retained.T@retained-np.eye(keep)))))
            del U,H,Hsave
            if tangent:
                del DH,Uk,Ud,applied
                if len(ee)>keep:del cross,den

        ground=min(es[0][0],es[1][0]);en=np.concatenate(es)-ground;par=np.repeat([1,-1],sizes)
        V=np.zeros((nold*nb,len(en)));DV=np.zeros_like(V) if tangent else None
        denew=np.zeros((len(en),len(en))) if tangent else None
        for s,ids in enumerate(idx):
            offset=0 if s==0 else sizes[0];dest=np.arange(offset,offset+sizes[s])
            V[np.ix_(ids,dest)]=vs[s]
            if tangent:DV[np.ix_(ids,dest)]=dvs[s];denew[np.ix_(dest,dest)]=ders[s]
        gsector=int(es[1][0]<es[0][0]);ground_idx=int(np.argmin(en));gs=V[:,ground_idx].reshape(nold,nb)
        if tangent:
            dg=[float(a[0,0]) for a in ders];de=denew-dg[gsector]*np.eye(len(en))
            a=np.zeros((nold,nb,V.shape[1]));da=np.zeros_like(a)
            weights=np.sqrt(np.arange(1,nb))[None,:,None]
            a[:,:-1,:]=weights*V.reshape(nold,nb,-1)[:,1:,:]
            da[:,:-1,:]=weights*DV.reshape(nold,nb,-1)[:,1:,:]
            a=a.reshape(V.shape);da=da.reshape(V.shape)
            prevb=V.T@a;dprevb=DV.T@a+V.T@da
        else:prevb=_project_new(V,b,nold)
        odd=par[:,None]!=par[None,:];prevb*=odd
        if tangent:dprevb*=odd;de*=~odd
        rec={'iteration':site,'log_energy_scale':float(-site*np.log(cfg.Lambda)),
             'odd_gap':float(es[1][0]-es[0][0]),'last_boson_occupation':float(np.sum(gs*gs*np.arange(nb)[None,:])),
             'last_boson_edge':float(np.sum(gs[:,-1]**2)),
             'even_levels':(es[0][:cfg.nlevels]-ground).tolist(),'odd_levels':(es[1][:cfg.nlevels]-ground).tolist()}
        if observers:
            sz=_project_old(V,sz,nb);sx=_project_old(V,sx,nb);sz*=odd;sx*=~odd
            sx-=sx[ground_idx,ground_idx]*np.eye(len(en));nz=float(np.linalg.norm(sz));nx=float(np.linalg.norm(sx))
            if nz>0:sz/=nz;logsz+=np.log(nz)
            if nx>0:sx/=nx;logsx+=np.log(nx)
            w=sz[:,ground_idx]**2;cw=float(np.sum(w*np.exp(-en)));wx=sx[:,ground_idx]**2;wx[ground_idx]=0;cx=float(np.sum(wx*np.exp(-en)))
            rec.update(log_spin_scale_correlation=float(np.log(max(cw,1e-300))+2*logsz),log_retained_spin_weight=float(np.log(max(w.sum(),1e-300))+2*logsz),log_thermal_scale_correlation=float(np.log(max(cx,1e-300))+2*logsx))
        if tangent:rec.update(d_alpha_odd_gap=dg[1]-dg[0],log_abs_d_alpha_odd_gap=float(np.log(max(abs(dg[1]-dg[0]),1e-300))))
        records.append(rec)
        stop=bool(stop_requested and stop_requested())
        if checkpoint is not None:
            state={'en':en,'b':prevb}
            if observers:state.update(sz=sz,sx=sx)
            if tangent:state.update(de=de,db=dprevb)
            state['meta']={'next_site':site+1,'records':records,'par':par.tolist(),
                 'logsz':float(logsz),'logsx':float(logsx),'maxres':maxres,'maxorth':maxorth,'mingap':mingap}
            checkpoint(state,stop or site+1==cfg.nsites)
        if stop:
            from .io import Interrupted
            raise Interrupted(f'Stopped safely after site {site}')
    return {'alpha':alpha,'config':asdict(cfg),'records':records,'seconds':time.perf_counter()-start,
            'validation':{'max_checked_eigen_residual':maxres,'max_checked_orthogonality':maxorth},
            'resumed_at_site':begin,'minimum_kept_discarded_gap':mingap,'method':'reference-order tangent' if tangent else 'reference-order flow','backend':'reference-order','observers':observers}
