from __future__ import annotations
import argparse,contextlib,json,sys,time
from pathlib import Path
import numpy as np
from . import io

def validate_checkpoint(cp,cfg):
    if cp['config']!=cfg:raise ValueError('Checkpoint configuration, source, or runtime mismatch')
    if 'low' in cp:
        for k in ('r','g','C'):
            a=np.asarray(cp['low'][k]);
            if a.shape!=(5,) or not np.isfinite(a).all():raise ValueError('Invalid low calibration')
    for p,c in cp.get('components',{}).items():
        if int(p) not in (0,1,2,3) or c['reference']!=int(p):raise ValueError('Invalid reference component')
        for k in ('F','M','V')+ (('K',) if cfg['scheme']=='vacuum_only' else ()):
            n=7 if k=='K' else 9;a=np.asarray(c[k])
            if a.shape!=(n,) or not np.isfinite(a).all():raise ValueError('Invalid component '+k)

def blas_single_thread():
    # threadpoolctl 2.2 raises on some BLAS builds; the batch scripts also export
    # OPENBLAS/MKL/OMP_NUM_THREADS=1, which is the fallback.
    try:
        from threadpoolctl import threadpool_limits
        return threadpool_limits(limits=1)
    except Exception:return contextlib.nullcontext()

def export_signature(config):
    # Thread count and outer backend do not change any output bit (fixed-block
    # reductions, disjoint prange rows; stored and ranked compared in the tests).
    # They stay recorded per row; resume and shard assembly still compare them.
    sig={k:v for k,v in config.items() if k not in ('cutoff','outer_backend')}
    sig['runtime']={k:v for k,v in config['runtime'].items() if k!='threads'}
    return sig

def run_item(args):
    import numba
    from .engine import compute,validate_result
    io.reject_multirank()
    if args.threads<1 or args.threads>numba.config.NUMBA_NUM_THREADS:raise ValueError('Invalid Numba thread count')
    if not np.isfinite(args.memory_limit_gib) or args.memory_limit_gib<=0:raise ValueError('Positive memory limit required')
    numba.set_num_threads(args.threads)
    # threadpool limits are process-global; only one solver per process.
    with blas_single_thread():
        cfg=io.config(args.cutoff,args.scheme,args.outer_backend,args.threads)
        ref=args.reference;refs=(0,1,3,2) if ref is None else (ref,)
        stem=f'{args.scheme}_L{args.cutoff}_d8'+('' if ref is None else f'_ref{ref}')
        out=args.output_dir/(stem+'.json');check=args.output_dir/'checkpoints'/(stem+'.json')
        # flock guards the node; the O_EXCL owner guards the shared file system. Both are
        # held by this solver from before the first read until after the last write.
        # Both files it writes are owned (io.owner_path, the same owners assemble/export use)
        # from before the first read until after the last write.
        with io.claim(args.output_dir/'claims'/(stem+'.lock')),io.owners(out,check),io.StopFlag() as stop:
            cp={'config':cfg,'components':{}}
            if out.exists():
                if not args.resume:raise FileExistsError('Output exists; use --resume')
                payload=io.read(out);validate_checkpoint(payload,cfg)
                if payload['references']!=list(refs):raise ValueError('Reference selection mismatch')
                if 'C' in payload:validate_result(payload)
                print(json.dumps({'status':'reused','path':str(out)}));return
            if check.exists():
                if not args.resume:raise FileExistsError('Checkpoint exists; use --resume')
                cp=io.read(check);validate_checkpoint(cp,cfg)
            def save():io.atomic_save(check,cp)
            def on_low(low):
                cp['low']=low;save();stop.boundary()
            def on_component(p,c):
                cp['components'][str(p)]=c;save();stop.boundary()
            # No basis rebuild when all scalar components are already present.
            stop.boundary()
            r=compute(args.cutoff,args.scheme,args.outer_backend,refs,cp.get('low'),
                      {int(k):v for k,v in cp['components'].items()},on_low,on_component,args.memory_limit_gib)
            r.update(config=cfg,references=list(refs))
            validate_checkpoint(r,cfg)
            if 'C' in r:validate_result(r)
            io.atomic_save(out,r)
            print(json.dumps({'status':'accepted','path':str(out),'seconds':r['seconds'],
                              'C8':r.get('C',[None]*9)[8],'maxrss_mib':r['peak_rss_kib']/1024}),flush=True)

def merge(args):
    from .engine import assemble,validate_result
    rows=[io.read(p) for p in args.inputs]
    if len(rows)!=4:raise ValueError('Exactly four reference files required')
    cfg=rows[0]['config'];low=rows[0]['low'];components={}
    for r in rows:
        validate_checkpoint(r,cfg)
        if io.digest(r['low'])!=io.digest(low):raise ValueError('Mixed calibration inputs')
        if len(r['references'])!=1:raise ValueError('Expected one-reference shards')
        p=r['references'][0]
        if p in components:raise ValueError('Duplicate reference')
        if set(r['components'])!={str(p)}:raise ValueError('Unexpected shard components')
        components[p]=r['components'][str(p)]
    result=assemble(components,low,cfg['cutoff'],cfg['scheme'])
    result.update(config=cfg,low=low,components={str(k):v for k,v in components.items()},
                  references=[0,1,3,2],assembly='four independent scalar reference shards',
                  shard_files=[str(p) for p in args.inputs])
    with io.publication(args.output):io.atomic_save(args.output,result)
    print(json.dumps({'path':str(args.output),'C8':result['C'][8]}))

def main(argv=None):
    ap=argparse.ArgumentParser(description='Exact residual-form C8 solver; raw or isolated vacuum prescription only.')
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--cutoff',type=int,required=True)
    p.add_argument('--scheme',choices=['raw','vacuum_only'],default='raw')
    p.add_argument('--outer-backend',choices=['stored','ranked'],default='stored')
    p.add_argument('--threads',type=int,default=1);p.add_argument('--reference',type=int,choices=[0,1,2,3])
    p.add_argument('--memory-limit-gib',type=float,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--resume',action='store_true')
    p=sub.add_parser('plan');p.add_argument('--cutoffs',type=int,nargs='+',required=True)
    p.add_argument('--outer-backend',choices=['stored','ranked'],default='stored')
    p=sub.add_parser('assemble');p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('export');p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('warmup');p.add_argument('--threads',type=int,default=1)
    args=ap.parse_args(argv)
    try:
        if args.command=='run':run_item(args)
        elif args.command=='assemble':merge(args)
        elif args.command=='plan':
            from .planning import plan
            print(json.dumps([plan(L,args.outer_backend) for L in args.cutoffs],indent=2))
        elif args.command=='export':
            from .engine import validate_result
            rows=[io.read(p) for p in args.inputs];seen=set();common=None
            for r in rows:
                validate_result(r);validate_checkpoint(r,r['config'])
                signature=export_signature(r['config'])
                if common is None:common=signature
                if signature!=common:raise ValueError('Mixed source/runtime/prescription outputs')
                if r['cutoff'] in seen:raise ValueError('Duplicate cutoff')
                seen.add(r['cutoff'])
            if args.output.exists():raise FileExistsError('Export exists')
            args.output.parent.mkdir(parents=True,exist_ok=True)
            # Legacy analysis consumes a flat JSON list. A sidecar records its digest. Both are
            # published under one exclusive owner; the sidecar is written last, so an export
            # without its sidecar is an interrupted publication (delete it and rerun).
            data=sorted(rows,key=lambda r:r['cutoff']);blob=json.dumps(data,indent=2,allow_nan=False)+'\n'
            import os,hashlib
            side=args.output.with_suffix('.provenance.json')
            with io.publication(args.output,side):
                tmp=io.tmp_name(args.output)
                try:
                    with tmp.open('w') as f:f.write(blob);f.flush();os.fsync(f.fileno())
                    os.replace(tmp,args.output)
                finally:
                    if tmp.exists():tmp.unlink()
                io.atomic_save(side,{'sha256_export':hashlib.sha256(blob.encode()).hexdigest(),'config':common})
        elif args.command=='warmup':
            import numba
            from .engine import compute
            numba.set_num_threads(args.threads)
            for scheme in ('raw','vacuum_only'):
                for backend in ('stored','ranked'):compute(4,scheme,backend)
            print('Float64 kernels warmed. Int64 edge kernels are exercised by the test suite.')
    except io.StopRequested as e:
        print(str(e),file=sys.stderr);return 75
    except io.ClaimBusy as e:
        print(str(e),file=sys.stderr);return 73
    return 0
if __name__=='__main__':sys.exit(main())
