"""Restartable fixed-alpha and critical-point workflows; no physical targets."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import json,math,os,signal,time
from .config import Config
from .api import run
from .io import identity,canonical,write_record,read_record,save_state,load_state,claim,Interrupted,IntegrityError
from .validation import validate_result,audit_tangent
from .campaign import resolve_target


def plan(cfg,sector_workers=1):
    cfg.check();d=cfg.keep*cfg.nb;k=cfg.keep
    # Conservative envelope: LAPACK copies/workspaces and local vectors. Calibrate!
    work=(8*(6*sector_workers*d*d+24*d*k+32*k*k))
    gib=(1.35*work+256*2**20)/2**30
    return {'max_dimension_per_parity':d,'retained_states_per_parity':k,
            'approximate_workspace_bytes':work,'estimated_gib_with_margin':gib,
            'status':'uncalibrated conservative estimate, not an RSS guarantee',
            'arithmetic':'float64','dense_asymptotics':'O(nsites*(keep*nb)^3) time; O((keep*nb)^2+keep^2*nb) working memory'}


def check_allocation(cfg,memory_limit_gib=None,sector_workers=1):
    for env in ('OMPI_COMM_WORLD_SIZE','PMI_SIZE','MV2_COMM_WORLD_SIZE'):
        if int(os.environ.get(env,'1'))>1:raise ValueError('Single trajectory is not MPI-distributed; use independent array tasks')
    if cfg.threads>int(os.environ.get('SLURM_CPUS_PER_TASK',str(cfg.threads))):raise ValueError('Thread budget exceeds SLURM_CPUS_PER_TASK')
    if memory_limit_gib is not None:
        if not math.isfinite(memory_limit_gib) or memory_limit_gib<=0:raise ValueError('Invalid memory limit')
        if plan(cfg,sector_workers)['estimated_gib_with_margin']>memory_limit_gib:raise MemoryError('Planned workspace exceeds explicit memory budget')

def _stop_file():
    return os.environ.get('LRI_SPIN_STOP_FILE') or None


def _refuse_if_stopped():
    # A lane's stop request persists as a file, so a child that was still
    # starting when it was made cannot miss it; nothing is written.
    f=_stop_file()
    if f and os.path.exists(f):raise Interrupted('Stop requested before start; no work done')


def _owner_token(token):
    return token if token is not None else os.environ.get('LRI_SPIN_OWNER_TOKEN')


class Stop:
    def __init__(self):self.requested=False;self.previous={};self.file=_stop_file()
    def __call__(self):
        if not self.requested and self.file and os.path.exists(self.file):self.requested=True
        return self.requested
    def __enter__(self):
        def handler(signum,frame):self.requested=True
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):
            self.previous[sig]=signal.signal(sig,handler)
        return self
    def __exit__(self,*args):
        for sig,h in self.previous.items():signal.signal(sig,h)


def _fixed(alpha,cfg,folder,*,tangent=False,backend='ordered',sector_workers=1,
           observers=True,resume=False,stop=None,checkpoint_every=8,guard=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    kind='tangent' if tangent else ('flow' if observers else 'spectrum')
    ident=identity(cfg,float(alpha),kind,backend,sector_workers,observers=observers)
    final=folder/'result.json';cp=folder/'state.npz'
    if final.exists():
        if not resume:raise FileExistsError(f'{final}; use --resume or a fresh folder')
        r=read_record(final,ident);validate_result(r,cfg,tangent=tangent,observers=observers);return r
    st=load_state(cp,ident) if cp.exists() and resume else None
    if cp.exists() and not resume:raise FileExistsError(f'{cp}; use --resume or a fresh folder')
    def save(state,force):
        if force or state['meta']['next_site']%checkpoint_every==0:
            if guard:guard()
            save_state(cp,ident,state)
    r=run(alpha,cfg,tangent=tangent,backend=backend,observers=observers,
          sector_workers=sector_workers,checkpoint=save,resume_state=st,stop_requested=stop,check_every=16)
    r['acceptance']=validate_result(r,cfg,tangent=tangent,observers=observers)
    if tangent:r['analysis']=audit_tangent(r)
    if guard:guard()
    write_record(final,ident,r)
    return r


def fixed(alpha,cfg,folder,*,memory_limit_gib=None,owner_token=None,**kw):
    check_allocation(cfg,memory_limit_gib,kw.get('sector_workers',1))
    _refuse_if_stopped()
    folder,guard=resolve_target(folder,_owner_token(owner_token))
    with claim(Path(folder)/'.claim.lock'),Stop() as stop:
        return _fixed(alpha,cfg,folder,stop=stop,guard=guard,**kw)


def critical(cfg,folder,*,bracket=(.01,2.),fraction=.3,atol=5e-14,maxiter=48,
             backend='ordered',sector_workers=1,memory_limit_gib=None,resume=False,
             with_tangent=True,checkpoint_every=8,owner_token=None):
    check_allocation(cfg,memory_limit_gib,sector_workers)
    if not (len(bracket)==2 and 0<bracket[0]<bracket[1] and all(map(math.isfinite,bracket))):raise ValueError('Invalid bracket')
    if not (0<fraction<1 and math.isfinite(atol) and atol>0 and 1<=maxiter<=200):raise ValueError('Invalid critical search limits')
    _refuse_if_stopped()
    folder,guard=resolve_target(folder,_owner_token(owner_token))
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    ident=identity(cfg,None,'critical',backend,sector_workers,bracket=list(bracket),fraction=fraction,atol=atol,maxiter=maxiter,with_tangent=with_tangent)
    statepath=folder/'tuning.json';final=folder/'result.json'
    with claim(folder/'.claim.lock'),Stop() as stop:
        if final.exists():
            if not resume:raise FileExistsError('Existing critical result; use --resume')
            out=read_record(final,ident)
            validate_result(out['critical_flow'],cfg)
            if with_tangent:validate_result(out['tangent'],cfg,tangent=True)
            return out
        if statepath.exists():
            if not resume:raise FileExistsError('Existing tuning state; use --resume')
            state=read_record(statepath,ident)
        else:state={'phase':'bracket','history':[],'iteration':0,'lo':bracket[0],'hi':bracket[1]}
        def persist():
            if guard:guard()
            write_record(statepath,ident,state)
        # The free target must use the SAME finite NRG map, not an analytic shortcut.
        free=_fixed(0.,cfg,folder/'trials'/'free',backend=backend,sector_workers=sector_workers,
                    observers=False,resume=resume,stop=stop,checkpoint_every=checkpoint_every,guard=guard)
        target=fraction*free['records'][-1]['odd_gap'];state['target']=target
        def ev(a):
            key=float(a).hex().replace('+','p').replace('-','m').replace('.','_')
            p=folder/'trials'/key
            # Identical alpha calls reuse only hashed, validated output from this search.
            d=_fixed(a,cfg,p,backend=backend,sector_workers=sector_workers,observers=False,
                     resume=resume or p.exists(),stop=stop,checkpoint_every=checkpoint_every,guard=guard)
            value=d['records'][-1]['odd_gap']-target
            state['history'].append({'alpha':a,'terminal_gap':value+target,'f':value})
            return value
        if state['phase']=='bracket':
            lo=state['lo'];hi=state['hi'];flo=ev(lo);fhi=ev(hi)
            for _ in range(40):
                if flo>0:break
                lo/=2;flo=ev(lo)
            for _ in range(40):
                if fhi<0:break
                hi*=2
                if hi>100:break
                fhi=ev(hi)
            if not flo>0>fhi:raise RuntimeError('No valid phase bracket; no critical result accepted')
            state.update(phase='bisect',lo=lo,hi=hi,flo=flo,fhi=fhi);persist()
        if state['phase']=='bisect':
            while state['iteration']<maxiter:
                lo=state['lo'];hi=state['hi'];mid=(lo+hi)/2
                if hi-lo < atol*max(1,abs(mid)):break
                fm=ev(mid)
                if fm>0:state.update(lo=mid,flo=fm)
                else:state.update(hi=mid,fhi=fm)
                state['iteration']+=1;persist()
                if stop():raise Interrupted('Saved bisection bracket')
            mid=(state['lo']+state['hi'])/2
            if state['hi']-state['lo']>=atol*max(1,abs(mid)):
                raise RuntimeError('Bisection exhausted: not accepted as critical')
            state['phase']='final';persist()
        midpoint=(state['lo']+state['hi'])/2
        common={'backend':backend,'sector_workers':sector_workers,'resume':resume,'stop':stop,'checkpoint_every':checkpoint_every,'guard':guard}
        d=_fixed(midpoint,cfg,folder/'final_flow',**common)
        d['critical_tuning']={'selection':'final_bracket_midpoint','bracket':[state['lo'],state['hi']],
            'target_gap':target,'fraction':fraction,'terminal_residual':d['records'][-1]['odd_gap']-target,
            'root_convention':'terminal fraction of free gap; interior plateau required'}
        out={'critical_flow':d,'tuning':state,'scope':'finite-resolution critical trajectory; not physical convergence'}
        if with_tangent:
            out['tangent']=_fixed(midpoint,cfg,folder/'tangent',tangent=True,**common)
            out['analysis']=out['tangent']['analysis']
        if guard:guard()
        write_record(final,ident,out);return out
