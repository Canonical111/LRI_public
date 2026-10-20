"""Command-line planning, immutable result identity and safe coefficient runs."""
from __future__ import annotations
from pathlib import Path
import argparse,json,os,signal,sys,time,resource,platform,socket

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    pl=sub.add_parser('plan');pl.add_argument('--cutoffs',type=int,nargs='+',required=True);pl.add_argument('--degree',type=int,default=8);pl.add_argument('--output',type=Path)
    r=sub.add_parser('run');r.add_argument('--cutoff',type=int,required=True);r.add_argument('--degree',type=int,default=8);r.add_argument('--scheme',choices=['raw','consistent','literal'],default='consistent');r.add_argument('--threads',type=int,default=1);r.add_argument('--backend',choices=['native','numba'],default='native');r.add_argument('--pmax',type=int);r.add_argument('--full-order',action='store_true');r.add_argument('--max-states',type=int,default=3000000);r.add_argument('--memory-gib',type=float,default=3.);r.add_argument('--cache',type=Path);r.add_argument('--checkpoint',type=Path);r.add_argument('--checkpoint-seconds',type=float,default=300);r.add_argument('--resume',action='store_true');r.add_argument('--output',type=Path,required=True);r.add_argument('--stop-after-wave',type=int,help=argparse.SUPPRESS)
    a=p.parse_args(argv)
    nt=getattr(a,'threads',1)
    if nt<1:p.error('threads must be positive')
    # Must occur before importing NumPy/Numba or initializing either OpenMP pool.
    os.environ['NUMBA_NUM_THREADS']=str(nt);os.environ['OMP_NUM_THREADS']=str(nt)
    os.environ.setdefault('OMP_WAIT_POLICY','PASSIVE')
    os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
    import numpy as np, scipy, numba
    numba.set_num_threads(nt)
    from .basis import plan
    from .storage import source_digest,digest,envelope,read_envelope,atomic_json,output_lock,cached_graph,save_checkpoint,load_checkpoint
    if a.command=='plan':
        out=[plan(L,a.degree) for L in a.cutoffs]
        if a.output:atomic_json(a.output,out)
        print(json.dumps(out,indent=2));return 0
    if a.memory_gib<=0 or a.max_states<1:p.error('Memory/state guards must be positive')
    if a.resume and a.checkpoint is None:p.error('--resume requires --checkpoint')
    if a.stop_after_wave and a.checkpoint is None:p.error('An interrupted test requires --checkpoint')
    cfg=dict(L=a.cutoff,degree=a.degree,scheme=a.scheme,pmax=a.pmax,full_order=a.full_order,backend=a.backend)
    runtime=dict(python=f'{sys.version_info.major}.{sys.version_info.minor}',numpy=np.__version__,scipy=scipy.__version__,numba=numba.__version__,longdouble_bits=int(np.finfo(np.longdouble).nmant),machine=platform.machine())
    ident=digest(dict(configuration=cfg,source=source_digest(),runtime=runtime));stop={'signal':None}
    def handler(sig,frame):stop['signal']=int(sig)
    for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):signal.signal(sig,handler)
    t=time.perf_counter()
    try:
      with output_lock(a.output,ident):
        if a.output.exists():
            old=read_envelope(a.output)
            if old['identity']!=ident:raise ValueError('Existing output has different source/model identity; choose a new output path.')
            print('Verified completed result; skipped:',a.output);return 0
        mem=int(a.memory_gib*2**30);planning=plan(a.cutoff,a.degree,a.pmax)
        if planning['auxiliary_states']>a.max_states or planning['recommended_memory_bytes']>mem:raise MemoryError('Requested plan exceeds explicit guards: '+json.dumps(planning))
        g,cachehit=cached_graph(a.cache,a.cutoff,a.degree,a.pmax,a.max_states,mem)
        from .engine import Engine
        e=Engine(a.cutoff,a.degree,a.scheme,pmax=a.pmax,full_order=a.full_order,max_states=a.max_states,max_bytes=mem,backend=a.backend,graph=g)
        restored=load_checkpoint(e,a.checkpoint,ident) if a.resume else False
        last=[time.monotonic()]
        def progress(eng,stage,k):
            now=time.monotonic();teststop=(a.stop_after_wave is not None and stage=='wave' and k>=a.stop_after_wave)
            required=bool(stop['signal'] or teststop)
            if a.checkpoint and (required or now-last[0]>=a.checkpoint_seconds):
                saved=save_checkpoint(eng,a.checkpoint,ident);last[0]=now
                print('CHECKPOINT',stage,k,saved,flush=True)
            if required:raise InterruptedError('Stopped at a complete coefficient boundary')
        e.progress=progress
        out=e.solve(True)
        payload=dict(identity=ident,configuration=cfg,runtime=runtime,result=out,source_digest=source_digest(),execution=dict(host=socket.gethostname(),threads=nt,seconds=time.perf_counter()-t,peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,cache_hit=cachehit,resumed=restored,slurm_job=os.environ.get('SLURM_JOB_ID')))
        atomic_json(a.output,envelope(payload));print('COMPLETED',a.output,flush=True);return 0
    except InterruptedError as exc:
        print(str(exc),file=sys.stderr);return 75
    except FileExistsError as exc:
        print(str(exc),file=sys.stderr);return 73
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr)
        return 1
