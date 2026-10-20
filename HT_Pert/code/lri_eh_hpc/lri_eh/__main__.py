"""CLI imports the numerical runtime only after argument parsing."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description='Isolated effective-Hamiltonian correction: reproducible HPC addon')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--cutoff',type=int,required=True);p.add_argument('--degree',type=int,choices=[4,5,6,7],default=7)
    p.add_argument('--threads',type=int,default=int(os.environ.get('SLURM_CPUS_PER_TASK','4')))
    p.add_argument('--memory-limit-gib',type=float,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--max-attempts',type=int,default=3)
    p=sub.add_parser('plan');p.add_argument('--cutoffs',nargs='+',type=int,required=True);p.add_argument('--degree',type=int,choices=[4,5,6,7],default=7)
    p.add_argument('--memory-limit-gib',type=float);p.add_argument('--output',type=Path)
    p=sub.add_parser('validate');p.add_argument('files',type=Path,nargs='+');p.add_argument('--expected-source',required=True)
    p=sub.add_parser('warmup');p.add_argument('--threads',type=int,default=1)
    p=sub.add_parser('lane');p.add_argument('--manifest',type=Path,required=True);p.add_argument('--lane',type=int,required=True)
    p=sub.add_parser('export');p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--expected-source',required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('source')
    args=parser.parse_args()
    # Respect explicitly supplied settings; avoid nested BLAS thread pools by default.
    os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
    if args.command=='source':
        from .runtime import fingerprint;print(fingerprint());return
    if args.command=='run':
        from .runner import run
        from .runtime import BusyError,Preempted,AcceptanceError
        try:
            r=run(args.cutoff,args.degree,args.output_dir,args.threads,args.memory_limit_gib,args.resume,args.max_attempts)
            print(json.dumps(dict(cutoff=r['cutoff'],degree=r['degree'],delta_C=r['delta_C'],seconds=r['seconds'],acceptance=r['acceptance']),allow_nan=False))
        except BusyError as e:print(str(e),file=sys.stderr);raise SystemExit(73)
        except Preempted as e:print(str(e),file=sys.stderr);raise SystemExit(75)
        except AcceptanceError as e:print(str(e),file=sys.stderr);raise SystemExit(65)
    elif args.command=='plan':
        from .planner import plan
        from .runtime import atomic_json
        r=[plan(L,args.degree,args.memory_limit_gib) for L in args.cutoffs]
        if args.output:
            if args.output.exists():raise FileExistsError(args.output)
            atomic_json(args.output,r)
        print(json.dumps(r,indent=2))
    elif args.command=='warmup':
        from numba import set_num_threads
        from .numerics import compute
        set_num_threads(args.threads)
        for d in (4,5,6,7):compute(4,d,1.)
        # Compile int64 index signature without a multi-billion-state allocation.
        import numpy as np
        from ._core.kernels import ladder
        for it in (np.int32,np.int64):
            ladder(np.array([0,1],np.int64),np.array([0],it),np.array([0],np.uint16),np.array([1],np.uint8),
                   np.ones((1,2,4)),np.ones((1,1)),np.empty((0,1)),3,np.array([0],np.int16),-1)
        print('Warmup complete (float64; int32/int64 edge-index signatures).')
    elif args.command=='validate':
        from .runtime import validate_result
        for f in args.files:
            r=validate_result(json.loads(f.read_text()))
            if r['source_sha256']!=args.expected_source:raise ValueError('Unexpected correction source')
            print(f'{f}: accepted')
    elif args.command=='lane':
        from .campaign import lane
        raise SystemExit(lane(args.manifest,args.lane))
    elif args.command=='export':
        from .export import export
        export(args.inputs,args.expected_source,args.output)

if __name__=='__main__':main()
